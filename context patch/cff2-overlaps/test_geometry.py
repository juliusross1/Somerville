#!/usr/bin/env python3
"""Geometry regression tests. Run with the project's sources/venv/bin/python."""
import itertools
import importlib.util
import json
import math
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

import pathops
_spec = importlib.util.spec_from_file_location('cff2_overlap_helper', Path(__file__).with_name('font-cff-overlaps.py'))
helper = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(helper)


def rectangle(x, y, w, h, reverse=False):
    points = [(x,y), (x+w,y), (x+w,y+h), (x,y+h)]
    if reverse:
        points.reverse()
    return [[*p, "m" if i == 0 else "l"] for i,p in enumerate(points)]


def cff1_quantized_segments(segments):
    """Model ConTeXt's current relative-delta 16.16 charstring encoder."""
    theoretical = (0,0)
    actual = (0,0)
    result = []
    for segment in segments:
        points = list(zip(segment[:-1:2], segment[1:-1:2]))
        converted = []
        for point in points:
            actual = tuple(a + math.floor((b-c)*65536)/65536 for a,b,c in zip(actual,point,theoretical))
            theoretical = point
            converted.extend(actual)
        result.append([*converted, segment[-1]])
    return result


class GeometryTests(unittest.TestCase):
    def assertEquivalent(self, segments, expect_changed=None):
        result, changed = helper.resolve_segments(segments)
        if expect_changed is not None:
            self.assertEqual(changed, expect_changed)
        original = helper.segments_to_path(segments)
        output = helper.segments_to_path(result)
        output.fillType = pathops.FillType.EVEN_ODD
        difference = pathops.op(original, output, pathops.PathOp.XOR)
        bounds = original.controlPointBounds
        scale = max(1, (bounds[2]-bounds[0])*(bounds[3]-bounds[1]))
        area = sum(abs(p.area) for p in difference.contours)
        self.assertLessEqual(area, scale * 2e-6, f"visible region differs by area {area}")
        quantized = helper.segments_to_path(cff1_quantized_segments(result))
        quantized.fillType = pathops.FillType.EVEN_ODD
        # Existing encoder truncates each relative delta to 16.16, so errors
        # can accumulate. Bound the geometric effect using perimeter and the
        # worst accumulated coordinate error for this glyph.
        perimeter_bound = sum(math.hypot(bounds[2]-bounds[0], bounds[3]-bounds[1]) for s in result)
        error = max(1, len(result)*3) / 65536
        self.assertLessEqual(abs(abs(output.area) - abs(quantized.area)),
                             scale * 2e-6 + perimeter_bound * error * 2)
        # Compare independent point membership as well as the boolean-XOR area.
        rng = random.Random(6128)
        for _ in range(300):
            x = rng.uniform(bounds[0]-1, bounds[2]+1)
            y = rng.uniform(bounds[1]-1, bounds[3]+1)
            self.assertEqual(original.contains((x,y)), output.contains((x,y)))
            self.assertEqual(original.contains((x,y)), quantized.contains((x,y)))
        # Simplification must be stable after passing the JSON protocol.
        again, second_changed = helper.resolve_segments(json.loads(json.dumps(result)))
        repeated = helper.segments_to_path(again)
        repeated.fillType = pathops.FillType.EVEN_ODD
        repeat_difference = pathops.op(output, repeated, pathops.PathOp.XOR)
        self.assertLessEqual(sum(abs(p.area) for p in repeat_difference.contours), scale * 2e-6)
        return result, changed

    def test_plain_rectangle_is_unchanged(self):
        original = rectangle(0.125, 0.25, 101.5, 43.5)
        result, changed = self.assertEquivalent(original, False)
        self.assertIs(result, original)

    def test_inexact_float32_coordinates_cannot_bypass_conversion(self):
        self.assertEquivalent(rectangle(0.123456789, 0.1, 101.23456789, 43.5), True)
        # At x=1000 the overlap is smaller than one float32 ulp. Converting
        # before comparison hides it; retaining the original charstring would
        # retain the invalid-for-CFF1 overlap. Ensure it is rebuilt instead.
        self.assertEquivalent(rectangle(0,0,1000,1000) + rectangle(999.999999,0,1000,1000), True)

    def test_disjoint_contours_are_unchanged(self):
        self.assertEquivalent(rectangle(0,0,10,10) + rectangle(20,0,10,10), False)

    def test_same_winding_overlapping_rectangles(self):
        result, _ = self.assertEquivalent(rectangle(0,0,10,10) + rectangle(5,5,10,10), True)
        self.assertAlmostEqual(abs(helper.segments_to_path(result).area), 175)

    def test_nested_same_winding_is_solid(self):
        result, _ = self.assertEquivalent(rectangle(0,0,10,10) + rectangle(2,2,6,6), True)
        self.assertTrue(helper.segments_to_path(result).contains((5,5)))

    def test_opposite_winding_nested_preserves_hole(self):
        result, _ = self.assertEquivalent(rectangle(0,0,10,10) + rectangle(2,2,6,6,True), False)
        self.assertFalse(helper.segments_to_path(result).contains((5,5)))

    def test_opposite_winding_partial_overlap_cancels(self):
        self.assertEquivalent(rectangle(0,0,10,10) + rectangle(5,5,10,10,True), True)

    def test_exact_opposite_duplicates_become_empty(self):
        result, _ = self.assertEquivalent(rectangle(0,0,10,10) + rectangle(0,0,10,10,True), True)
        self.assertEqual(result, [])

    def test_shared_edge_and_shared_point(self):
        self.assertEquivalent(rectangle(0,0,10,10) + rectangle(10,0,10,10), True)
        self.assertEquivalent(rectangle(0,0,10,10) + rectangle(10,10,10,10))

    def test_island_inside_counter(self):
        self.assertEquivalent(rectangle(0,0,100,100) + rectangle(10,10,80,80,True) + rectangle(30,30,40,40), False)

    def test_ring_and_cross_gives_four_holes(self):
        shape = rectangle(0,0,100,100) + rectangle(15,15,70,70,True)
        shape += rectangle(40,0,20,100) + rectangle(0,40,100,20)
        result, _ = self.assertEquivalent(shape, True)
        path = helper.segments_to_path(result)
        self.assertEqual(len(list(path.contours)), 5)
        self.assertTrue(path.contains((50,50)))
        self.assertFalse(path.contains((25,25)))

    def test_self_intersecting_bowtie(self):
        self.assertEquivalent([[0,0,"m"],[10,10,"l"],[0,10,"l"],[10,0,"l"]], True)

    def test_fractional_tiny_counters_and_near_coincidence(self):
        self.assertEquivalent(rectangle(0.03125,0.0625,1000,1000) + rectangle(400.03125,400.0625,0.125,0.25,True), False)
        self.assertEquivalent(rectangle(0,0,1000,1000) + rectangle(999.875,0.0625,20.03125,999.875), True)

    def test_empty_and_degenerate(self):
        self.assertEquivalent([], False)
        self.assertEquivalent([[0,0,"m"],[0,0,"l"]], True)

    def test_closed_cubic_retains_curves(self):
        # Two intersecting closed cubic loops.
        shape = [[0,0,"m"],[0,100,100,100,100,0,"c"],[100,-100,0,-100,0,0,"c"]]
        shape += [[50,0,"m"],[50,100,150,100,150,0,"c"],[150,-100,50,-100,50,0,"c"]]
        result, _ = self.assertEquivalent(shape, True)
        self.assertIn("c", [s[-1] for s in result])

    def test_invalid_requests(self):
        for segments in ([[1,2,"l"]], [[float("nan"),0,"m"]], [[0,0,"m"],[1,2,"q"]], [[True,0,"m"]]):
            with self.assertRaises(ValueError):
                helper.resolve_segments(segments)
        for request in ({}, {"protocol":2,"glyphs":[]}, {"protocol":1,"glyphs":[{"id":0,"segments":[]},{"id":0,"segments":[]}]}):
            with self.assertRaises(ValueError):
                helper.process_request(request)

    def test_independent_runtime_guard_rejects_missing_contour(self):
        original = rectangle(0,0,100,100) + rectangle(20,20,60,60,True)
        wrong = rectangle(20,20,60,60)
        reference,tolerance = helper.validation_reference(original,helper.segments_to_path(original))
        self.assertIsNotNone(helper.validate_result(original,wrong,reference,tolerance))

    def test_runtime_guard_rejects_missing_tiny_triangle_counter(self):
        wrong = rectangle(0,0,1000,1000)
        original = wrong + [[100,100,'m'],[100,100.1,'l'],[100.1,100,'l']]
        reference,tolerance = helper.validation_reference(original,helper.segments_to_path(original))
        self.assertIsNotNone(helper.validate_result(original,wrong,reference,tolerance))

    def test_robust_cubic_ray_predicate(self):
        shape = [[0,0,'m'],[0,100,100,100,100,0,'c'],[100,-100,0,-100,0,0,'c']]
        self.assertTrue(helper.robust_point_inside(shape,(50,74.875)))
        self.assertFalse(helper.robust_point_inside(shape,(50,75.125)))

    def test_protocol_batch_and_cli_failure(self):
        request = {"protocol":1,"glyphs":[{"id":0,"segments":rectangle(0,0,10,10)}, {"id":"empty","segments":[]}]}
        result = helper.process_request(request)
        self.assertEqual(result["stats"]["glyphs"], 2)
        self.assertEqual(result["stats"]["changed"], 0)
        with tempfile.TemporaryDirectory() as d:
            source, output = Path(d)/"input.json", Path(d)/"output.json"
            source.write_text(json.dumps(request))
            run = subprocess.run([sys.executable, str(Path(helper.__file__)), str(source), str(output)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(json.loads(output.read_text())["glyphs"], result["glyphs"])
            source.write_text('{"protocol":1,"glyphs":[{"id":6,"segments":[[0,0,"z"]]}]}')
            output.unlink()
            run = subprocess.run([sys.executable, str(Path(helper.__file__)), str(source), str(output)], capture_output=True, text=True)
            self.assertNotEqual(run.returncode, 0)
            self.assertIn("glyph 6", run.stderr)
            self.assertFalse(output.exists())

    def test_real_somerville_glyphs_at_axis_locations(self):
        from fontTools.ttLib import TTFont
        from fontTools.pens.recordingPen import RecordingPen
        candidates = [Path('/Users/juliusross/Documents/fontoutputs/SomervilleMathCFFtestVF.otf'),
                      Path('/Users/juliusross/Documents/fontoutputs/SomervilleMathVF.otf')]
        tested = changed = 0
        for filename in candidates:
            if not filename.exists():
                continue
            font = TTFont(filename)
            self.assertIn('CFF2', font)
            axes = font['fvar'].axes
            locations = [{a.axisTag:a.defaultValue for a in axes}]
            if len(axes) <= 3:
                locations += [{a.axisTag:(a.minValue if bit == 0 else a.maxValue) for a,bit in zip(axes,bits)} for bits in itertools.product((0,1), repeat=len(axes))]
            else:
                defaults = locations[0]
                locations += [dict(defaults, **{a.axisTag:v}) for a in axes for v in (a.minValue,a.maxValue)]
                locations += [{a.axisTag:getattr(a,extreme) for a in axes} for extreme in ('minValue','maxValue')]
            locations += [{a.axisTag:(a.minValue+a.maxValue)/2 for a in axes}]
            names = font.getGlyphOrder()
            if len(names) > 100:
                names = [n for n in names if n in ('A','B','O','e','g') or 'circledplus' in n.lower() or n == 'uni2A01']
            for location in locations:
                glyphset = font.getGlyphSet(location=location)
                for name in names:
                    pen = RecordingPen();glyphset[name].draw(pen)
                    segments = []
                    for op,points in pen.value:
                        if op in ('closePath','endPath'):
                            continue
                        self.assertIn(op, ('moveTo','lineTo','curveTo'))
                        segments.append([*(v for point in points for v in point), {'moveTo':'m','lineTo':'l','curveTo':'c'}[op]])
                    with self.subTest(font=filename.name, glyph=name, location=location):
                        _, did_change = self.assertEquivalent(segments)
                    tested += 1;changed += did_change
        self.assertGreater(tested, 0, 'No Somerville CFF2 export available')
        print(f'\nActual exported outlines: {tested} instances checked; {changed} changed', flush=True)

    def test_all_somerville_glyphs_default_and_nondefault(self):
        from fontTools.ttLib import TTFont
        from fontTools.pens.recordingPen import RecordingPen
        filename = Path('/Users/juliusross/Documents/fontoutputs/SomervilleMathVF.otf')
        if not filename.exists():
            self.skipTest('Full Somerville CFF2 export unavailable')
        font = TTFont(filename)
        requested = {'wdth':104,'wght':630,'opsz':80,'MGHT':630,'ARLN':400,'ARHD':200,'STYA':60,'STYB':60,'INSL':50}
        axes = font['fvar'].axes
        defaults = {a.axisTag:a.defaultValue for a in axes}
        nondefault = {a.axisTag:min(a.maxValue,max(a.minValue,requested.get(a.axisTag,a.defaultValue))) for a in axes}
        for location in (defaults,nondefault):
            glyphset = font.getGlyphSet(location=location)
            changed = 0
            for name in font.getGlyphOrder():
                pen = RecordingPen();glyphset[name].draw(pen)
                segments = [[*(v for point in points for v in point),{'moveTo':'m','lineTo':'l','curveTo':'c'}[op]]
                            for op,points in pen.value if op not in ('closePath','endPath')]
                with self.subTest(glyph=name, location=location):
                    _, did_change = self.assertEquivalent(segments)
                changed += did_change
            print(f'\nFull font: {len(font.getGlyphOrder())} glyphs, {changed} rebuilt, location {location}', flush=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
