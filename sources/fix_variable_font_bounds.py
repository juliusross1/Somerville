"""Enclose variable outlines in the exported head bounding box.

ConTeXt embeds instantiated TrueType outlines with the original head bounds.
A reduced font's default-instance bounds can clip its wider variable instances.
This updates only the generated TTF header, never a Glyphs source or outline.
"""

import math
import os
from pathlib import Path
import sys
import tempfile
from time import perf_counter

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables.DefaultTable import DefaultTable
from fontTools.ttLib.tables._g_l_y_f import SCALED_COMPONENT_OFFSET
from fontTools.varLib.iup import iup_delta


def variable_bounds(font):
    glyf = font["glyf"]
    variations = font["gvar"].variations
    metrics = font["hmtx"].metrics
    cache = {}
    visiting = set()

    def transform_box(box, matrix):
        xx, xy, yx, yy = matrix
        corners = [(xx*x + yx*y, xy*x + yy*y)
                   for x in (box[0], box[2]) for y in (box[1], box[3])]
        return (min(x for x, y in corners), min(y for x, y in corners),
                max(x for x, y in corners), max(y for x, y in corners))

    def bounds(name):
        if name in cache:
            return cache[name]
        if name in visiting:
            raise ValueError("Cyclic component: " + name)
        visiting.add(name)
        glyph = glyf[name]
        coords, controls = glyf._getCoordinatesAndControls(name, metrics)
        # Each tuple has a nonnegative scalar at most one. Summing each delta's
        # negative/positive contribution bounds every possible axis combination.
        lo = [list(p) for p in coords]
        hi = [list(p) for p in coords]
        for variation in variations.get(name, []):
            deltas = variation.coordinates
            if any(delta is None for delta in deltas):
                deltas = iup_delta(deltas, coords, controls.endPts)
            for i, (dx, dy) in enumerate(deltas):
                lo[i][0] += min(0, dx)
                lo[i][1] += min(0, dy)
                hi[i][0] += max(0, dx)
                hi[i][1] += max(0, dy)
        boxes = []
        if glyph.isComposite():
            for i, component in enumerate(glyph.components):
                if not hasattr(component, "x"):
                    raise ValueError("Point-attached component is unsupported: " + name)
                child = bounds(component.glyphName)
                if child is None:
                    continue
                _, (xx, xy, yx, yy, _, _) = component.getComponentInfo()
                matrix = (xx, xy, yx, yy)
                child = transform_box(child, matrix)
                offset = (lo[i][0], lo[i][1], hi[i][0], hi[i][1])
                if component.flags & SCALED_COMPONENT_OFFSET:
                    offset = transform_box(offset, matrix)
                boxes.append((child[0]+offset[0], child[1]+offset[1],
                              child[2]+offset[2], child[3]+offset[3]))
        elif len(coords) > 4:
            # Ignore the four phantom metric points; enclose control points as
            # well as on-curve points, so quadratic curves are also enclosed.
            boxes.append((min(p[0] for p in lo[:-4]), min(p[1] for p in lo[:-4]),
                          max(p[0] for p in hi[:-4]), max(p[1] for p in hi[:-4])))
        result = None if not boxes else (
            min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))
        cache[name] = result
        visiting.remove(name)
        return result

    boxes = [box for name in font.getGlyphOrder() if (box := bounds(name)) is not None]
    return (math.floor(min(b[0] for b in boxes)), math.floor(min(b[1] for b in boxes)),
            math.ceil(max(b[2] for b in boxes)), math.ceil(max(b[3] for b in boxes)))


def fix_bounds(path):
    started = perf_counter()
    path = Path(path)
    with TTFont(path, recalcBBoxes=False, recalcTimestamp=False) as font:
        if "glyf" not in font or "gvar" not in font:
            raise ValueError("Expected a variable TrueType font: " + str(path))
        head = font["head"]
        original_tables = {tag: font.reader[tag] for tag in font.reader.tables if tag != "head"}
        old = (head.xMin, head.yMin, head.xMax, head.yMax)
        calculated = variable_bounds(font)
        new = (min(old[0], calculated[0]), min(old[1], calculated[1]),
               max(old[2], calculated[2]), max(old[3], calculated[3]))
        if min(new) < -32768 or max(new) > 32767:
            raise ValueError("Variable bounding box exceeds TrueType header range: %r" % (new,))
        if new != old:
            head.xMin, head.yMin, head.xMax, head.yMax = new
            # Reading glyf/gvar can cause fontTools to re-encode them on save.
            # Keep every other table byte-for-byte, including its compression.
            for tag, data in original_tables.items():
                raw = DefaultTable(tag)
                raw.data = data
                font[tag] = raw
            fd, temporary = tempfile.mkstemp(prefix=path.stem + "-bounds-", suffix=".ttf", dir=path.parent)
            os.close(fd)
            try:
                font.save(temporary, reorderTables=None)
                with TTFont(temporary, lazy=True) as checked:
                    for tag, data in original_tables.items():
                        if checked.reader[tag] != data:
                            raise ValueError("Unexpected change to table: " + tag)
                os.replace(temporary, path)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
    print("Variable font bounds: %r -> %r; %.3f seconds." % (old, new, perf_counter()-started))
    return old, new


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: fix_variable_font_bounds.py EXPORTED_FONT.ttf")
    fix_bounds(sys.argv[1])
