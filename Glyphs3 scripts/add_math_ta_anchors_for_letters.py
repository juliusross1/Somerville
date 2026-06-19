#MenuTitle: Add or adjust math.ta Anchors for Mathematical Letters
# -*- coding: utf-8 -*-

"""
Add math.ta anchors to mathematical letter glyphs in the frontmost font.

The script only works on mathematical alphabet glyphs listed in the custom
filter plist "CustomFilter Mathematics Alphabets.plist". It looks for an
existing "top" anchor on every layer of each chosen glyph. If a layer has no
direct "top" anchor, it also checks the glyph's components recursively and uses
a component-provided "top" anchor when found.

The new "math.ta" anchor is placed at the top anchor's x-position and at the
layer's bounding box height plus (AccentBaseHeight - AxisHeight). For glyphs
whose names contain "italic-math", the x-position can be shifted by an italic
angle using:
    (AccentBaseHeight - AxisHeight) * tan(angle)
"""

import math
import os
import plistlib
import vanilla
from GlyphsApp import Glyphs, GSAnchor


SOURCE_ANCHOR = "top"
TARGET_ANCHOR = "math.ta"
DEFAULT_SLANT_DEGREES = 15
MATH_CONSTANTS_PARAMETER = "com.nagwa.MATHPlugin.constants"
MATHEMATICAL_ALPHABETS_PLIST = "CustomFilter Mathematics Alphabets.plist"
LEGACY_MATHEMATICAL_ALPHABETS_PLIST = "CustomFilter Mathematical Alphabets.plist"
POSITION_TOLERANCE = 0.001


Glyphs.clearLog()
Glyphs.showMacroWindow()
print("Add math.ta Anchors for Mathematical Letters")
print("Ready. Choose the scope and press 'Insert/adjust math.ta anchors'.")
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
        return set(), []

    try:
        with open(plist_path, "rb") as plist_file:
            blocks = plistlib.load(plist_file)
    except Exception as error:
        print("Warning: could not read %s: %s" % (plist_path, error))
        return set(), []

    glyph_names = []
    block_names = []
    seen = set()
    for block in blocks:
        block_name = block.get("name", "Unnamed block")
        block_names.append(block_name)
        for glyph_name in block.get("list", []):
            if glyph_name in seen:
                continue
            seen.add(glyph_name)
            glyph_names.append(glyph_name)

    print("Loaded %i mathematical alphabet glyph names from %s." % (len(glyph_names), os.path.basename(plist_path)))
    print("Filter blocks: %i" % len(block_names))
    return set(glyph_names), block_names


def filter_mathematical_glyphs(glyphs, mathematical_names):
    return [glyph for glyph in glyphs if glyph.name in mathematical_names]


def all_mathematical_glyphs(font, mathematical_names):
    glyphs = []
    missing = 0
    for glyph_name in sorted(mathematical_names):
        glyph = font.glyphs[glyph_name]
        if glyph is None:
            missing += 1
            continue
        glyphs.append(glyph)
    return glyphs, missing


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


def custom_parameter_value(owner, parameter_name):
    parameters = getattr(owner, "customParameters", None)
    if not parameters:
        return None

    try:
        value = parameters[parameter_name]
        if value is not None:
            return value
    except Exception:
        pass

    for parameter in parameters:
        name = getattr(parameter, "name", None)
        if name == parameter_name:
            return getattr(parameter, "value", None)
    return None


def math_constant_value(font, master, constant_name):
    for owner in (master, font):
        constants = custom_parameter_value(owner, MATH_CONSTANTS_PARAMETER)
        if constants and constant_name in constants:
            return constants[constant_name]
    return None


def metric_value(master, attribute_name, fallback=0):
    value = getattr(master, attribute_name, None)
    if value is None:
        return fallback
    return value


def cap_height_for_layer(font, layer):
    return metric_value(master_for_layer(font, layer), "capHeight")


def accent_base_minus_axis(font, layer):
    master = master_for_layer(font, layer)
    accent_base_height = math_constant_value(font, master, "AccentBaseHeight")
    if accent_base_height is None:
        accent_base_height = cap_height_for_layer(font, layer)

    axis_height = math_constant_value(font, master, "AxisHeight")
    if axis_height is None:
        axis_height = metric_value(master, "xHeight")

    return float(accent_base_height) - float(axis_height)


def bounding_box_height(layer):
    bounds = layer.bounds
    size = getattr(bounds, "size", None)
    if size is not None:
        return float(size.height)

    try:
        return float(bounds[3])
    except Exception:
        return 0.0


def math_ta_position_for_layer(font, layer, x_position):
    y_position = bounding_box_height(layer) + accent_base_minus_axis(font, layer)
    return (float(x_position), y_position)


def italic_adjustment(font, layer, slant_degrees):
    return accent_base_minus_axis(font, layer) * math.tan(math.radians(slant_degrees))


def is_italic_math_glyph(glyph):
    return "italic-math" in glyph.name


def add_anchor(layer, anchor_name, position):
    anchor = layer.anchors[anchor_name]
    if anchor is not None:
        return "present"

    anchor = GSAnchor()
    anchor.name = anchor_name
    anchor.position = position
    layer.anchors.append(anchor)
    return "added"


def positions_are_equal(first_position, second_position):
    return (
        abs(float(first_position.x) - float(second_position[0])) <= POSITION_TOLERANCE
        and abs(float(first_position.y) - float(second_position[1])) <= POSITION_TOLERANCE
    )


def component_layer_for_parent(component, parent_layer):
    component_layer = getattr(component, "componentLayer", None)
    if component_layer is not None:
        return component_layer

    component_glyph = getattr(component, "component", None)
    if component_glyph is None:
        return None

    layer_id = getattr(parent_layer, "associatedMasterId", None) or getattr(parent_layer, "layerId", None)
    if layer_id:
        try:
            component_layer = component_glyph.layers[layer_id]
            if component_layer is not None:
                return component_layer
        except Exception:
            pass

    return None


def transformed_component_x(component, x_position):
    transform = getattr(component, "transform", None)
    if transform is not None:
        try:
            return (float(transform.m11) * float(x_position)) + float(transform.tX)
        except Exception:
            pass

        try:
            return (float(transform[0]) * float(x_position)) + float(transform[4])
        except Exception:
            pass

    position = getattr(component, "position", None)
    if position is not None:
        return float(x_position) + float(position.x)

    return float(x_position) + float(getattr(component, "x", 0) or 0)


def anchor_x_in_layer(layer, anchor_name, seen=None):
    if seen is None:
        seen = set()

    layer_key = id(layer)
    if layer_key in seen:
        return None
    seen.add(layer_key)

    anchor = layer.anchors[anchor_name]
    if anchor is not None:
        return float(anchor.position.x), "direct"

    for component in layer.components:
        component_layer = component_layer_for_parent(component, layer)
        if component_layer is None:
            continue

        component_anchor = anchor_x_in_layer(component_layer, anchor_name, seen)
        if component_anchor is not None:
            component_anchor_x, source = component_anchor
            if source == "direct":
                source = "component"
            return transformed_component_x(component, component_anchor_x), source

    return None


def add_math_ta_for_glyph(font, glyph, adjust_for_italics, slant_degrees, overwrite_existing):
    added = 0
    moved = 0
    existing = 0
    already_correct = 0
    skipped = 0
    direct_sources = 0
    component_sources = 0

    for layer in glyph.layers:
        math_ta_anchor = layer.anchors[TARGET_ANCHOR]
        if math_ta_anchor is not None:
            existing += 1

        if math_ta_anchor is not None and not overwrite_existing:
            already_correct += 1
            continue

        anchor_result = anchor_x_in_layer(layer, SOURCE_ANCHOR)
        if anchor_result is None:
            skipped += 1
            continue

        x_position, source = anchor_result
        if source == "component":
            component_sources += 1
        else:
            direct_sources += 1

        if adjust_for_italics and is_italic_math_glyph(glyph):
            x_position += italic_adjustment(font, layer, slant_degrees)

        position = math_ta_position_for_layer(font, layer, x_position)
        if math_ta_anchor is not None:
            if positions_are_equal(math_ta_anchor.position, position):
                already_correct += 1
            else:
                math_ta_anchor.position = position
                moved += 1
        elif add_anchor(layer, TARGET_ANCHOR, position) == "added":
            added += 1
        else:
            existing += 1
            already_correct += 1

    return added, moved, existing, already_correct, skipped, direct_sources, component_sources


class MathTAAnchorBuilder(object):
    def __init__(self):
        print("Opening UI.")
        self.w = vanilla.FloatingWindow((330, 202), "Add math.ta Anchors")
        self.w.scopeLabel = vanilla.TextBox((15, 16, -15, 18), "Apply to")
        self.w.scope = vanilla.RadioGroup(
            (15, 38, -15, 42),
            ["Selected mathematical letters", "All mathematical letters"],
        )
        self.w.scope.set(0)
        self.w.adjustForItalics = vanilla.CheckBox((15, 88, -15, 20), "Adjust for italics", value=True)
        self.w.overwriteExisting = vanilla.CheckBox((15, 114, -15, 20), "Overwrite existing math.ta positions", value=False)
        self.w.angleLabel = vanilla.TextBox((15, 144, 92, 18), "Angle")
        self.w.angle = vanilla.EditText((110, 139, 60, 22), str(DEFAULT_SLANT_DEGREES))
        self.w.angleUnits = vanilla.TextBox((176, 144, -15, 18), "degrees")
        self.w.applyButton = vanilla.Button((15, 169, -15, 26), "Insert/adjust math.ta anchors", callback=self.apply_callback)
        self.w.open()

    def glyphs_to_process(self, font, mathematical_names):
        if self.w.scope.get() == 0:
            selected_glyphs = unique_selected_glyphs(font)
            if not selected_glyphs:
                return [], 0, 0, "no_selection"

            glyphs = filter_mathematical_glyphs(selected_glyphs, mathematical_names)
            if not glyphs:
                return [], len(selected_glyphs), 0, "no_selected_mathematical_letters"

            return glyphs, len(selected_glyphs), 0, None

        glyphs, missing = all_mathematical_glyphs(font, mathematical_names)
        return glyphs, len(mathematical_names), missing, None

    def apply_callback(self, sender):
        font = Glyphs.font
        Glyphs.showMacroWindow()
        print("Starting math.ta anchor pass.")

        if font is None:
            print("No font open.")
            return

        adjust_for_italics = bool(self.w.adjustForItalics.get())
        overwrite_existing = bool(self.w.overwriteExisting.get())
        try:
            slant_degrees = float(self.w.angle.get())
        except Exception:
            slant_degrees = float(DEFAULT_SLANT_DEGREES)
            print("Invalid angle value; using %.1f degrees." % slant_degrees)

        mathematical_names, filter_blocks = load_mathematical_alphabet_names()
        if not mathematical_names:
            print("No mathematical alphabet glyph list loaded.")
            return

        scope_is_all = self.w.scope.get() == 1
        scope_label = "all mathematical letters" if scope_is_all else "selected mathematical letters"
        glyphs, candidate_count, missing_count, stop_reason = self.glyphs_to_process(font, mathematical_names)
        self.w.close()

        if not glyphs:
            if stop_reason == "no_selection":
                print("No glyphs are selected. Select one or more mathematical letters, or choose 'All mathematical letters'.")
            elif stop_reason == "no_selected_mathematical_letters":
                print("No selected glyphs are mathematical letters from %s." % MATHEMATICAL_ALPHABETS_PLIST)
            else:
                print("No mathematical alphabet glyphs to process.")
            return

        print("")
        print("Adding '%s' anchors from '%s' anchors in %s" % (TARGET_ANCHOR, SOURCE_ANCHOR, font.familyName))
        print("Scope: %s" % scope_label)
        print("Mathematical alphabet blocks loaded: %i" % len(filter_blocks))
        print("Candidate glyphs before filtering/missing checks: %i" % candidate_count)
        if scope_is_all:
            print("Mathematical alphabet glyphs missing from font: %i" % missing_count)
        print("Glyphs to process: %i" % len(glyphs))
        print("Adjust for italics: %s" % ("yes" if adjust_for_italics else "no"))
        print("Overwrite existing '%s' anchors: %s" % (TARGET_ANCHOR, "yes" if overwrite_existing else "no"))
        if adjust_for_italics:
            print("Italic angle: %g degrees" % slant_degrees)
        print("Looking for '%s' anchors directly on layers and recursively in components." % SOURCE_ANCHOR)
        print("New '%s' anchors use y = bounding box height + (AccentBaseHeight - AxisHeight)." % TARGET_ANCHOR)
        print("")

        total_added = 0
        total_moved = 0
        total_existing = 0
        total_already_correct = 0
        total_skipped = 0
        total_direct_sources = 0
        total_component_sources = 0

        font.disableUpdateInterface()
        try:
            for glyph in glyphs:
                added, moved, existing, already_correct, skipped, direct_sources, component_sources = add_math_ta_for_glyph(
                    font,
                    glyph,
                    adjust_for_italics,
                    slant_degrees,
                    overwrite_existing,
                )
                total_added += added
                total_moved += moved
                total_existing += existing
                total_already_correct += already_correct
                total_skipped += skipped
                total_direct_sources += direct_sources
                total_component_sources += component_sources
                print("%s: added %i, moved %i, existing %i, already correct %i, skipped %i layers without top; top source direct %i, component %i" % (
                    glyph.name,
                    added,
                    moved,
                    existing,
                    already_correct,
                    skipped,
                    direct_sources,
                    component_sources,
                ))
        finally:
            font.enableUpdateInterface()

        print("")
        print("Done.")
        print("Anchors added: %i" % total_added)
        print("Existing math.ta anchors found: %i" % total_existing)
        print("Existing math.ta anchors moved: %i" % total_moved)
        print("Existing math.ta anchors already correct: %i" % total_already_correct)
        print("Layers skipped without top anchor: %i" % total_skipped)
        print("Direct top anchors used: %i" % total_direct_sources)
        print("Component top anchors used: %i" % total_component_sources)


MathTAAnchorBuilder()
