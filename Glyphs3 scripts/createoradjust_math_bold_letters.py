#MenuTitle: Create or adjust math bold letters
# -*- coding: utf-8 -*-

"""
Create/adjust math-bold layers.

The script works on glyphs listed in the Math Bold and Math Bold Italic blocks
of "CustomFilter Mathematics Alphabets.plist". The UI lets you choose either
the currently selected target glyphs from those blocks or all available target
glyphs from those blocks in the open font. It can optionally open a tab with
the glyphs it modified.

For each target glyph, the script derives the source glyph name, then asks
designspace_axis_rotation.rotate_glyph_designspace() to copy fully decomposed
source layers into the target while moving the effect of the source axis onto
the target axis.
"""

import os
import plistlib
import sys
import vanilla
from GlyphsApp import Glyphs


BOLD_MATH_SUFFIX = "bold-math"
BOLD_ITALIC_MATH_SUFFIX = "bolditalic-math"
ITALIC_MATH_SUFFIX = "italic-math"
MATHEMATICAL_ALPHABETS_PLIST = "CustomFilter Mathematics Alphabets.plist"
BOLD_FILTER_BLOCKS = (
    "Math Bold Latin",
    "Math Bold Greek",
    "Math Bold Italic Latin",
    "Math Bold Italic Greek",
    "Math Bold Italic Symbols",
)
ROTATION_SOURCE_AXIS_TAG = "wght"
ROTATION_TARGET_AXIS_TAG = "MGHT"
ROTATION_SOURCE_LOW_VALUE = 360
ROTATION_SOURCE_HIGH_VALUE = 900
ROTATION_TARGET_VALUE = 540
SCRIPT_VERSION = "2026-06-21 factored-axis-rotation-mght-540"
SOURCE_GLYPH_NAME_OVERRIDES = {
    "hbolditalic-math": "planckconstant",
}


def script_directory():
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except Exception:
        return os.getcwd()


SCRIPT_DIR = script_directory()
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from designspace_axis_rotation import axis_id_for_tag, print_warning, rotate_glyph_designspace


Glyphs.clearLog()
Glyphs.showMacroWindow()
print("Create or adjust math bold letters")
print("Script version: %s" % SCRIPT_VERSION)
print("Ready. Choose the scope and press 'Create/adjust'.")
print("")


def mathematical_alphabets_plist_path():
    candidate_directories = [
        os.path.join(SCRIPT_DIR, "..", "sources"),
        os.path.join(SCRIPT_DIR, "..", "..", "sources"),
        os.path.join(os.getcwd(), "sources"),
    ]

    for directory in candidate_directories:
        path = os.path.abspath(os.path.join(directory, MATHEMATICAL_ALPHABETS_PLIST))
        if os.path.exists(path):
            return path
    return None


def load_bold_math_names():
    plist_path = mathematical_alphabets_plist_path()
    if plist_path is None:
        print_warning("Could not find %s." % MATHEMATICAL_ALPHABETS_PLIST)
        return []

    try:
        with open(plist_path, "rb") as plist_file:
            blocks = plistlib.load(plist_file)
    except Exception as error:
        print_warning("Could not read %s: %s" % (plist_path, error))
        return []

    glyph_names = []
    seen = set()
    wanted_blocks = set(BOLD_FILTER_BLOCKS)
    for block in blocks:
        if block.get("name") not in wanted_blocks:
            continue
        for glyph_name in block.get("list", []):
            if glyph_name in seen:
                continue
            seen.add(glyph_name)
            glyph_names.append(glyph_name)

    print("Loaded %i target glyph names from %s." % (len(glyph_names), os.path.basename(plist_path)))
    print("Filter blocks: %s" % ", ".join(BOLD_FILTER_BLOCKS))
    return glyph_names


def unique_selected_glyphs(font):
    glyphs = []
    seen = set()
    for layer in font.selectedLayers:
        glyph = layer.parent
        if glyph is None or glyph.name in seen:
            continue
        seen.add(glyph.name)
        glyphs.append(glyph)
    return glyphs


def selected_bold_math_glyphs(font, bold_math_names):
    bold_name_set = set(bold_math_names)
    return [glyph for glyph in unique_selected_glyphs(font) if glyph.name in bold_name_set]


def all_available_bold_math_glyphs(font, bold_math_names):
    glyphs = []
    missing = 0
    for glyph_name in bold_math_names:
        glyph = font.glyphs[glyph_name]
        if glyph is None:
            missing += 1
            continue
        glyphs.append(glyph)
    return glyphs, missing


def source_name_for_bold_math_glyph(glyph_name):
    if glyph_name in SOURCE_GLYPH_NAME_OVERRIDES:
        return SOURCE_GLYPH_NAME_OVERRIDES[glyph_name]
    if glyph_name.endswith(BOLD_ITALIC_MATH_SUFFIX):
        return glyph_name[:-len(BOLD_ITALIC_MATH_SUFFIX)] + ITALIC_MATH_SUFFIX
    if not glyph_name.endswith(BOLD_MATH_SUFFIX):
        return None
    return glyph_name[:-len(BOLD_MATH_SUFFIX)]


def append_unique(items, item):
    if item not in items:
        items.append(item)


def add_stats(total, update):
    for key, value in update.items():
        if key == "modified":
            continue
        if isinstance(value, int):
            total[key] = total.get(key, 0) + value


def open_modified_glyphs_tab(font, glyph_names):
    if not glyph_names:
        print("No modified glyphs to open in a tab.")
        return

    try:
        font.newTab("/" + "/".join(glyph_names))
        print("Opened tab with %i modified glyphs." % len(glyph_names))
    except Exception as error:
        print_warning("Could not open modified glyphs tab: %s" % error)


def process_target_glyph(font, glyph):
    source_glyph_name = source_name_for_bold_math_glyph(glyph.name)
    if source_glyph_name is None:
        print_warning("%s: skipped, could not derive source glyph name" % glyph.name)
        return {"copy_layers_skipped": len(glyph.layers), "modified": 0}

    source_glyph = font.glyphs[source_glyph_name]
    if source_glyph is None:
        print_warning("%s: skipped, missing source glyph %s" % (glyph.name, source_glyph_name))
        return {"copy_layers_skipped": len(glyph.layers), "modified": 0}

    return rotate_glyph_designspace(
        font,
        source_glyph,
        glyph,
        ROTATION_SOURCE_AXIS_TAG,
        ROTATION_TARGET_AXIS_TAG,
        ROTATION_SOURCE_LOW_VALUE,
        ROTATION_SOURCE_HIGH_VALUE,
        ROTATION_TARGET_VALUE,
    )


def run_for_glyphs(font, glyphs, open_tab=False):
    target_axis_id = axis_id_for_tag(font, ROTATION_TARGET_AXIS_TAG)
    if target_axis_id is None:
        print_warning("Could not find axis %s in the open font." % ROTATION_TARGET_AXIS_TAG)
        return

    source_axis_id = axis_id_for_tag(font, ROTATION_SOURCE_AXIS_TAG)
    if source_axis_id is None:
        print_warning("Could not find axis %s in the open font." % ROTATION_SOURCE_AXIS_TAG)
        return

    print("Font: %s" % (font.familyName or "Untitled"))
    print("Glyphs to process: %i" % len(glyphs))
    print("Target %s value: %s" % (ROTATION_TARGET_AXIS_TAG, ROTATION_TARGET_VALUE))
    print("Master layers use %s=%s; intermediate layers use %s=%s." % (
        ROTATION_SOURCE_AXIS_TAG,
        ROTATION_SOURCE_LOW_VALUE,
        ROTATION_SOURCE_AXIS_TAG,
        ROTATION_SOURCE_HIGH_VALUE,
    ))
    print("Alternate layer rules on %s (%s) are remapped to %s (%s)." % (
        ROTATION_SOURCE_AXIS_TAG,
        source_axis_id,
        ROTATION_TARGET_AXIS_TAG,
        target_axis_id,
    ))
    print("")

    totals = {}
    modified_glyph_names = []
    font.disableUpdateInterface()
    try:
        for index, glyph in enumerate(glyphs, 1):
            print("[%i/%i] Processing %s" % (index, len(glyphs), glyph.name))
            stats = process_target_glyph(font, glyph)
            add_stats(totals, stats)
            if stats.get("modified"):
                append_unique(modified_glyph_names, glyph.name)
    finally:
        font.enableUpdateInterface()

    if open_tab:
        open_modified_glyphs_tab(font, modified_glyph_names)

    print("")
    print("Done.")
    print("Glyphs processed: %i" % len(glyphs))
    print("Modified glyphs collected for tab: %i" % len(modified_glyph_names))
    for key in sorted(totals.keys()):
        print("%s: %i" % (key.replace("_", " ").capitalize(), totals[key]))


class BoldMathWindow(object):
    def __init__(self):
        self.bold_math_names = load_bold_math_names()
        self.w = vanilla.FloatingWindow((360, 162), "Create/adjust math bold letters")
        self.w.scope = vanilla.RadioGroup(
            (15, 15, -15, 42),
            ["Selected target glyphs", "All available target glyphs"],
            isVertical=True,
        )
        self.w.scope.set(0)
        self.w.openTab = vanilla.CheckBox((15, 70, -15, 20), "Open tab with modified glyphs", value=False)
        self.w.runButton = vanilla.Button((15, 111, -15, 24), "Create/adjust", callback=self.run_callback)
        self.w.open()
        self.w.makeKey()
        print("UI opened.")

    def run_callback(self, sender):
        Glyphs.clearLog()
        Glyphs.showMacroWindow()
        print("Create or adjust math bold letters")
        print("Script version: %s" % SCRIPT_VERSION)
        print("")

        font = Glyphs.font
        if font is None:
            print_warning("No font open.")
            return

        if not self.bold_math_names:
            print_warning("No target glyph names were loaded from the custom filter.")
            return

        if self.w.scope.get() == 0:
            glyphs = selected_bold_math_glyphs(font, self.bold_math_names)
            if not glyphs:
                print_warning("No selected glyphs are listed in the supported Math Bold/Bold Italic custom filter blocks.")
                print_warning("Select one or more target glyphs, or choose 'All available target glyphs'.")
                return
            print("Scope: selected target glyphs")
        else:
            glyphs, missing = all_available_bold_math_glyphs(font, self.bold_math_names)
            if not glyphs:
                print_warning("None of the target glyphs from the custom filter exist in this font.")
                return
            print("Scope: all available target glyphs")
            print("Custom-filter glyphs missing from font: %i" % missing)

        open_tab = self.w.openTab.get()
        self.w.close()
        run_for_glyphs(font, glyphs, open_tab=open_tab)


try:
    BOLD_MATH_WINDOW = BoldMathWindow()
except Exception as error:
    import traceback

    Glyphs.clearLog()
    Glyphs.showMacroWindow()
    print("Create or adjust math bold letters")
    print("")
    print_warning("Could not open UI: %s" % error)
    print_warning(traceback.format_exc())
