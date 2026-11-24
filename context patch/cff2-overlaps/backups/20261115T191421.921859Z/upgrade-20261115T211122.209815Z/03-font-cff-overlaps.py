#!/usr/bin/env python3
"""Resolve instantiated CFF2 compound outlines for CFF1 embedding.

Protocol 1: input/output JSON files, each containing a `glyphs` array. Segments
are ConTeXt absolute-coordinate arrays ending in m, l, or c. Contours close
implicitly at the next move or end of the glyph, exactly as CFF does.

Skia PathOps operates on float32 coordinates. Outlines proven unchanged with
exact float32 input coordinates are returned verbatim so the caller can retain
their existing charstrings and hints. Other outlines have PathOps precision.
No font files are modified.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import sys
import struct
import tempfile
import time

try:
    import pathops
except ImportError as exc:
    raise SystemExit("CFF2 overlap helper requires skia-pathops in this Python environment") from exc

PROTOCOL = 1


def segments_to_path(segments):
    if not isinstance(segments, list):
        raise ValueError("segments must be an array")
    shape = pathops.Path(fillType=pathops.FillType.WINDING)
    opened = False
    sizes = {"m": 3, "l": 3, "c": 7}
    for i, segment in enumerate(segments):
        if not isinstance(segment, list) or not segment:
            raise ValueError(f"segment {i} must be a nonempty array")
        tag = segment[-1]
        if not isinstance(tag, str) or sizes.get(tag) != len(segment):
            raise ValueError(f"segment {i} has an unsupported operation or operand count")
        values = segment[:-1]
        if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in values):
            raise ValueError(f"segment {i} coordinates must be finite numbers")
        if tag == "m":
            if opened:
                shape.close()
            shape.moveTo(*values)
            opened = True
        elif not opened:
            raise ValueError(f"segment {i} draws before a move")
        elif tag == "l":
            shape.lineTo(*values)
        else:
            shape.cubicTo(*values)
    if opened:
        shape.close()
    # Reject overflow in the conversion from Python doubles to Skia floats.
    if any(not math.isfinite(v) for _, points in shape for point in points for v in point):
        raise ValueError("coordinates exceed PathOps finite range")
    return shape


def path_to_segments(shape):
    segments = []
    current = start = None
    for verb, points in shape:
        if verb == pathops.PathVerb.MOVE:
            current = start = points[0]
            segments.append([*current, "m"])
        elif verb == pathops.PathVerb.LINE:
            current = points[0]
            segments.append([*current, "l"])
        elif verb == pathops.PathVerb.CUBIC:
            current = points[-1]
            segments.append([*points[0], *points[1], *points[2], "c"])
        elif verb == pathops.PathVerb.QUAD:
            # Exact quadratic-to-cubic conversion, should a boolean operation
            # happen to reduce one of the original cubics to a quadratic.
            control, end = points
            first = tuple(a + (b-a)*2/3 for a, b in zip(current, control))
            second = tuple(a + (b-a)*2/3 for a, b in zip(end, control))
            segments.append([*first, *second, *end, "c"])
            current = end
        elif verb == pathops.PathVerb.CLOSE:
            current = start
        else:
            raise ValueError(f"PathOps produced unsupported path verb {verb}")
    return segments


def canonical_contours(shape):
    """Ignore contour order and starting point, but retain direction/geometry."""
    contours = []
    edges = []
    current = start = None

    def finish():
        nonlocal edges
        if start is not None and current != start:
            edges.append(("l", *current, *start))
        if edges:
            # Rotate to the lexicographically smallest edge; ties compare the
            # entire rotation. Do not reverse: winding remains significant.
            smallest = min(edges)
            rotations = [tuple(edges[i:] + edges[:i]) for i, edge in enumerate(edges) if edge == smallest]
            contours.append(min(rotations))
        edges = []

    for verb, points in shape:
        if verb == pathops.PathVerb.MOVE:
            finish()
            current = start = points[0]
        elif verb == pathops.PathVerb.CLOSE:
            finish()
            current = start = None
        else:
            edge = (str(int(verb)), *current, *(v for point in points for v in point))
            # Use the same tag for explicit and implicit closing straight lines.
            if verb == pathops.PathVerb.LINE:
                edge = ("l", *current, *points[0])
            edges.append(edge)
            current = points[-1]
    finish()
    return tuple(sorted(contours))


class CompiledWinding:
    """Standalone ray winding; compile monotonic pieces once per outline.

    Cubic y extrema partition each curve into monotonic intervals. Conservative
    control-point x bounds decide crossings without solving most curves. Only
    ambiguous x positions require bounded 48-step monotonic bisection. No Skia
    classification, font-processing library, or platform renderer is involved.
    """
    def __init__(self, segments):
        self.lines = []
        self.curves = []
        current = start = None
        def line(a,b):
            if a[1] != b[1]:
                low,high = (a,b) if a[1] < b[1] else (b,a)
                self.lines.append((low[1],high[1],low[0],(high[0]-low[0])/(high[1]-low[1]),
                                   1 if b[1] > a[1] else -1))
        def cubic(points):
            p0,p1,p2,p3 = points
            coefficients = []
            for axis in (0,1):
                d = p0[axis]
                c = 3*(p1[axis]-d)
                b = 3*(p2[axis]-p1[axis])-c
                a = p3[axis]-d-c-b
                coefficients.append((a,b,c,d))
            ay,by,cy,dy = coefficients[1]
            cuts = [0.0,1.0]
            if ay == 0:
                if by:
                    cuts.append(-cy/(2*by))
            else:
                discriminant = 4*by*by-12*ay*cy
                if discriminant >= 0:
                    root = math.sqrt(discriminant)
                    cuts.extend(((-2*by-root)/(6*ay),(-2*by+root)/(6*ay)))
            cuts = sorted(set(t for t in cuts if 0 <= t <= 1))
            xmin,xmax = min(p[0] for p in points),max(p[0] for p in points)
            for low,high in zip(cuts,cuts[1:]):
                # Bernstein evaluation at subdivision boundaries avoids
                # cancellation at joins; Horner is used for root refinement.
                def y(t):
                    u = 1-t
                    return u*u*u*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t*t*t*p3[1]
                yl,yh = y(low),y(high)
                if yl != yh:
                    self.curves.append((min(yl,yh),max(yl,yh),low,high,yh>yl,xmin,xmax,
                                        coefficients[0],coefficients[1]))
        for segment in segments:
            tag = segment[-1]
            points = list(zip(segment[:-1:2],segment[1:-1:2]))
            if tag == 'm':
                if current is not None:
                    line(current,start)
                current = start = points[0]
            elif tag == 'l':
                line(current,points[0]);current=points[0]
            else:
                cubic((current,*points));current=points[-1]
        if current is not None:
            line(current,start)

    def __call__(self, point):
        px,py = point
        winding = 0
        for ymin,ymax,x,slope,direction in self.lines:
            if ymin <= py < ymax and x+(py-ymin)*slope > px:
                winding += direction
        for ymin,ymax,low,high,up,xmin,xmax,xcoef,ycoef in self.curves:
            if not ymin <= py < ymax or px >= xmax:
                continue
            direction = 1 if up else -1
            if px < xmin:
                winding += direction
                continue
            ay,by,cy,dy = ycoef
            left,right = low,high
            for _ in range(48):
                middle = (left+right)/2
                if ((((ay*middle+by)*middle+cy)*middle+dy) < py) == up:
                    left = middle
                else:
                    right = middle
            t = (left+right)/2
            ax,bx,cx,dx = xcoef
            if ((ax*t+bx)*t+cx)*t+dx > px:
                winding += direction
        return winding


def point_winding(segments, point):
    return CompiledWinding(segments)(point)


def point_inside(segments, point, even_odd=False):
    winding = point_winding(segments,point)
    return bool(winding % 2) if even_odd else bool(winding)


def robust_point_inside(segments, point, even_odd=False):
    """Independent ray winding with monotonic cubic subdivision/bisection.

    Separate Bernstein evaluator used to adjudicate any disagreement with the
    compiled Horner evaluator near extrema and numerically delicate joins.
    """
    px,py = point
    winding = 0
    current = start = None
    def cross_line(a,b):
        nonlocal winding
        if a[1] <= py < b[1] or b[1] <= py < a[1]:
            x = a[0] + (py-a[1])*(b[0]-a[0])/(b[1]-a[1])
            if x > px:
                winding += 1 if b[1] > a[1] else -1
    def cross_cubic(points):
        nonlocal winding
        p0,p1,p2,p3 = points
        a = p3[1]-3*p2[1]+3*p1[1]-p0[1]
        b = 3*p2[1]-6*p1[1]+3*p0[1]
        c = 3*(p1[1]-p0[1])
        cuts = [0.0,1.0]
        if a == 0:
            if b:
                cuts.append(-c/(2*b))
        else:
            discriminant = 4*b*b-12*a*c
            if discriminant >= 0:
                root = math.sqrt(discriminant)
                cuts.extend(((-2*b-root)/(6*a),(-2*b+root)/(6*a)))
        cuts = sorted(set(t for t in cuts if 0 <= t <= 1))
        def evaluate(t,axis):
            u = 1-t
            return u*u*u*p0[axis]+3*u*u*t*p1[axis]+3*u*t*t*p2[axis]+t*t*t*p3[axis]
        for low,high in zip(cuts,cuts[1:]):
            yl,yh = evaluate(low,1),evaluate(high,1)
            if not (yl <= py < yh or yh <= py < yl):
                continue
            up = yh > yl
            left,right = low,high
            for _ in range(48):
                middle = (left+right)/2
                if (evaluate(middle,1) < py) == up:
                    left = middle
                else:
                    right = middle
            if evaluate((left+right)/2,0) > px:
                winding += 1 if up else -1
    for segment in segments:
        tag = segment[-1]
        points = list(zip(segment[:-1:2],segment[1:-1:2]))
        if tag == 'm':
            if current is not None:
                cross_line(current,start)
            current = start = points[0]
        elif tag == 'l':
            cross_line(current,points[0]);current = points[0]
        else:
            cross_cubic((current,*points));current = points[-1]
    if current is not None:
        cross_line(current,start)
    return bool(winding % 2) if even_odd else bool(winding)


def validation_reference(segments, shape, oracle=None):
    bounds = shape.controlPointBounds
    xmin,ymin,xmax,ymax = bounds
    magnitude = max(1, *(abs(v) for v in bounds))
    tolerance = max(1e-5, magnitude * 2**-21)
    step = max(0.125, tolerance * 8)
    points = [(xmin+(xmax-xmin)*(i+0.5)/7, ymin+(ymax-ymin)*(j+0.5)/7)
              for i in range(7) for j in range(7)]
    # Probe both sides of every segment, including small counters that could
    # be entirely missed by a global sampling grid.
    current = start = None
    contour_points = []
    def line_probes(a,b):
        midpoint = tuple((x+y)/2 for x,y in zip(a,b))
        tangent = (b[0]-a[0],b[1]-a[1])
        add_probes(midpoint,tangent)
    def add_probes(midpoint,tangent):
        length = math.hypot(*tangent)
        if length:
            for distance in (max(tolerance*4,min(0.01,step/4)),step):
                normal = (-tangent[1]/length*distance,tangent[0]/length*distance)
                points.extend(tuple(p+s*n for p,n in zip(midpoint,normal)) for s in (-1,1))
    def finish_contour():
        if current is not None and start is not None and current != start:
            line_probes(current,start)
        if contour_points:
            points.append(((min(p[0] for p in contour_points)+max(p[0] for p in contour_points))/2,
                           (min(p[1] for p in contour_points)+max(p[1] for p in contour_points))/2))
    for segment in segments:
        tag = segment[-1]
        coordinates = list(zip(segment[:-1:2],segment[1:-1:2]))
        if tag == 'm':
            finish_contour();contour_points=[]
            current = start = coordinates[0]
        elif tag == 'l':
            line_probes(current,coordinates[0]);current=coordinates[0]
        else:
            p0,p1,p2,p3 = current,*coordinates
            midpoint = tuple((a+3*b+3*c+d)/8 for a,b,c,d in zip(p0,p1,p2,p3))
            tangent = tuple(0.75*(b-a)+1.5*(c-b)+0.75*(d-c) for a,b,c,d in zip(p0,p1,p2,p3))
            add_probes(midpoint,tangent);current=p3
        contour_points.extend(coordinates)
    finish_contour()
    oracle = oracle or CompiledWinding(segments)
    reference = [(p,bool(oracle(p))) for p in dict.fromkeys(points)]
    return reference,tolerance


def validate_result(original, converted, reference, tolerance):
    converted_oracle = CompiledWinding(converted)
    for point,expected in reference:
        winding = converted_oracle(point)
        if bool(winding) == expected and bool(winding % 2) == expected:
            continue
        expected = robust_point_inside(original,point)
        if (robust_point_inside(converted,point) == expected and
                robust_point_inside(converted,point,even_odd=True) == expected):
            continue
        # Input/output round to float32 (and subsequently CFF1 16.16). Points
        # within this declared numeric band of an original boundary cannot
        # reliably distinguish rounding from a fill error.
        if any(robust_point_inside(original,(point[0]+dx,point[1]+dy)) != expected
               for dx,dy in ((tolerance,0),(-tolerance,0),(0,tolerance),(0,-tolerance))):
            continue
        # Analytic horizontal-ray tests are also numerically ambiguous exactly
        # at a cubic join's y coordinate. Require agreement on BOTH sides of
        # that narrow band, never accept an arbitrary successful nearby point.
        if all(robust_point_inside(original,(point[0],point[1]+dy)) ==
               robust_point_inside(converted,(point[0],point[1]+dy)) ==
               robust_point_inside(converted,(point[0],point[1]+dy),even_odd=True)
               for dy in (-tolerance,tolerance)):
            continue
        return point
    return None


def resolve_segments(segments):
    shape = segments_to_path(segments)
    if not segments:
        return segments,False
    reference,tolerance = validation_reference(segments,shape)
    bounds = shape.controlPointBounds
    center = (-(bounds[0]+bounds[2])/2,-(bounds[1]+bounds[3])/2)
    mismatch = None
    # Skia may silently lose a contour around almost coincident self-crossings.
    # Its own XOR operation can repeat that error, so validate independently.
    # Changing the numeric origin can condition such cases; accept a retry
    # only if it passes the same independent tests against the original.
    for offset in ((0,0),(10,10),center,(0.125,0.25),(-100,-100)):
        shifted = [[*(v+offset[i%2] for i,v in enumerate(s[:-1])),s[-1]] for s in segments]
        try:
            resolved = pathops.simplify(segments_to_path(shifted), fix_winding=True, keep_starting_points=True, clockwise=False)
            converted = path_to_segments(resolved)
            converted = [[*(v-offset[i%2] for i,v in enumerate(s[:-1])),s[-1]] for s in converted]
            mismatch = validate_result(segments,converted,reference,tolerance)
            if mismatch is None:
                resolved = segments_to_path(converted)
                break
        except (pathops.PathOpsError,ValueError) as exc:
            mismatch = str(exc)
    else:
        raise ValueError(f"independent nonzero/even-odd fill validation failed near {mismatch}")
    # CFF1 has no supported overlap semantics. Simplify the entire WINDING
    # path, not each contour independently, so holes and winding cancellation
    # survive. This produces an equivalent nonintersecting contour set.
    exact_input = all(struct.unpack('f', struct.pack('f', float(v)))[0] == v
                      for segment in segments for v in segment[:-1])
    # If conversion to float32 changed any coordinates, topology comparison
    # alone cannot prove the original charstring safe: an overlap smaller than
    # one float32 ulp may already have disappeared before simplify saw it.
    changed = offset != (0,0) or not exact_input or canonical_contours(shape) != canonical_contours(resolved)
    return (converted if changed else segments), changed


def process_request(request):
    if not isinstance(request, dict) or request.get("protocol") != PROTOCOL:
        raise ValueError("unsupported request protocol (expected 1)")
    glyphs = request.get("glyphs")
    if not isinstance(glyphs, list):
        raise ValueError("glyphs must be an array")
    seen = set()
    output = []
    cache = {}
    started = time.monotonic()
    for glyph in glyphs:
        if not isinstance(glyph, dict):
            raise ValueError("each glyph must be an object")
        identifier = glyph.get("id")
        if isinstance(identifier, bool) or not isinstance(identifier, (int, str)) or identifier in seen:
            raise ValueError("glyph ids must be unique integers or strings")
        seen.add(identifier)
        try:
            original = glyph.get("segments")
            key = json.dumps(original,allow_nan=False,separators=(",",":"))
            if key not in cache:
                cache[key] = resolve_segments(original)
            segments, changed = cache[key]
        except Exception as exc:
            raise ValueError(f"glyph {identifier!r}: {exc}") from exc
        output.append({"id": identifier, "segments": segments, "changed": changed})
    return {"protocol": PROTOCOL, "glyphs": output, "stats": {
        "glyphs": len(output), "changed": sum(g["changed"] for g in output),
        "seconds": time.monotonic() - started, "pathops_version": pathops.__version__,
        "unique_outlines": len(cache),
    }}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    temporary = None
    try:
        with args.input.open(encoding="utf-8") as stream:
            request = json.load(stream)
        result = process_request(request)
        # Never expose a partially written successful response.
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=args.output.parent,
                                         prefix=args.output.name + ".", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(result, stream, allow_nan=False, separators=(",", ":"))
            stream.write("\n")
        os.replace(temporary, args.output)
        return 0
    except Exception as exc:
        print(f"CFF2 overlap conversion failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


if __name__ == "__main__":
    sys.exit(main())
