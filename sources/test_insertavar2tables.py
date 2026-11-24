"""Regression checks for the exported font's user-facing axis mappings.

Run: sources/venv/bin/python -m unittest discover -s sources -p test_insertavar2tables.py
"""

import contextlib
import io
from pathlib import Path
import tempfile
import unittest

from fontTools.misc.roundTools import otRound
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont
from fontTools.varLib.models import normalizeValue, piecewiseLinearMap
from fontTools.varLib.varStore import VarStoreInstancer

import insertavar2tables as converter


ROOT = Path(__file__).resolve().parent.parent
FRESH_FONT = ROOT / "fonts/SomervilleMath/SomervilleMathVF.ttf"


class MathWeightMappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.path = Path(cls.temporary.name) / "mapped.ttf"
        with contextlib.redirect_stdout(io.StringIO()):
            converter.insert_avar2_tables(FRESH_FONT, output=cls.path)
        cls.original = TTFont(FRESH_FONT)
        cls.font = TTFont(cls.path)

    @classmethod
    def tearDownClass(cls):
        cls.original.close()
        cls.font.close()
        cls.temporary.cleanup()

    def internal_weight(self, user):
        return 360 + 540 * self.original.normalizeLocation({"wght": user}).get("wght", 0)

    def internal_math_weight(self, user_weight, strength):
        location = self.font.normalizeLocation({"wght": user_weight, "MGHT": strength})
        return 360 + 540 * location.get("MGHT", 0)

    def test_endpoints_default_and_piecewise_interpolation(self):
        # An independent evaluation of the requested design-space formula,
        # including between avar1 knots and around the upper clamp.
        weights = [360, 370, 400, 475, 500, 600, 700, 749.9, 750, 750.1, 800, 900]
        strengths = [0, 0.1, 12.5, 25, 49.9, 50, 50.1, 75, 99.9, 100]
        for weight in weights:
            middle = min(self.internal_weight(weight) + 200, 900)
            for strength in strengths:
                with self.subTest(weight=weight, strength=strength):
                    if strength <= 50:
                        expected = 360 + strength / 50 * (middle - 360)
                    else:
                        expected = middle + (strength - 50) / 50 * (900 - middle)
                    self.assertAlmostEqual(self.internal_math_weight(weight, strength), expected, delta=0.1)

    def test_omitted_axes_use_the_new_default(self):
        for location, expected in [({}, 560), ({"wght": 400}, 600), ({"MGHT": 0}, 360), ({"MGHT": 100}, 900)]:
            actual = 360 + 540 * self.font.normalizeLocation(location).get("MGHT", 0)
            self.assertAlmostEqual(actual, expected, delta=0.1)

    def test_bold_glyph_outlines_at_equivalent_internal_locations(self):
        inverse = {v: k for k, v in self.original['avar'].segments['MGHT'].items()}
        for weight, strength in [(360, 0), (360, 50), (400, 25), (400, 50), (400, 75), (900, 100)]:
            middle = min(self.internal_weight(weight) + 200, 900)
            expected = (360 + strength / 50 * (middle - 360) if strength <= 50
                        else middle + (strength - 50) / 50 * (900 - middle))
            old_user = 360 + 540 * piecewiseLinearMap((expected - 360) / 540, inverse)
            old_glyphs = self.original.getGlyphSet(location={'wght': weight, 'MGHT': old_user})
            new_glyphs = self.font.getGlyphSet(location={'wght': weight, 'MGHT': strength})
            for codepoint in (0x1D400, 0x1D401, 0x1D7CE):  # Bold A, B, and zero.
                glyph = self.font.getBestCmap()[codepoint]
                before, after = BoundsPen(old_glyphs), BoundsPen(new_glyphs)
                old_glyphs[glyph].draw(before)
                new_glyphs[glyph].draw(after)
                for a, b in zip(before.bounds, after.bounds):
                    self.assertAlmostEqual(a, b, delta=0.25)

    def test_user_metadata_and_all_named_instances(self):
        axis = self.font['fvar'].getAxes()['MGHT']
        self.assertEqual(axis, (0, 50, 100))
        self.assertGreater(len(self.font['fvar'].instances), 0)
        for instance in self.font['fvar'].instances:
            self.assertEqual(instance.coordinates['MGHT'], 50)
        stat = self.font['STAT'].table
        index = next(i for i, axis in enumerate(stat.DesignAxisRecord.Axis) if axis.AxisTag == 'MGHT')
        values = [v.Value for v in stat.AxisValueArray.AxisValue if v.Format == 1 and v.AxisIndex == index]
        self.assertEqual(values, [0, 25, 50, 75, 100])

    def test_stat_guide_labels_and_regular_flags(self):
        stat = self.font['STAT'].table
        tags = [a.AxisTag for a in stat.DesignAxisRecord.Axis]
        actual = {}
        for value in stat.AxisValueArray.AxisValue:
            if value.Format == 1:
                actual.setdefault(tags[value.AxisIndex], []).append(
                    (value.Value, self.font['name'].getDebugName(value.ValueNameID), value.Flags))
        self.assertEqual(actual['wght'], [(360, 'SemiLight', 0), (400, 'Regular', 2),
            (500, 'Medium', 0), (600, 'SemiBold', 0), (700, 'Bold', 0),
            (800, 'ExtraBold', 0), (900, 'Black', 0)])
        for tag, default in {'wdth': 100, 'wght': 400, 'MGHT': 50, 'opsz': 12,
                             'INSL': 0, 'ARLN': 100, 'ARHD': 100}.items():
            self.assertEqual([(v, n) for v, n, flags in actual[tag] if flags & 2],
                             [(default, 'Regular')])
        self.assertEqual([(v, n) for v, n, _ in actual['ARHD']],
                         [(100, 'Regular'), (150, 'Larger'), (200, 'Largest')])
        self.assertNotIn('ital', tags)
        self.assertEqual(stat.DesignAxisCount, len(tags))
        self.assertEqual(stat.AxisValueCount, len(stat.AxisValueArray.AxisValue))
        for tag in ('STYA', 'STYB'):
            def records(font):
                table = font['STAT'].table
                index = next(i for i, a in enumerate(table.DesignAxisRecord.Axis) if a.AxisTag == tag)
                return [vars(v) for v in table.AxisValueArray.AxisValue
                        if v.Format != 4 and v.AxisIndex == index]
            self.assertEqual(records(self.original), records(self.font))

    def test_italic_removal_reindexes_values_when_italic_is_first(self):
        source = Path(self.temporary.name) / 'italic-first.ttf'
        output = Path(self.temporary.name) / 'italic-removed.ttf'
        with TTFont(FRESH_FONT) as font:
            stat = font['STAT'].table
            axes = stat.DesignAxisRecord.Axis
            italic = next(i for i, a in enumerate(axes) if a.AxisTag == 'ital')
            order = [italic] + [i for i in range(len(axes)) if i != italic]
            indices = {old: new for new, old in enumerate(order)}
            stat.DesignAxisRecord.Axis = [axes[i] for i in order]
            for value in stat.AxisValueArray.AxisValue:
                records = value.AxisValueRecord if value.Format == 4 else [value]
                for record in records:
                    record.AxisIndex = indices[record.AxisIndex]
            font.save(source)
        with contextlib.redirect_stdout(io.StringIO()):
            converter.insert_avar2_tables(source, output=output)
        with TTFont(output) as font:
            self.assertEqual(font.getTableData('STAT'), self.font.getTableData('STAT'))

    def test_unrelated_tables_and_mappings_are_preserved(self):
        for tag in self.original.keys():
            if tag not in ('GlyphOrder', 'head', 'avar', 'fvar', 'STAT', 'name'):
                # Compare saved bytes; inspecting outlines/cmaps in another
                # test can change how FontTools recompiles a loaded table.
                self.assertEqual(self.original.reader[tag], self.font.reader[tag], tag)
        for tag, segments in self.original['avar'].segments.items():
            if tag not in ('MGHT', 'wdth'):
                self.assertEqual(segments, self.font['avar'].segments[tag], tag)

    def test_script_axes_still_follow_optical_size(self):
        rows = converter.load_rows(converter.DEFAULT_CSV)
        for row in rows:
            # Exercise the v2 script-axis mapping in post-avar1 space so it is
            # independent of the exporter's optical-size segment quantization.
            for strength in (0, 50, 100):
                location = {'opsz': converter.fixed(converter.normalized(row['output_opsz'])),
                            'MGHT': normalizeValue(strength, (0, 50, 100)),
                            'STYA': 0.37, 'STYB': 0.81}
                axes = self.font['fvar'].axes
                store = VarStoreInstancer(self.font['avar'].table.VarStore, axes, location)
                for tag in converter.DRIVEN:
                    index = next(i for i, axis in enumerate(axes) if axis.axisTag == tag)
                    actual = (otRound(location[tag] * converter.SCALE) + otRound(store[index])) / converter.SCALE
                    expected = converter.normalized(row[f'output_{tag}'])
                    self.assertAlmostEqual(actual, expected, delta=converter.TOLERANCE)

    def test_converting_again_is_rejected_without_replacing_output(self):
        destination = Path(self.temporary.name) / 'untouched.ttf'
        destination.write_bytes(b'original destination')
        with self.assertRaisesRegex(ValueError, 'avar v1'):
            converter.insert_avar2_tables(self.path, output=destination)
        self.assertEqual(destination.read_bytes(), b'original destination')


if __name__ == '__main__':
    unittest.main()
