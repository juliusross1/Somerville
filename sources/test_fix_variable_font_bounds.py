import contextlib
import io
from pathlib import Path
import tempfile
import unittest

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables.TupleVariation import TupleVariation

from fix_variable_font_bounds import fix_bounds, variable_bounds


def make_font():
    builder = FontBuilder(1000, isTTF=True)
    builder.setupGlyphOrder([".notdef", "u", "mirrored"])
    empty = TTGlyphPen(None).glyph()
    pen = TTGlyphPen(None)
    pen.moveTo((0, 0))
    pen.lineTo((100, 0))
    pen.lineTo((100, 200))
    pen.lineTo((0, 200))
    pen.closePath()
    u = pen.glyph()
    pen = TTGlyphPen({"u": u})
    pen.addComponent("u", (-1, 0, 0, 1, 500, 0))
    builder.setupGlyf({".notdef": empty, "u": u, "mirrored": pen.glyph()})
    builder.setupHorizontalMetrics({n: (600, 0) for n in builder.font.getGlyphOrder()})
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.setupCharacterMap({0x75: "u"})
    builder.setupNameTable({"familyName": "Bounds Test", "styleName": "Regular"})
    builder.setupOS2()
    builder.setupPost()
    builder.setupFvar([("wdth", 0, 0, 1, "Width"), ("opsz", 0, 0, 1, "Optical Size")], [])
    gvar = newTable("gvar")
    # Sparse tuple points exercise IUP; independent axes can act together.
    gvar.variations = {
        ".notdef": [],
        "u": [TupleVariation({"wdth": (0, 1, 1)}, [(250, 0)] + [None]*7),
              TupleVariation({"opsz": (0, 1, 1)}, [(-40, -30)] + [None]*7)],
        "mirrored": [TupleVariation({"wdth": (0, 1, 1)}, [(25, 0)] + [None]*4)],
    }
    builder.font["gvar"] = gvar
    return builder.font


class VariableBoundsTests(unittest.TestCase):
    def test_bounds_enclose_sparse_deltas_and_transformed_components(self):
        font = make_font()
        bounds = variable_bounds(font)
        self.assertEqual(bounds, (-40, -30, 565, 200))
        for width in (0, .3, 1):
            for optical in (0, .6, 1):
                glyphs = font.getGlyphSet(location={"wdth": width, "opsz": optical})
                for name in ("u", "mirrored"):
                    pen = BoundsPen(glyphs)
                    glyphs[name].draw(pen)
                    actual = pen.bounds
                    self.assertLessEqual(bounds[0], actual[0])
                    self.assertLessEqual(bounds[1], actual[1])
                    self.assertGreaterEqual(bounds[2], actual[2])
                    self.assertGreaterEqual(bounds[3], actual[3])

    def test_only_header_changes_and_second_pass_is_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "proof.ttf"
            make_font().save(path)
            with TTFont(path, recalcBBoxes=False, recalcTimestamp=False) as font:
                tables = {tag: font.getTableData(tag) for tag in font.keys()
                          if tag not in {"GlyphOrder", "head"}}
            with contextlib.redirect_stdout(io.StringIO()):
                old, new = fix_bounds(path)
                again = fix_bounds(path)
            self.assertNotEqual(old, new)
            self.assertEqual(again, (new, new))
            with TTFont(path) as font:
                for tag, data in tables.items():
                    self.assertEqual(font.getTableData(tag), data, tag)


if __name__ == "__main__":
    unittest.main()
