#MenuTitle: Check Arrows
# -*- coding: utf-8 -*-

"""Run read-only consistency reports for Mayfair's horizontal arrows.

This script never changes glyphs or layers. Its first report checks the advance
widths of the short and long arrow heads and ends listed in ``arrow.md``.
Its second report checks the advance
width of every master layer for the Unicode arrows in ``ARROW_CHARACTERS``.
Standard arrows are compared with ``StandardArrowLength`` and the explicitly
listed long arrows with ``LongArrowLength``. Expected values are resolved from
``recipe_constants.plist`` using its global constants, wildcard master groups,
and master-specific overrides, in the same order used by the recipe system.

Intermediate and other special layers are deliberately excluded from this
width report. Every discrepancy reports the glyph, Unicode, master, expected
width, actual width, and signed difference ``actual - expected``. Missing
glyphs, missing master layers, and unresolved constants are also reported.
"""

import os
import plistlib
from fnmatch import fnmatchcase

from GlyphsApp import Glyphs, Message


ARROW_CHARACTERS = (
    "←→↔↢↣⤔⤕⤙⤚⤛⤜⬹⬺↞↠⤀⤁⤖⤗⤘⬴⬽⬻⬵↼↽⇀⇁⥊⥋⥎⥐⥒⥓⥖⥗"
    "⇤⇥↤↦⟻⟼⟽⟾⤅⤆⤇⥚⥛⥞⥟↹⇄⇆⇇⇉⇋⇌⥢⥤⥦⥧⥨⥩⥪⥫⥬⥭"
    "⇍⇎⇏⇐⇒⇔⇺⇻⟸⟹⟺⤂⤃⤄⟵⟶⟷↮⇷⇸⇹↚↛"
)
LONG_ARROW_CHARACTERS = "⟵⟶⟷⟸⟹⟺⟻⟼⟽⟾"
SHORT_HEAD_AND_END_GLYPHS = (
    "rightArrow.lft",
    "FrombarArrowEnd.lft",
    "FrombarDoubleArrowEnd.lft",
    "DoubleArrowEnd.lft",
    "rightArrow.rgt",
    "rightDoubleArrow.rgt",
    "harpoonrightup.rgt",
    "DoubleArrowHead.rgt",
)
LONG_HEAD_AND_END_GLYPHS = (
    "ArrowEnd.lft",
    "twoheadrightarrow.rgt",
    "rightTabHarpoonUpArrow.rgt",
    "rightTabArrow.rgt",
)
WIDTH_TOLERANCE = 0.001
LARGE_DISCREPANCY_THRESHOLD = 1.0
CONSTANTS_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "recipes", "recipe_constants.plist")
)


def format_number(value, signed=False):
    number = float(value)
    if abs(number) <= WIDTH_TOLERANCE:
        number = 0.0
    if number.is_integer():
        result = str(int(number))
    else:
        result = "%g" % number
    if signed and number > 0:
        result = "+" + result
    return result


def glyph_for_unicode(font, character):
    unicode_value = "%04X" % ord(character)
    try:
        glyph = font.glyphForUnicode_(unicode_value)
        if glyph is not None:
            return glyph
    except Exception:
        pass
    for glyph in font.glyphs:
        unicodes = []
        try:
            if glyph.unicode:
                unicodes.append(str(glyph.unicode).upper())
        except Exception:
            pass
        try:
            unicodes.extend(str(value).upper() for value in glyph.unicodes if value)
        except Exception:
            pass
        if unicode_value in unicodes:
            return glyph
    return None


def master_layer(glyph, master):
    try:
        layer = glyph.layers[master.id]
        if layer is not None:
            return layer
    except Exception:
        pass
    for layer in glyph.layers:
        try:
            if bool(layer.isMasterLayer) and str(layer.layerId) == str(master.id):
                return layer
        except Exception:
            pass
    return None


def load_constants():
    with open(CONSTANTS_PATH, "rb") as handle:
        data = plistlib.load(handle)
    constants = data.get("constants", {})
    groups = data.get("masterGroups", [])
    overrides = data.get("masterOverrides", {})
    if not isinstance(constants, dict):
        raise RuntimeError("The constants entry must be a dictionary.")
    if not isinstance(groups, list):
        raise RuntimeError("The masterGroups entry must be an array.")
    if not isinstance(overrides, dict):
        raise RuntimeError("The masterOverrides entry must be a dictionary.")
    return constants, groups, overrides


def resolved_constant(name, master, constants, groups, overrides):
    found = name in constants
    value = constants.get(name)
    source = "global constants"
    master_name = str(master.name or "")
    master_id = str(master.id or "")
    for group in groups:
        pattern = str(group.get("match", ""))
        group_constants = group.get("constants", {})
        if (
            pattern
            and isinstance(group_constants, dict)
            and fnmatchcase(master_name.lower(), pattern.lower())
            and name in group_constants
        ):
            value = group_constants[name]
            source = "master group %s" % pattern
            found = True
    for key in (master_name, master_id):
        master_constants = overrides.get(key)
        if isinstance(master_constants, dict) and name in master_constants:
            value = master_constants[name]
            source = "master override %s" % key
            found = True
    if not found:
        raise RuntimeError("No %s value matches master %s." % (name, master_name))
    try:
        return float(value), source
    except Exception:
        raise RuntimeError(
            "%s for master %s is not numeric: %r" % (name, master_name, value)
        )


def report_head_and_end_widths(font, constants, groups, overrides):
    print("\n" + "=" * 78)
    print("REPORT 1 — MASTER-LAYER ARROW HEAD AND END WIDTHS")
    print("=" * 78)
    print("Classification source: sources/Settings/arrow.md")
    print("Intermediate and special layers: not checked")
    print("Short glyphs (%i): %s" % (
        len(SHORT_HEAD_AND_END_GLYPHS),
        ", ".join(SHORT_HEAD_AND_END_GLYPHS),
    ))
    print("Long glyphs (%i): %s" % (
        len(LONG_HEAD_AND_END_GLYPHS),
        ", ".join(LONG_HEAD_AND_END_GLYPHS),
    ))

    checked = 0
    discrepancies = []
    missing_glyphs = []
    missing_layers = []
    constant_errors = []
    categories = (
        (SHORT_HEAD_AND_END_GLYPHS, "ShortHeadsandEnds", "short"),
        (LONG_HEAD_AND_END_GLYPHS, "LongHeadsandEnds", "long"),
    )

    expected_by_master = {}
    for master in font.masters:
        expected_by_master[str(master.id)] = {}
        for constant_name in ("ShortHeadsandEnds", "LongHeadsandEnds"):
            try:
                value, source = resolved_constant(
                    constant_name, master, constants, groups, overrides
                )
                expected_by_master[str(master.id)][constant_name] = value
                print(
                    "  CONSTANT %-45s %-20s = %s (%s)"
                    % (master.name, constant_name, format_number(value), source)
                )
            except Exception as error:
                constant_errors.append(
                    "%s / %s: %s" % (master.name, constant_name, error)
                )

    for glyph_names, constant_name, category in categories:
        for glyph_name in glyph_names:
            try:
                glyph = font.glyphs[glyph_name]
            except Exception:
                glyph = None
            if glyph is None:
                missing_glyphs.append("/%s (%s)" % (glyph_name, category))
                continue
            for master in font.masters:
                layer = master_layer(glyph, master)
                if layer is None:
                    missing_layers.append("/%s / %s" % (glyph_name, master.name))
                    continue
                expected = expected_by_master.get(str(master.id), {}).get(
                    constant_name
                )
                if expected is None:
                    continue
                checked += 1
                actual = float(layer.width)
                difference = actual - expected
                if abs(difference) > WIDTH_TOLERANCE:
                    discrepancies.append(
                        {
                            "glyph": glyph_name,
                            "master": master.name,
                            "category": category,
                            "constant": constant_name,
                            "expected": expected,
                            "actual": actual,
                            "difference": difference,
                        }
                    )

    print("\nDISCREPANCIES: %i" % len(discrepancies))
    if not discrepancies:
        print("  None. All %i checked master layers have the expected width." % checked)
    for item in discrepancies:
        print(
            "  /%-36s | %-42s | %s: expected %s (%s), actual %s, discrepancy %s"
            % (
                item["glyph"],
                item["master"],
                item["category"],
                format_number(item["expected"]),
                item["constant"],
                format_number(item["actual"]),
                format_number(item["difference"], signed=True),
            )
        )
    large_discrepancy_count = sum(
        abs(item["difference"]) > LARGE_DISCREPANCY_THRESHOLD
        for item in discrepancies
    )
    print(
        "DISCREPANCIES LARGER THAN ±%s: %i"
        % (format_number(LARGE_DISCREPANCY_THRESHOLD), large_discrepancy_count)
    )

    print("\nMISSING GLYPHS: %i" % len(missing_glyphs))
    for item in missing_glyphs:
        print("  %s" % item)
    print("MISSING MASTER LAYERS: %i" % len(missing_layers))
    for item in missing_layers:
        print("  %s" % item)
    print("CONSTANT ERRORS: %i" % len(constant_errors))
    for item in constant_errors:
        print("  %s" % item)
    print("MASTER LAYERS CHECKED: %i" % checked)

    return {
        "checked": checked,
        "discrepancies": len(discrepancies),
        "largeDiscrepancies": large_discrepancy_count,
        "missingGlyphs": len(missing_glyphs),
        "missingLayers": len(missing_layers),
        "constantErrors": len(constant_errors),
    }


def report_master_widths(font, constants, groups, overrides):
    print("\n" + "=" * 78)
    print("REPORT 2 — MASTER-LAYER COMPLETE ARROW WIDTHS")
    print("=" * 78)
    print("Constants file: %s" % CONSTANTS_PATH)
    print("Intermediate and special layers: not checked")
    print("Long-arrow Unicode set: %s" % LONG_ARROW_CHARACTERS)

    checked = 0
    discrepancies = []
    missing_glyphs = []
    missing_layers = []
    constant_errors = []

    expected_by_master = {}
    for master in font.masters:
        expected_by_master[str(master.id)] = {}
        for constant_name in ("StandardArrowLength", "LongArrowLength"):
            try:
                value, source = resolved_constant(
                    constant_name, master, constants, groups, overrides
                )
                expected_by_master[str(master.id)][constant_name] = value
                print(
                    "  CONSTANT %-45s %-20s = %s (%s)"
                    % (
                        master.name,
                        constant_name,
                        format_number(value),
                        source,
                    )
                )
            except Exception as error:
                constant_errors.append("%s / %s: %s" % (master.name, constant_name, error))

    for character in ARROW_CHARACTERS:
        unicode_label = "U+%04X" % ord(character)
        glyph = glyph_for_unicode(font, character)
        if glyph is None:
            missing_glyphs.append("%s %s" % (character, unicode_label))
            continue
        constant_name = (
            "LongArrowLength"
            if character in LONG_ARROW_CHARACTERS
            else "StandardArrowLength"
        )
        for master in font.masters:
            layer = master_layer(glyph, master)
            if layer is None:
                missing_layers.append(
                    "%s %s (%s) / %s"
                    % (character, unicode_label, glyph.name, master.name)
                )
                continue
            expected = expected_by_master.get(str(master.id), {}).get(constant_name)
            if expected is None:
                continue
            checked += 1
            actual = float(layer.width)
            difference = actual - expected
            if abs(difference) > WIDTH_TOLERANCE:
                discrepancies.append(
                    {
                        "character": character,
                        "unicode": unicode_label,
                        "glyph": glyph.name,
                        "master": master.name,
                        "constant": constant_name,
                        "expected": expected,
                        "actual": actual,
                        "difference": difference,
                    }
                )

    print("\nDISCREPANCIES: %i" % len(discrepancies))
    if not discrepancies:
        print("  None. All %i checked master layers have the expected width." % checked)
    for item in discrepancies:
        print(
            "  %s %s %-34s | %-42s | expected %s (%s), actual %s, discrepancy %s"
            % (
                item["character"],
                item["unicode"],
                item["glyph"],
                item["master"],
                format_number(item["expected"]),
                item["constant"],
                format_number(item["actual"]),
                format_number(item["difference"], signed=True),
            )
        )
    large_discrepancy_count = sum(
        abs(item["difference"]) > LARGE_DISCREPANCY_THRESHOLD
        for item in discrepancies
    )
    print(
        "DISCREPANCIES LARGER THAN ±%s: %i"
        % (format_number(LARGE_DISCREPANCY_THRESHOLD), large_discrepancy_count)
    )

    print("\nMISSING GLYPHS: %i" % len(missing_glyphs))
    for item in missing_glyphs:
        print("  %s" % item)
    print("MISSING MASTER LAYERS: %i" % len(missing_layers))
    for item in missing_layers:
        print("  %s" % item)
    print("CONSTANT ERRORS: %i" % len(constant_errors))
    for item in constant_errors:
        print("  %s" % item)
    print("MASTER LAYERS CHECKED: %i" % checked)

    return {
        "checked": checked,
        "discrepancies": len(discrepancies),
        "largeDiscrepancies": large_discrepancy_count,
        "missingGlyphs": len(missing_glyphs),
        "missingLayers": len(missing_layers),
        "constantErrors": len(constant_errors),
    }


def main():
    font = Glyphs.font
    Glyphs.clearLog()
    Glyphs.showMacroWindow()
    print("CHECK ARROWS — READ-ONLY REPORTS")
    if font is None:
        print("ABORTED: no font is open.")
        Message("Check Arrows", "Open a font before running this script.")
        return
    print("Font: %s" % (font.familyName or "unnamed font"))
    print("Arrow characters in inventory: %i" % len(ARROW_CHARACTERS))
    try:
        constants, groups, overrides = load_constants()
        head_end_result = report_head_and_end_widths(
            font, constants, groups, overrides
        )
        arrow_result = report_master_widths(font, constants, groups, overrides)
    except Exception as error:
        print("\nABORTED: %s" % error)
        Message("Check Arrows", "Could not run the report. See the Macro window.")
        return

    results = (head_end_result, arrow_result)
    checked_count = sum(result["checked"] for result in results)
    problem_count = sum(
        result["discrepancies"]
        + result["missingGlyphs"]
        + result["missingLayers"]
        + result["constantErrors"]
        for result in results
    )
    large_discrepancy_count = sum(
        result["largeDiscrepancies"] for result in results
    )
    print("\n" + "=" * 78)
    print("CHECK ARROWS COMPLETE — %i problem(s) reported" % problem_count)
    print(
        "WIDTH DISCREPANCIES LARGER THAN ±%s: %i"
        % (format_number(LARGE_DISCREPANCY_THRESHOLD), large_discrepancy_count)
    )
    Message(
        "Check Arrows Complete",
        "Checked %i master layers and reported %i problem(s), including %i "
        "width discrepancies larger than ±%s."
        % (
            checked_count,
            problem_count,
            large_discrepancy_count,
            format_number(LARGE_DISCREPANCY_THRESHOLD),
        ),
    )


main()
