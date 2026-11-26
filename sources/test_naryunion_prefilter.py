"""Run with sources/venv/bin/python -m unittest discover -s sources -p test_naryunion_prefilter.py."""

import contextlib
import io
from pathlib import Path
import unittest
from unittest.mock import Mock

import glyphsLib
from glyphsLib.parser import Parser, load_glyphspackage
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.ttLib import TTFont

from naryunion_prefilter import (feature_is_active, set_feature_active,
                                prune_substitutions, subset_for_naryunion,
                                subset_for_operators)


class NaryunionPrefilterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        package = Path(__file__).parent / "SomervilleMath.glyphspackage"
        data = load_glyphspackage(package)
        if data.get(".formatVersion") == 4:
            # glyphsLib needs the v3 node reader for v4's tuple nodes.
            # These tests use glyph names, components and features, not smart axes.
            data[".formatVersion"] = 3
            for key in ("featurePrefixes", "features"):
                for entry in data.get(key, []):
                    if "file" in entry:
                        feature_file = package / "features" / entry.pop("file")
                        entry["code"] = feature_file.read_text(encoding="utf-8")
        cls.font = glyphsLib.GSFont()
        Parser().parse_into_object(cls.font, data)
        # GlyphsApp resolves omitted categories through GlyphData automatically;
        # glyphsLib's file reader leaves them unset.
        for glyph in cls.font.glyphs:
            if glyph.category is None:
                glyph.category = glyphsLib.glyphdata.get_glyph(
                    glyph.name, unicodes=glyph.unicodes
                ).category
        cls.original_export = {g.name: bool(g.export) for g in cls.font.glyphs}
        with contextlib.redirect_stdout(io.StringIO()):
            cls.result = subset_for_naryunion(cls.font)

    def test_letters_preserved_and_unrelated_symbols_disabled(self):
        for glyph in self.font.glyphs:
            if glyph.category in {"Letter", "Number"}:
                self.assertEqual(bool(glyph.export), self.original_export[glyph.name])
        self.assertFalse(self.font.glyphs["rightArrow"].export)

    def test_numerals_and_script_variants_retained(self):
        for name in ("zero", "nine", "zero.ssty1", "nine.ssty2", "zerobold-math"):
            self.assertTrue(self.font.glyphs[name].export, name)

    def test_arithmetic_and_round_square_operator_families_retained(self):
        for name in ("equal", "plus", "minus", "union", "intersection",
                     "naryintersection", "naryintersection.s20", "naryintersection.ss15",
                     "nArySquareUnionOperator", "nArySquareUnionOperator.s20",
                     "nArySquareUnionOperator.ss15.s20",
                     "nArySquareIntersectionOperator", "nArySquareIntersectionOperator.s20",
                     "nArySquareIntersectionOperator.ss15.s20"):
            self.assertTrue(self.font.glyphs[name].export, name)

    def test_union_variants_and_recursive_components_retained(self):
        retained = self.result["retained"]
        for name in ("naryunion", "naryunion.s20", "naryunion.ss15", "naryunion.ss15.s20"):
            self.assertTrue(self.font.glyphs[name].export, name)
        for name in retained:
            glyph = self.font.glyphs[name]
            for layer in glyph.layers:
                for component in layer.components:
                    self.assertIn(component.componentName, retained)
        # Smart component helpers must not become standalone exported glyphs.
        self.assertIn("_smart.naryunion", retained)
        self.assertEqual(bool(self.font.glyphs["_smart.naryunion"].export),
                         self.original_export["_smart.naryunion"])

    def test_big_operator_size_variants_retained(self):
        for family in (
            "naryunion.ssty1", "naryunion.ssty2",
            "product", "coproduct", "nAryTimesOperator",
            "nAryCircledPlusOperator", "nAryCircledPlusOperator.ss16",
            "nAryCircledDotOperator",
            "nAryCircledTimesOperator", "nAryCircledTimesOperator.ss16",
            "nAryUnionOperatorWithPlus", "nAryUnionOperatorWithPlus.ss15",
            "nAryUnionOperatorWithDot", "nAryUnionOperatorWithDot.ss15",
        ):
            for suffix in [""] + [f".s{i:02d}" for i in range(1, 21)]:
                name = family + suffix
                self.assertIn(name, self.result["exporting"])
                self.assertTrue(self.font.glyphs[name].export, name)
                for layer in self.font.glyphs[name].layers:
                    for component in layer.components:
                        self.assertIn(component.componentName, self.result["retained"])

    def test_features_compile_against_exact_subset(self):
        font = TTFont()
        font.setGlyphOrder([".notdef"] + sorted(self.result["exporting"] - {".notdef"}))
        code = "\n".join(p.code for p in self.font.featurePrefixes if not p.disabled)
        for feature in self.font.features:
            if not feature.disabled and feature.code:
                code += "\nfeature %s {\n%s\n} %s;" % (
                    feature.name, feature.code, feature.name
                )
        addOpenTypeFeaturesFromString(font, code)
        tags = {f.FeatureTag for f in font["GSUB"].table.FeatureList.FeatureRecord}
        self.assertIn("ss15", tags)
        self.assertIn("dtls", tags)
        self.assertNotIn("ss17", tags)

    def test_idempotent(self):
        before = self.result["exporting"]
        with contextlib.redirect_stdout(io.StringIO()):
            again = subset_for_naryunion(self.font)
        self.assertEqual(before, again["exporting"])

    def test_rule_filter_fails_closed_for_missing_glyphs_and_complex_lookups(self):
        self.assertEqual(prune_substitutions(
            "sub A by A.alt; sub zero by zero.zero;", {"A", "A.alt"}
        ), "sub A by A.alt;")
        self.assertEqual(prune_substitutions(
            "lookup foo { sub A by A.alt; } foo;", {"A", "A.alt"}
        ), "")

    def test_glyphsapp_feature_activation_uses_property_not_objc_method(self):
        class Feature:
            active = True

            def disabled(self):
                return not self.active

        feature = Feature()
        self.assertTrue(feature_is_active(feature))
        set_feature_active(feature, False)
        self.assertFalse(feature_is_active(feature))
        self.assertTrue(feature.disabled())

    def test_exclusion_removes_glyphs_but_retains_nonexporting_components(self):
        font = glyphsLib.GSFont()
        font.masters.append(glyphsLib.GSFontMaster())
        font.disableUpdateInterface = Mock()
        font.enableUpdateInterface = Mock()
        for name, category, exporting in [
            ("A", "Letter", True), ("naryunion", "Symbol", True),
            ("helper", "Symbol", False), ("rightArrow", "Symbol", True),
            ("unused-helper", "Symbol", False),
        ]:
            glyph = glyphsLib.GSGlyph(name)
            glyph.category = category
            glyph.export = exporting
            font.glyphs.append(glyph)
        layer = glyphsLib.GSLayer()
        layer.layerId = "union-layer"
        layer.components.append(glyphsLib.GSComponent("helper"))
        font.glyphs["naryunion"].layers.append(layer)
        removed_exporting_glyph = font.glyphs["rightArrow"]
        with contextlib.redirect_stdout(io.StringIO()):
            result = subset_for_naryunion(font, exclude=True)
        self.assertEqual({g.name for g in font.glyphs}, {"A", "naryunion", "helper"})
        self.assertEqual(result["exporting"], {"A", "naryunion"})
        self.assertTrue(removed_exporting_glyph.export)
        self.assertFalse(font.glyphs["helper"].export)
        self.assertEqual(result["removed"], 2)
        font.disableUpdateInterface.assert_called_once()
        font.enableUpdateInterface.assert_called_once()

    def test_union_only_omits_letters_but_keeps_variable_design_space(self):
        font = glyphsLib.GSFont()
        for name, category in [("A", "Letter"), ("naryunion", "Symbol"),
                               ("naryunion.s01", "Symbol")]:
            glyph = glyphsLib.GSGlyph(name)
            glyph.category = category
            font.glyphs.append(glyph)
        master = glyphsLib.GSFontMaster()
        font.masters.append(master)
        with contextlib.redirect_stdout(io.StringIO()):
            result = subset_for_naryunion(font, letters=False)
        self.assertEqual(result["exporting"], {"naryunion", "naryunion.s01"})
        self.assertIs(font.masters[0], master)

    def test_operators_subset_keeps_small_operators_and_recursive_helpers(self):
        font = glyphsLib.GSFont()
        font.masters.append(glyphsLib.GSFontMaster())
        font.disableUpdateInterface = Mock()
        font.enableUpdateInterface = Mock()
        wanted = {"A", "zero", "zero.ssty1", "plus", "union", "intersection",
                  "plus.circled", "parallel.circled", "squaredplus",
                  "squaredRisingDiagonalSlash", "squaredSquare", "space", ".notdef"}
        omitted = {"naryunion", "naryunion.s20", "summation", "summation.s04",
                   "product", "coproduct", "integral", "contourIntegral",
                   "nAryCircledPlusOperator", "plus.s01", "rightArrow", "unused-helper",
                   "bigwedge", "bigwedge.ss15"}
        for name in wanted | omitted | {"_operator.circle", "_smart.circle.small"}:
            glyph = glyphsLib.GSGlyph(name)
            glyph.category = "Letter" if name == "A" else "Number" if name.startswith("zero") else "Symbol"
            glyph.subCategory = "Arrow" if name == "rightArrow" else "Math"
            glyph.export = not name.startswith("_") and name != "unused-helper"
            font.glyphs.append(glyph)
        font.glyphs["bigwedge"].unicode = "22C0"
        for parent, child in [("plus.circled", "_operator.circle"),
                              ("_operator.circle", "_smart.circle.small")]:
            layer = glyphsLib.GSLayer()
            layer.components.append(glyphsLib.GSComponent(child))
            font.glyphs[parent].layers.append(layer)
        master = font.masters[0]
        with contextlib.redirect_stdout(io.StringIO()):
            result = subset_for_operators(font, exclude=True)
        self.assertEqual(result["exporting"], wanted)
        self.assertEqual(result["retained"], wanted | {"_operator.circle", "_smart.circle.small"})
        self.assertEqual({g.name for g in font.glyphs}, result["retained"])
        self.assertFalse(font.glyphs["_operator.circle"].export)
        self.assertIs(font.masters[0], master)


if __name__ == "__main__":
    unittest.main()
