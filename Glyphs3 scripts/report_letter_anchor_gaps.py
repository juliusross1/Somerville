#MenuTitle: Report Mathematical Letters Missing Top or Bottom Anchors
# -*- coding: utf-8 -*-

import os
import plistlib
import vanilla
from GlyphsApp import Glyphs, GSAnchor


ANCHORS = ("top", "bottom")
MATHEMATICAL_ALPHABETS_PLIST = "CustomFilter Mathematics Alphabets.plist"
LEGACY_MATHEMATICAL_ALPHABETS_PLIST = "CustomFilter Mathematical Alphabets.plist"
EXCLUDED_MATH_BOLD_MARKERS = ("bold-math", "bolditalic-math")
NUMERAL_GLYPH_NAMES = (
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
)


def is_anchor_layer(layer):
    return layer.isMasterLayer or layer.isSpecialLayer


def is_excluded_math_bold_name(glyph_name):
    glyph_name = str(glyph_name or "")
    return any(marker in glyph_name for marker in EXCLUDED_MATH_BOLD_MARKERS)


def script_directory():
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except Exception:
        return os.getcwd()


def mathematical_alphabets_plist_path():
    script_dir = script_directory()
    candidate_directories = [
        os.path.join(script_dir, "..", "sources"),
        os.path.join(script_dir, "..", "..", "sources"),
        os.path.join(os.getcwd(), "sources"),
    ]
    candidate_names = [
        MATHEMATICAL_ALPHABETS_PLIST,
        LEGACY_MATHEMATICAL_ALPHABETS_PLIST,
    ]

    for directory in candidate_directories:
        for file_name in candidate_names:
            path = os.path.abspath(os.path.join(directory, file_name))
            if os.path.exists(path):
                return path
    return None


def load_mathematical_alphabet_names():
    plist_path = mathematical_alphabets_plist_path()
    if plist_path is None:
        print("Warning: could not find %s." % MATHEMATICAL_ALPHABETS_PLIST)
        return []

    try:
        with open(plist_path, "rb") as plist_file:
            blocks = plistlib.load(plist_file)
    except Exception as error:
        print("Warning: could not read %s: %s" % (plist_path, error))
        return []

    glyph_names = []
    seen = set()
    for block in blocks:
        for glyph_name in block.get("list", []):
            if glyph_name in seen:
                continue
            seen.add(glyph_name)
            glyph_names.append(glyph_name)

    mathematical_count = len(glyph_names)
    numeral_count = 0
    for glyph_name in NUMERAL_GLYPH_NAMES:
        if glyph_name in seen:
            continue
        seen.add(glyph_name)
        glyph_names.append(glyph_name)
        numeral_count += 1

    print("Loaded %i mathematical alphabet glyph names from %s." % (mathematical_count, os.path.basename(plist_path)))
    print("Added %i numeral glyph names for anchor checking." % numeral_count)
    return glyph_names


def mathematical_glyphs_in_font(font, glyph_names):
    glyphs = []
    missing_count = 0
    nonexporting_count = 0
    math_bold_count = 0

    for glyph_name in glyph_names:
        if is_excluded_math_bold_name(glyph_name):
            math_bold_count += 1
            continue

        glyph = font.glyphs[glyph_name]
        if glyph is None:
            missing_count += 1
            continue
        if not glyph.export:
            nonexporting_count += 1
            continue
        glyphs.append(glyph)

    return glyphs, missing_count, nonexporting_count, math_bold_count


def master_for_layer(font, layer):
    master = getattr(layer, "master", None)
    if master is not None:
        return master

    associated_master_id = getattr(layer, "associatedMasterId", None)
    if associated_master_id:
        master = font.masters[associated_master_id]
        if master is not None:
            return master

    return font.selectedFontMaster


def cap_height_for_layer(font, layer):
    return master_for_layer(font, layer).capHeight


def component_name(component):
    for attribute_name in ("componentName", "name"):
        if hasattr(component, attribute_name):
            value = getattr(component, attribute_name)
            if value:
                return value
    return None


def component_layer(component, parent_layer):
    layer = getattr(component, "componentLayer", None)
    if layer is not None:
        return layer

    glyph = getattr(component, "component", None)
    if glyph is None:
        return None

    associated_master_id = getattr(parent_layer, "associatedMasterId", None) or getattr(parent_layer, "layerId", None)
    if associated_master_id:
        layer = glyph.layers[associated_master_id]
        if layer is not None:
            return layer

    return None


def layer_or_components_have_anchor(layer, anchor_name, seen=None):
    if seen is None:
        seen = set()

    if layer.anchors[anchor_name] is not None:
        return True

    layer_key = (getattr(layer.parent, "name", None), layer.layerId, anchor_name)
    if layer_key in seen:
        return False
    seen.add(layer_key)

    for component in layer.components:
        name = component_name(component)
        if name is None:
            continue

        child_layer = component_layer(component, layer)
        if child_layer is not None and layer_or_components_have_anchor(child_layer, anchor_name, seen):
            return True

    return False


def is_missing_anchor(glyph, anchor_name):
    for layer in glyph.layers:
        if not is_anchor_layer(layer):
            continue
        if not layer_or_components_have_anchor(layer, anchor_name):
            return True
    return False


def print_missing_anchor_report(heading, missing_glyphs):
    print(heading)
    if not missing_glyphs:
        print("  None")
        return

    for glyph_name in missing_glyphs:
        print("  %s" % glyph_name)


def anchor_position(font, layer, anchor_name):
    x_position = float(layer.width) / 2.0
    if anchor_name == "top":
        return (x_position, float(cap_height_for_layer(font, layer)))
    return (x_position, 0.0)


def add_anchor(layer, anchor_name, position):
    anchor = GSAnchor()
    anchor.name = anchor_name
    anchor.position = position
    layer.anchors.append(anchor)


def missing_anchor_report(font):
    mathematical_names = load_mathematical_alphabet_names()
    if not mathematical_names:
        return None

    mathematical_glyphs, missing_count, nonexporting_count, math_bold_count = mathematical_glyphs_in_font(font, mathematical_names)
    missing_by_anchor = {anchor_name: [] for anchor_name in ANCHORS}
    checked_count = 0

    for glyph in mathematical_glyphs:
        checked_count += 1
        for anchor_name in ANCHORS:
            if is_missing_anchor(glyph, anchor_name):
                missing_by_anchor[anchor_name].append(glyph.name)

    return {
        "glyphs": mathematical_glyphs,
        "missing_by_anchor": missing_by_anchor,
        "checked_count": checked_count,
        "missing_count": missing_count,
        "nonexporting_count": nonexporting_count,
        "math_bold_count": math_bold_count,
    }


def print_report(font, report):
    missing_by_anchor = report["missing_by_anchor"]
    print("Mathematical Letter and Numeral Anchor Report for %s" % (font.familyName or "Untitled"))
    print("")
    print("Glyphs checked: %i" % report["checked_count"])
    print("Glyph names missing from font: %i" % report["missing_count"])
    print("Non-exporting glyphs skipped: %i" % report["nonexporting_count"])
    print("Bold-math and bolditalic-math glyphs skipped: %i" % report["math_bold_count"])
    print("")
    print_missing_anchor_report("These glyphs do not have a top anchor", missing_by_anchor["top"])
    print("")
    print_missing_anchor_report("These glyphs do not have a bottom anchor", missing_by_anchor["bottom"])


def report_missing_glyph_names(report):
    glyph_names = []
    seen = set()
    for anchor_name in ANCHORS:
        for glyph_name in report["missing_by_anchor"][anchor_name]:
            if glyph_name in seen:
                continue
            seen.add(glyph_name)
            glyph_names.append(glyph_name)
    return glyph_names


def open_missing_glyphs_tab(font, report):
    glyph_names = report_missing_glyph_names(report)
    if not glyph_names:
        print("No missing-anchor glyphs to open in a tab.")
        return

    tab_text = "/" + "/".join(glyph_names)
    font.newTab(tab_text)
    print("Opened tab with %i glyphs that are missing top and/or bottom anchors." % len(glyph_names))


def add_missing_anchors(font, report):
    totals = {anchor_name: 0 for anchor_name in ANCHORS}
    skipped_layers = 0

    print("")
    print("Adding missing direct anchors.")
    print("top anchors: x = layer width / 2, y = cap height")
    print("bottom anchors: x = layer width / 2, y = baseline")
    print("")

    font.disableUpdateInterface()
    try:
        for glyph in report["glyphs"]:
            glyph_counts = {anchor_name: 0 for anchor_name in ANCHORS}
            for layer in glyph.layers:
                if not is_anchor_layer(layer):
                    skipped_layers += 1
                    continue

                for anchor_name in ANCHORS:
                    if layer_or_components_have_anchor(layer, anchor_name):
                        continue

                    position = anchor_position(font, layer, anchor_name)
                    add_anchor(layer, anchor_name, position)
                    glyph_counts[anchor_name] += 1
                    totals[anchor_name] += 1

            if glyph_counts["top"] or glyph_counts["bottom"]:
                print("%s: added top %i, bottom %i" % (
                    glyph.name,
                    glyph_counts["top"],
                    glyph_counts["bottom"],
                ))
    finally:
        font.enableUpdateInterface()

    print("")
    print("Done adding missing anchors.")
    print("Top anchors added: %i" % totals["top"])
    print("Bottom anchors added: %i" % totals["bottom"])
    print("Non-anchor layers skipped: %i" % skipped_layers)


class MathematicalAnchorGapReporter(object):
    def __init__(self):
        Glyphs.clearLog()
        Glyphs.showMacroWindow()
        print("Report Mathematical Letters Missing Top or Bottom Anchors")
        print("Ready. Choose options and run a report or add missing anchors.")
        print("")

        self.w = vanilla.FloatingWindow((360, 128), "Mathematical Anchor Gaps")
        self.w.openTab = vanilla.CheckBox((15, 16, -15, 20), "Open tab with reported glyphs", value=False)
        self.w.reportButton = vanilla.Button((15, 52, 155, 28), "Report", callback=self.report_callback)
        self.w.addButton = vanilla.Button((185, 52, -15, 28), "Add missing anchors", callback=self.add_callback)
        self.w.closeButton = vanilla.Button((15, 92, -15, 26), "Close", callback=self.close_callback)
        self.w.open()

    def current_report(self):
        font = Glyphs.font
        Glyphs.showMacroWindow()

        if font is None:
            print("No font open.")
            return None, None

        report = missing_anchor_report(font)
        if report is None:
            print("No mathematical alphabet glyph list loaded.")
            return font, None

        return font, report

    def run_report(self, open_tab=None):
        font, report = self.current_report()
        if report is None:
            return font, None

        print_report(font, report)
        if open_tab is None:
            open_tab = self.w.openTab.get()
        if open_tab:
            open_missing_glyphs_tab(font, report)
        return font, report

    def report_callback(self, sender):
        Glyphs.clearLog()
        Glyphs.showMacroWindow()
        self.run_report()

    def add_callback(self, sender):
        Glyphs.clearLog()
        Glyphs.showMacroWindow()
        font, report = self.run_report(open_tab=self.w.openTab.get())
        if report is None:
            return

        add_missing_anchors(font, report)

        print("")
        print("Updated report after adding anchors:")
        updated_report = missing_anchor_report(font)
        if updated_report is not None:
            print_report(font, updated_report)

    def close_callback(self, sender):
        self.w.close()


MathematicalAnchorGapReporter()
