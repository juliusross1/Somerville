#MenuTitle: Create or adjust math bold letters
# -*- coding: utf-8 -*-

"""
Create/adjust math-bold layers.

The script works on glyphs listed in the Math Bold and Math Bold Italic blocks
of "CustomFilter Mathematics Alphabets.plist". The UI lets you choose either
the currently selected glyphs from those blocks or all available glyphs from
those blocks in the open font. It can optionally open a tab with the glyphs it
modified.

For each selected target glyph and each font master, the script creates or
refreshes one intermediate layer with MGHT set to 900. It makes a temporary
working copy of the source glyph, decomposes all normal components plus corner,
cap, stem, segment, and brush helpers, and then copies the resulting outlines,
anchors, stems, and width into the target layer.
"""

import os
import plistlib
import uuid
import vanilla
from GlyphsApp import Glyphs, GSLayer


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
TARGET_AXIS_TAG = "MGHT"
TARGET_AXIS_VALUE = 900
WEIGHT_AXIS_TAG = "wght"
LOW_WEIGHT_VALUE = 360
HIGH_WEIGHT_VALUE = 900
SCRIPT_VERSION = "2026-06-20 decompose-temp-glyph-in-font"


Glyphs.clearLog()
Glyphs.showMacroWindow()
print("Create or adjust math bold letters")
print("Script version: %s" % SCRIPT_VERSION)
print("Ready. Choose the scope and press 'Create/adjust'.")
print("")


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

    for directory in candidate_directories:
        path = os.path.abspath(os.path.join(directory, MATHEMATICAL_ALPHABETS_PLIST))
        if os.path.exists(path):
            return path
    return None


def print_warning(message):
    print("🔴 WARNING: %s" % message)


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
    if glyph_name.endswith(BOLD_ITALIC_MATH_SUFFIX):
        return glyph_name[:-len(BOLD_ITALIC_MATH_SUFFIX)] + ITALIC_MATH_SUFFIX
    if not glyph_name.endswith(BOLD_MATH_SUFFIX):
        return None
    return glyph_name[:-len(BOLD_MATH_SUFFIX)]


def append_unique(items, item):
    if item not in items:
        items.append(item)


def open_modified_glyphs_tab(font, glyph_names):
    if not glyph_names:
        print("No modified glyphs to open in a tab.")
        return

    try:
        font.newTab("/" + "/".join(glyph_names))
        print("Opened tab with %i modified glyphs." % len(glyph_names))
    except Exception as error:
        print_warning("Could not open modified glyphs tab: %s" % error)


def axis_tag(axis):
    for attribute_name in ("tag", "axisTag"):
        value = getattr(axis, attribute_name, None)
        if value:
            return str(value)
    return ""


def axis_id(axis):
    for attribute_name in ("axisId", "id"):
        value = getattr(axis, attribute_name, None)
        if value:
            return str(value)
    return None


def axis_index(font, target_tag):
    for index, axis in enumerate(font.axes):
        if axis_tag(axis) == target_tag:
            return index
    return None


def axis_id_for_tag(font, target_tag):
    index = axis_index(font, target_tag)
    if index is None:
        return None
    return axis_id(font.axes[index])


def master_coordinates(font, master):
    coordinates = {}
    for axis in font.axes:
        current_axis_id = axis_id(axis)
        if current_axis_id is None:
            return None
        try:
            coordinates[current_axis_id] = float(master.axisValueValueForId_(current_axis_id))
        except Exception:
            return None
    return coordinates


def coordinates_for_layer(font, layer):
    if layer.isMasterLayer:
        for master in font.masters:
            if master.id == layer.layerId:
                return master_coordinates(font, master)
        return None

    attributes = getattr(layer, "attributes", None)
    if not attributes:
        return None

    try:
        coordinates = attributes["coordinates"]
    except Exception:
        return None

    values = coordinate_values(font, coordinates)
    if values is None:
        return None

    coordinates_dict = {}
    for index, axis in enumerate(font.axes):
        current_axis_id = axis_id(axis)
        if current_axis_id is None:
            return None
        coordinates_dict[current_axis_id] = values[index]
    return coordinates_dict


def coordinate_values(font, coordinates):
    if coordinates is None:
        return None

    if hasattr(coordinates, "keys"):
        values = []
        for axis in font.axes:
            current_axis_id = axis_id(axis)
            if current_axis_id is None:
                return None
            try:
                values.append(float(coordinates[str(current_axis_id)]))
            except Exception:
                return None
        return values

    values = []
    for value in coordinates:
        try:
            values.append(float(value))
        except Exception:
            return None
    return values


def layer_coordinates(font, layer):
    attributes = getattr(layer, "attributes", None)
    if not attributes:
        return None

    try:
        coordinates = attributes["coordinates"]
    except Exception:
        return None

    return coordinate_values(font, coordinates)


def coordinates_match(font, first_coordinates, second_coordinates):
    first = coordinate_values(font, first_coordinates)
    second = coordinate_values(font, second_coordinates)
    if first is None or second is None or len(first) != len(second):
        return False

    for first_value, second_value in zip(first, second):
        if abs(first_value - second_value) > 0.001:
            return False
    return True


def coordinates_match_except_axes(font, first_coordinates, second_coordinates, ignored_axis_ids):
    ignored_axis_ids = set(ignored_axis_ids)
    for axis in font.axes:
        current_axis_id = axis_id(axis)
        if current_axis_id is None or current_axis_id in ignored_axis_ids:
            continue
        try:
            first_value = float(first_coordinates[str(current_axis_id)])
            second_value = float(second_coordinates[str(current_axis_id)])
        except Exception:
            return False
        if abs(first_value - second_value) > 0.001:
            return False
    return True


def corresponding_master_for_weight(font, coordinates, weight_axis_id, mght_axis_id, target_weight):
    if coordinates is None:
        return None

    target_coordinates = dict(coordinates)
    target_coordinates[str(weight_axis_id)] = float(target_weight)

    ignored_axis_ids = [mght_axis_id]
    for master in font.masters:
        master_coords = master_coordinates(font, master)
        if master_coords is None:
            continue
        if coordinates_match_except_axes(font, master_coords, target_coordinates, ignored_axis_ids):
            return master
    return None


def intermediate_layer_name(master):
    return "%s MGHT %s" % (master.name, TARGET_AXIS_VALUE)


def matching_intermediate_layer(font, glyph, associated_master_id, coordinates, name=None):
    for layer in glyph.layers:
        if layer.isMasterLayer:
            continue
        if associated_master_id is not None and getattr(layer, "associatedMasterId", None) != associated_master_id:
            continue
        if name is not None and layer.name == name:
            return layer
        if coordinates_match(font, layer_coordinates(font, layer), coordinates):
            return layer
    return None


def intermediate_layer_shell(layer_id, name, coordinates, associated_master_id, width):
    layer = GSLayer()
    layer.layerId = layer_id
    layer.associatedMasterId = associated_master_id
    layer.name = name
    if coordinates is not None:
        layer.attributes["coordinates"] = coordinates
    layer.width = width
    return layer


def layer_index(glyph, layer):
    return list(glyph.layers).index(layer)


def replace_layer_contents(target_layer, coordinates, associated_master_id, width):
    refreshed_layer = intermediate_layer_shell(
        target_layer.layerId,
        target_layer.name,
        coordinates,
        associated_master_id,
        width,
    )
    glyph = target_layer.parent
    index = layer_index(glyph, target_layer)
    del glyph.layers[index]
    glyph.layers.insert(index, refreshed_layer)
    return refreshed_layer


def create_intermediate_layer(glyph, master_layer, master, coordinates, width):
    new_layer = intermediate_layer_shell(
        str(uuid.uuid4()).upper(),
        intermediate_layer_name(master),
        coordinates,
        master.id,
        width,
    )
    glyph.layers.insert(layer_index(glyph, master_layer) + 1, new_layer)
    return new_layer


def has_coordinates_attribute(layer):
    attributes = getattr(layer, "attributes", None)
    if not attributes:
        return False

    try:
        attributes["coordinates"]
        return True
    except Exception:
        return False


def source_glyph_has_special_layers(source_glyph):
    for layer in source_glyph.layers:
        if layer.isMasterLayer:
            continue
        if getattr(layer, "isSpecialLayer", False) or has_coordinates_attribute(layer):
            return True
    return False


def clear_proxy(proxy):
    try:
        proxy.clear()
        return
    except Exception:
        pass

    while len(proxy):
        item = proxy[-1]
        try:
            proxy.remove(item)
        except Exception:
            break


def copy_stems(source, target):
    if not hasattr(source, "stems") or not hasattr(target, "stems"):
        return 0

    try:
        target.stems = [stem.copy() for stem in source.stems]
    except Exception:
        try:
            target.stems = source.stems.copy()
        except Exception as error:
            print("  Could not copy stems for %s: %s" % (getattr(target, "name", "glyph"), error))
            return 0

    try:
        return len(target.stems)
    except Exception:
        return 0


HELPER_HINT_PREFIXES = ("_corner.", "_cap.", "_segment.", "_brush.", "_stem")
HELPER_HINT_TYPES = ("Corner", "Cap", "Segment", "Brush", "Stem")


def hint_name(hint):
    value = getattr(hint, "name", "")
    if callable(value):
        try:
            value = value()
        except Exception:
            value = ""
    return str(value or "")


def hint_type_name(hint):
    value = getattr(hint, "type", "")
    if callable(value):
        try:
            value = value()
        except Exception:
            value = ""
    return str(value or "")


def is_helper_hint(hint):
    name = hint_name(hint)
    hint_type = hint_type_name(hint)
    return name.startswith(HELPER_HINT_PREFIXES) or hint_type in HELPER_HINT_TYPES


def count_helper_hints(layer):
    if not hasattr(layer, "hints"):
        return 0
    count = 0
    for hint in layer.hints:
        if is_helper_hint(hint):
            count += 1
    return count


def count_components(layer):
    try:
        return len(layer.components)
    except Exception:
        return 0


def remove_temp_glyph(font, glyph):
    try:
        font.glyphs.remove(glyph)
        return
    except Exception:
        pass

    try:
        del font.glyphs[glyph.name]
    except Exception:
        pass


def source_layer_copy_in_temp_glyph(font, source_glyph, source_layer):
    glyph_copy = source_glyph.copy()
    glyph_copy.name = "__tmp_decompose_%s_%s" % (source_glyph.name, str(uuid.uuid4()).replace("-", ""))
    try:
        glyph_copy.export = False
    except Exception:
        pass

    font.glyphs.append(glyph_copy)
    for layer in glyph_copy.layers:
        if layer.layerId == source_layer.layerId:
            return glyph_copy, layer

    return glyph_copy, glyph_copy.layers[source_layer.layerId]


def call_decompose_method(layer, method_name):
    method = getattr(layer, method_name, None)
    if method is None:
        return False
    try:
        method()
        return True
    except Exception:
        return False


def decompose_layer_components(layer):
    changed = call_decompose_method(layer, "decomposeComponents")
    try:
        components = list(layer.components)
    except Exception:
        components = []
    for component in components:
        try:
            component.decompose()
            changed = True
        except Exception:
            pass
    return changed


def decompose_layer_helpers(layer):
    changed = False
    for method_name in (
        "decomposeAllComponents",
        "decomposeCorners",
        "decomposeCornerComponents",
        "decomposeCornersAndCaps",
        "decomposeCornerComponentsAndCaps",
        "decomposeSmartOutlines",
        "decomposeHints",
    ):
        if call_decompose_method(layer, method_name):
            changed = True
    return changed


def fully_decomposed_layer_copy(font, source_glyph, source_layer):
    temp_glyph = None
    try:
        temp_glyph, layer_copy = source_layer_copy_in_temp_glyph(font, source_glyph, source_layer)

        previous_state = None
        for _ in range(10):
            before = (count_components(layer_copy), count_helper_hints(layer_copy), len(layer_copy.shapes))
            decompose_layer_components(layer_copy)
            decompose_layer_helpers(layer_copy)
            after = (count_components(layer_copy), count_helper_hints(layer_copy), len(layer_copy.shapes))
            if after == before or after == previous_state:
                break
            previous_state = before

        return layer_copy.copy()
    finally:
        if temp_glyph is not None:
            remove_temp_glyph(font, temp_glyph)


def copy_metric_attribute(source_layer, target_layer, attribute_name):
    if not hasattr(source_layer, attribute_name) or not hasattr(target_layer, attribute_name):
        return
    try:
        setattr(target_layer, attribute_name, getattr(source_layer, attribute_name))
    except Exception:
        pass


def copy_decomposed_layer_contents(font, source_glyph, source_layer, target_layer):
    source_copy = fully_decomposed_layer_copy(font, source_glyph, source_layer)

    clear_proxy(target_layer.shapes)
    clear_proxy(target_layer.anchors)
    if hasattr(target_layer, "hints"):
        clear_proxy(target_layer.hints)

    for shape in source_copy.shapes:
        target_layer.shapes.append(shape.copy())
    for anchor in source_copy.anchors:
        target_layer.anchors.append(anchor.copy())

    stem_count = copy_stems(source_layer, target_layer)
    target_layer.width = source_copy.width
    for attribute_name in ("leftMetricsKey", "rightMetricsKey", "widthMetricsKey"):
        copy_metric_attribute(source_layer, target_layer, attribute_name)

    return len(source_copy.shapes), len(source_copy.anchors), count_components(source_copy), count_helper_hints(source_copy), stem_count


def source_layer_for_target_layer(font, source_glyph, target_layer, weight_axis_id, mght_axis_id, intermediate_coordinates_by_layer_id):
    coordinates = intermediate_coordinates_by_layer_id.get(target_layer.layerId)
    if coordinates is None:
        coordinates = coordinates_for_layer(font, target_layer)

    if target_layer.isMasterLayer:
        target_weight = LOW_WEIGHT_VALUE
    else:
        target_weight = HIGH_WEIGHT_VALUE

    source_master = corresponding_master_for_weight(
        font,
        coordinates,
        weight_axis_id,
        mght_axis_id,
        target_weight,
    )
    if source_master is None:
        return None, target_weight

    source_layer = source_glyph.layers[source_master.id]
    return source_layer, target_weight


def copy_source_layers_into_target(font, glyph, source_glyph, weight_axis_id, mght_axis_id, intermediate_coordinates_by_layer_id):
    copied = 0
    skipped = 0

    for layer in glyph.layers:
        source_layer, target_weight = source_layer_for_target_layer(
            font,
            source_glyph,
            layer,
            weight_axis_id,
            mght_axis_id,
            intermediate_coordinates_by_layer_id,
        )
        if source_layer is None:
            skipped += 1
            print_warning("%s: could not find source layer for wght=%s" % (
                layer.name or layer.layerId,
                target_weight,
            ))
            continue

        shape_count, anchor_count, remaining_components, remaining_helpers, stem_count = copy_decomposed_layer_contents(
            font,
            source_glyph,
            source_layer,
            layer,
        )
        copied += 1
        print("%s: copied fully decomposed %s from %s (%i shapes, %i anchors, %i stems, width %s; remaining components %i, helpers %i)" % (
            layer.name or layer.layerId,
            source_glyph.name,
            source_layer.name or source_layer.layerId,
            shape_count,
            anchor_count,
            stem_count,
            layer.width,
            remaining_components,
            remaining_helpers,
        ))

    return copied, skipped


def process_bold_math_glyph(font, glyph, weight_axis_id, mght_axis_id):
    created = 0
    refreshed = 0
    skipped = 0
    layers_copied = 0
    copy_layers_skipped = 0
    intermediate_coordinates_by_layer_id = {}

    print("")
    print("[%s]" % glyph.name)

    source_glyph_name = source_name_for_bold_math_glyph(glyph.name)
    source_glyph = None
    if source_glyph_name is None:
        copy_layers_skipped += len(glyph.layers)
        print_warning("%s: skipped, could not derive source glyph name" % glyph.name)
        return process_stats(copy_layers_skipped=copy_layers_skipped)

    source_glyph = font.glyphs[source_glyph_name]
    if source_glyph is None:
        copy_layers_skipped += len(glyph.layers)
        print_warning("%s: skipped, missing source glyph %s" % (glyph.name, source_glyph_name))
        return process_stats(copy_layers_skipped=copy_layers_skipped)

    if source_glyph_has_special_layers(source_glyph):
        copy_layers_skipped += len(glyph.layers)
        print_warning("%s: skipped because source glyph %s has special/intermediate layers" % (
            glyph.name,
            source_glyph_name,
        ))
        return process_stats(copy_layers_skipped=copy_layers_skipped)

    for master in font.masters:
        master_layer = glyph.layers[master.id]
        if master_layer is None:
            skipped += 1
            print_warning("%s: skipped, no master layer found" % master.name)
            continue

        coordinates = master_coordinates(font, master)
        if coordinates is None:
            skipped += 1
            print_warning("%s: skipped, could not read master coordinates" % master.name)
            continue
        coordinates[str(mght_axis_id)] = float(TARGET_AXIS_VALUE)

        layer_name = intermediate_layer_name(master)
        existing_layer = matching_intermediate_layer(font, glyph, master.id, coordinates, name=layer_name)
        if existing_layer is None:
            layer = create_intermediate_layer(glyph, master_layer, master, coordinates, master_layer.width)
            intermediate_coordinates_by_layer_id[layer.layerId] = dict(coordinates)
            created += 1
            print("%s: created intermediate layer at %s" % (
                master.name,
                coordinates,
            ))
        else:
            layer = replace_layer_contents(existing_layer, coordinates, master.id, master_layer.width)
            intermediate_coordinates_by_layer_id[layer.layerId] = dict(coordinates)
            refreshed += 1
            print("%s: refreshed intermediate layer at %s" % (
                master.name,
                coordinates,
            ))

    copied, copy_skipped = copy_source_layers_into_target(
        font,
        glyph,
        source_glyph,
        weight_axis_id,
        mght_axis_id,
        intermediate_coordinates_by_layer_id,
    )
    layers_copied += copied
    copy_layers_skipped += copy_skipped

    print("%s summary: created %i, refreshed %i, skipped %i" % (
        glyph.name,
        created,
        refreshed,
        skipped,
    ))

    return process_stats(
        created=created,
        refreshed=refreshed,
        skipped=skipped,
        layers_copied=layers_copied,
        copy_layers_skipped=copy_layers_skipped,
        modified=True,
    )


def add_stats(total, update):
    for key, value in update.items():
        if key == "modified":
            continue
        if isinstance(value, int):
            total[key] = total.get(key, 0) + value


def process_stats(created=0, refreshed=0, skipped=0, layers_copied=0, copy_layers_skipped=0, modified=False):
    return {
        "created": created,
        "refreshed": refreshed,
        "skipped": skipped,
        "layers_copied": layers_copied,
        "copy_layers_skipped": copy_layers_skipped,
        "modified": int(bool(modified)),
    }


def run_for_glyphs(font, glyphs, open_tab=False):
    mght_axis_id = axis_id_for_tag(font, TARGET_AXIS_TAG)
    if mght_axis_id is None:
        print_warning("Could not find axis %s in the open font." % TARGET_AXIS_TAG)
        return

    weight_axis_id = axis_id_for_tag(font, WEIGHT_AXIS_TAG)
    if weight_axis_id is None:
        print_warning("Could not find axis %s in the open font." % WEIGHT_AXIS_TAG)
        return

    print("Font: %s" % (font.familyName or "Untitled"))
    print("Glyphs to process: %i" % len(glyphs))
    print("Target %s value: %s" % (TARGET_AXIS_TAG, TARGET_AXIS_VALUE))
    print("Master layers use wght=%s; intermediate layers use wght=%s." % (
        LOW_WEIGHT_VALUE,
        HIGH_WEIGHT_VALUE,
    ))
    print("")

    totals = {}
    modified_glyph_names = []
    font.disableUpdateInterface()
    try:
        for index, glyph in enumerate(glyphs, 1):
            print("[%i/%i] Processing %s" % (index, len(glyphs), glyph.name))
            stats = process_bold_math_glyph(font, glyph, weight_axis_id, mght_axis_id)
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
