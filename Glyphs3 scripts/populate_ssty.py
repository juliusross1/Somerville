#MenuTitle: Populate SSTY
# -*- coding: utf-8 -*-

"""
Populate .ssty1 and .ssty2 glyph layers.

The script works on glyphs in the open font whose names end with .ssty1 or
.ssty2. For each target glyph, it derives the source by removing that suffix.
For example, A.ssty1 uses A as its source, and A.ss01.ssty1 uses A.ss01.

The source optical-size axis is flattened and moved onto the SSTY target axis:
.ssty1 uses STYA, and .ssty2 uses STYB.
"""

import os
import sys
import importlib
import vanilla
from GlyphsApp import Glyphs


SSTY1_SUFFIX = ".ssty1"
SSTY2_SUFFIX = ".ssty2"
SSTY_SUFFIXES = (SSTY1_SUFFIX, SSTY2_SUFFIX)
TARGET_AXIS_BY_SUFFIX = {
    SSTY1_SUFFIX: "STYA",
    SSTY2_SUFFIX: "STYB",
}
ROTATION_SOURCE_AXIS_TAG = "opsz"
ROTATION_SOURCE_BASE_VALUE = 1200
ROTATION_SOURCE_SMALL_VALUE = 5
ROTATION_TARGET_VALUE = ROTATION_SOURCE_SMALL_VALUE
SCRIPT_VERSION = "2026-06-23 10:19 CDT ssty-opsz-to-stya-styb"


def script_directory():
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except Exception:
        return os.getcwd()


SCRIPT_DIR = script_directory()
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import designspace_axis_rotation
designspace_axis_rotation = importlib.reload(designspace_axis_rotation)
from designspace_axis_rotation import (
    DESIGNSPACE_AXIS_ROTATION_VERSION,
    axis_id_for_tag,
    print_warning,
    rotate_glyph_designspace,
)


Glyphs.clearLog()
Glyphs.showMacroWindow()
print("Populate SSTY")
print("Script version: %s" % SCRIPT_VERSION)
print("Helper version: %s" % DESIGNSPACE_AXIS_ROTATION_VERSION)
print("Ready. Choose the scope and press 'Populate'.")
print("")


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


def ssty_suffix_for_glyph_name(glyph_name):
    for suffix in SSTY_SUFFIXES:
        if glyph_name.endswith(suffix):
            return suffix
    return None


def is_ssty_target_name(glyph_name):
    return ssty_suffix_for_glyph_name(glyph_name) is not None


def source_name_for_ssty_glyph(glyph_name):
    suffix = ssty_suffix_for_glyph_name(glyph_name)
    if suffix is None:
        return None
    return glyph_name[:-len(suffix)]


def target_axis_tag_for_ssty_glyph(glyph_name):
    suffix = ssty_suffix_for_glyph_name(glyph_name)
    if suffix is None:
        return None
    return TARGET_AXIS_BY_SUFFIX[suffix]


def selected_ssty_glyphs(font):
    return [glyph for glyph in unique_selected_glyphs(font) if is_ssty_target_name(glyph.name)]


def all_available_ssty_glyphs(font):
    glyphs = []
    for glyph in font.glyphs:
        glyph_name = getattr(glyph, "name", None)
        if glyph_name and is_ssty_target_name(glyph_name):
            glyphs.append(glyph)
    return sorted(glyphs, key=lambda glyph: glyph.name)


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
    source_glyph_name = source_name_for_ssty_glyph(glyph.name)
    if source_glyph_name is None:
        print_warning("%s: skipped, could not derive source glyph name" % glyph.name)
        return {"copy_layers_skipped": len(glyph.layers), "modified": 0}

    source_glyph = font.glyphs[source_glyph_name]
    if source_glyph is None:
        print_warning("%s: skipped, missing source glyph %s" % (glyph.name, source_glyph_name))
        return {"copy_layers_skipped": len(glyph.layers), "modified": 0}

    target_axis_tag = target_axis_tag_for_ssty_glyph(glyph.name)
    if target_axis_tag is None:
        print_warning("%s: skipped, could not derive target SSTY axis" % glyph.name)
        return {"copy_layers_skipped": len(glyph.layers), "modified": 0}

    return rotate_glyph_designspace(
        font,
        source_glyph,
        glyph,
        ROTATION_SOURCE_AXIS_TAG,
        target_axis_tag,
        ROTATION_SOURCE_BASE_VALUE,
        ROTATION_SOURCE_SMALL_VALUE,
        ROTATION_TARGET_VALUE,
        map_source_axis_coordinates_to_target_axis=True,
    )


def run_for_glyphs(font, glyphs, open_tab=False):
    source_axis_id = axis_id_for_tag(font, ROTATION_SOURCE_AXIS_TAG)
    if source_axis_id is None:
        print_warning("Could not find axis %s in the open font." % ROTATION_SOURCE_AXIS_TAG)
        return

    required_target_axes = sorted(set(target_axis_tag_for_ssty_glyph(glyph.name) for glyph in glyphs))
    missing_target_axes = [
        axis_tag for axis_tag in required_target_axes
        if axis_tag is None or axis_id_for_tag(font, axis_tag) is None
    ]
    if missing_target_axes:
        print_warning("Could not find required SSTY axis/axes in the open font: %s" % ", ".join(missing_target_axes))
        return

    print("Font: %s" % (font.familyName or "Untitled"))
    print("Glyphs to process: %i" % len(glyphs))
    print(".ssty1 target axis: %s" % TARGET_AXIS_BY_SUFFIX[SSTY1_SUFFIX])
    print(".ssty2 target axis: %s" % TARGET_AXIS_BY_SUFFIX[SSTY2_SUFFIX])
    print("Master layers use %s=%s; SSTY layers use %s=%s." % (
        ROTATION_SOURCE_AXIS_TAG,
        ROTATION_SOURCE_BASE_VALUE,
        ROTATION_SOURCE_AXIS_TAG,
        ROTATION_SOURCE_SMALL_VALUE,
    ))
    print("Source coordinate layers keep their %s coordinate on the SSTY target axis." % ROTATION_SOURCE_AXIS_TAG)
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


class SSTYWindow(object):
    def __init__(self):
        self.w = vanilla.FloatingWindow((360, 162), "Populate SSTY")
        self.w.scope = vanilla.RadioGroup(
            (15, 15, -15, 42),
            ["Selected .ssty glyphs", "All available .ssty glyphs"],
            isVertical=True,
        )
        self.w.scope.set(0)
        self.w.openTab = vanilla.CheckBox((15, 70, -15, 20), "Open tab with modified glyphs", value=False)
        self.w.runButton = vanilla.Button((15, 111, -15, 24), "Populate", callback=self.run_callback)
        self.w.open()
        self.w.makeKey()
        print("UI opened.")

    def run_callback(self, sender):
        Glyphs.clearLog()
        Glyphs.showMacroWindow()
        print("Populate SSTY")
        print("Script version: %s" % SCRIPT_VERSION)
        print("Helper version: %s" % DESIGNSPACE_AXIS_ROTATION_VERSION)
        print("")

        font = Glyphs.font
        if font is None:
            print_warning("No font open.")
            return

        if self.w.scope.get() == 0:
            glyphs = selected_ssty_glyphs(font)
            if not glyphs:
                print_warning("No selected glyphs end with .ssty1 or .ssty2.")
                print_warning("Select one or more SSTY target glyphs, or choose 'All available .ssty glyphs'.")
                return
            print("Scope: selected .ssty glyphs")
        else:
            glyphs = all_available_ssty_glyphs(font)
            if not glyphs:
                print_warning("No glyphs ending with .ssty1 or .ssty2 exist in this font.")
                return
            print("Scope: all available .ssty glyphs")

        open_tab = self.w.openTab.get()
        self.w.close()
        run_for_glyphs(font, glyphs, open_tab=open_tab)


try:
    SSTY_WINDOW = SSTYWindow()
except Exception as error:
    import traceback

    Glyphs.clearLog()
    Glyphs.showMacroWindow()
    print("Populate SSTY")
    print("")
    print_warning("Could not open UI: %s" % error)
    print_warning(traceback.format_exc())
