#MenuTitle: Create Wide Layers for Selected Glyph
# -*- coding: utf-8 -*-

import uuid

from GlyphsApp import Glyphs, GSSmartComponentAxis


SCRIPT_VERSION = "2026-07-03 00:00 CDT create-wide-layers-smart-width-poles"
SMART_AXIS_NAME = "width"
SMART_AXIS_BOTTOM_VALUE = 0
SMART_AXIS_TOP_VALUE = 100
SMART_MASTER_SELECTION_VALUE = 1
SMART_WIDE_SELECTION_VALUE = 2


def print_warning(message):
    print("WARNING: %s" % message)


def safe_call(value, default=None):
    if callable(value):
        try:
            return value()
        except Exception:
            return default
    return value


def layer_index(glyph, target_layer):
    for index, layer in enumerate(glyph.layers):
        if layer is target_layer:
            return index
    return len(glyph.layers) - 1


def is_master_layer(layer):
    return bool(safe_call(getattr(layer, "isMasterLayer", False), False))


def layer_name(layer):
    return str(safe_call(getattr(layer, "name", ""), "") or "")


def associated_master_id(layer):
    value = safe_call(getattr(layer, "associatedMasterId", None))
    if value is None:
        return None
    return str(value)


def layer_id(layer):
    value = safe_call(getattr(layer, "layerId", None))
    if value is None:
        return None
    return str(value)


def copied_value(value):
    if hasattr(value, "copy"):
        try:
            return value.copy()
        except Exception:
            pass
    return value


def layer_attribute(layer, key):
    sentinel = object()
    direct_value = safe_call(getattr(layer, key, sentinel), sentinel)
    if direct_value is not sentinel and direct_value is not None:
        return direct_value

    for proxy_name in ("attributes", "attr"):
        attributes = getattr(layer, proxy_name, None)
        if attributes is None:
            continue
        try:
            return attributes[key]
        except Exception:
            pass

    for method_name in ("attributeForKey_", "valueForKey_"):
        method = getattr(layer, method_name, None)
        if method is None:
            continue
        try:
            value = method(key)
        except Exception:
            pass
        else:
            if value is not None:
                return value
    return None


def set_layer_attribute(layer, key, value):
    value = copied_value(value)
    for method_name in ("setAttribute_forKey_", "setValue_forKey_"):
        method = getattr(layer, method_name, None)
        if method is None:
            continue
        try:
            method(value, key)
            return True
        except Exception:
            pass

    for proxy_name in ("attributes", "attr"):
        attributes = getattr(layer, proxy_name, None)
        if attributes is None:
            continue
        try:
            attributes[key] = value
            return True
        except Exception:
            pass
    return False


def set_associated_master_id(layer, associated_master_id):
    method = getattr(layer, "setAssociatedMasterId_", None)
    if method is not None:
        try:
            method(associated_master_id)
            return
        except Exception:
            pass
    try:
        layer.associatedMasterId = associated_master_id
    except Exception:
        pass


def remove_layer(glyph, layer):
    for method_name in ("remove_", "removeObject_", "removeObject", "removeLayer_"):
        method = getattr(glyph.layers, method_name, None)
        if method is None:
            continue
        try:
            method(layer)
            return True
        except Exception:
            pass

    current_layer_id = layer_id(layer)
    if current_layer_id is not None:
        try:
            del glyph.layers[current_layer_id]
            return True
        except Exception:
            pass
    return False


def set_object_attribute(obj, attribute_name, value):
    try:
        setattr(obj, attribute_name, value)
        return True
    except Exception:
        pass

    method_name = "set%s%s_" % (attribute_name[:1].upper(), attribute_name[1:])
    method = getattr(obj, method_name, None)
    if method is not None:
        try:
            method(value)
            return True
        except Exception:
            pass
    return False


def smart_axis_name(axis):
    return str(safe_call(getattr(axis, "name", ""), "") or "")


def axis_identifier(axis):
    for attribute_name in ("id", "axisId"):
        value = safe_call(getattr(axis, attribute_name, None))
        if value:
            return str(value)
    return None


def glyph_smart_axes(glyph):
    try:
        return list(glyph.smartComponentAxes or [])
    except Exception:
        return []


def append_smart_axis(glyph, axis):
    try:
        glyph.smartComponentAxes.append(axis)
        return True
    except Exception:
        pass

    try:
        axes = list(glyph.smartComponentAxes or [])
    except Exception:
        axes = []
    axes.append(axis)
    try:
        glyph.smartComponentAxes = axes
        return True
    except Exception:
        return False


def ensure_width_smart_axis(glyph):
    width_axis = None
    for axis in glyph_smart_axes(glyph):
        if smart_axis_name(axis) == SMART_AXIS_NAME:
            width_axis = axis
            break

    created = False
    if width_axis is None:
        width_axis = GSSmartComponentAxis()
        set_object_attribute(width_axis, "name", SMART_AXIS_NAME)
        if not append_smart_axis(glyph, width_axis):
            print_warning("%s: could not add smart glyph axis %s." % (glyph.name, SMART_AXIS_NAME))
            return None, False
        created = True

    set_object_attribute(width_axis, "name", SMART_AXIS_NAME)
    set_object_attribute(width_axis, "bottomValue", SMART_AXIS_BOTTOM_VALUE)
    set_object_attribute(width_axis, "topValue", SMART_AXIS_TOP_VALUE)
    return width_axis, created


def set_smart_component_pole_mapping(layer, axis, selection_value):
    axis_id = axis_identifier(axis)
    if axis_id is None:
        return False

    mapping = getattr(layer, "smartComponentPoleMapping", None)
    if mapping is not None:
        try:
            mapping[axis_id] = selection_value
            return True
        except Exception:
            pass

        try:
            mapping = dict(mapping or {})
            mapping[axis_id] = selection_value
            layer.smartComponentPoleMapping = mapping
            return True
        except Exception:
            pass

    try:
        mapping = dict(layer_attribute(layer, "smartComponentPoleMapping") or {})
    except Exception:
        mapping = {}
    mapping[axis_id] = selection_value
    return set_layer_attribute(layer, "smartComponentPoleMapping", mapping)


def set_width_layer_properties(layer, axis, selection_value):
    try:
        part_selection = dict(layer_attribute(layer, "partSelection") or {})
    except Exception:
        part_selection = {}
    part_selection[SMART_AXIS_NAME] = selection_value

    changed = False
    if set_layer_attribute(layer, "partSelection", part_selection):
        changed = True
    if set_smart_component_pole_mapping(layer, axis, selection_value):
        changed = True
    return changed


def set_master_width_layer_properties(glyph, axis):
    changed = 0
    for layer in glyph.layers:
        if not is_master_layer(layer):
            continue
        if set_width_layer_properties(layer, axis, SMART_MASTER_SELECTION_VALUE):
            changed += 1
    return changed


def is_high_layer(layer):
    return (not is_master_layer(layer)) and ("High" in layer_name(layer))


def set_high_layers_width_low(glyph, axis):
    changed = 0
    for layer in glyph.layers:
        if not is_high_layer(layer):
            continue
        if set_width_layer_properties(layer, axis, SMART_MASTER_SELECTION_VALUE):
            changed += 1
    return changed


def wide_layer_name(master):
    return "%s Wide" % master.name


def remove_existing_wide_layers(glyph, master):
    removed = 0
    expected_name = wide_layer_name(master)
    expected_master_id = str(master.id)
    for layer in list(glyph.layers):
        if is_master_layer(layer):
            continue
        if layer_name(layer) != expected_name:
            continue
        if associated_master_id(layer) != expected_master_id:
            continue
        if remove_layer(glyph, layer):
            removed += 1
    return removed


def selected_glyph(font):
    selected_layers = list(font.selectedLayers or [])
    if not selected_layers:
        return None
    return selected_layers[0].parent


def create_wide_layer(glyph, master, width_axis):
    removed_count = remove_existing_wide_layers(glyph, master)
    master_layer = glyph.layers[master.id]
    if master_layer is None:
        print_warning("%s: no layer for master %s" % (glyph.name, master.name))
        return None, removed_count

    wide_layer = master_layer.copy()
    wide_layer.layerId = str(uuid.uuid4()).upper()
    set_associated_master_id(wide_layer, master.id)
    wide_layer.name = wide_layer_name(master)
    set_width_layer_properties(wide_layer, width_axis, SMART_WIDE_SELECTION_VALUE)
    glyph.layers.insert(layer_index(glyph, master_layer) + 1, wide_layer)
    return wide_layer, removed_count


Glyphs.clearLog()
Glyphs.showMacroWindow()
print("Create Wide Layers for Selected Glyph")
print("Script version: %s" % SCRIPT_VERSION)
print("")

font = Glyphs.font
if font is None:
    print_warning("No font open.")
else:
    glyph = selected_glyph(font)
    if glyph is None:
        print_warning("No glyph selected.")
    else:
        print("Glyph: %s" % glyph.name)
        created_count = 0
        removed_existing_count = 0
        master_property_count = 0
        high_width_low_count = 0
        smart_axis_created = False

        font.disableUpdateInterface()
        try:
            width_axis, smart_axis_created = ensure_width_smart_axis(glyph)
            master_property_count = set_master_width_layer_properties(glyph, width_axis)
            high_width_low_count = set_high_layers_width_low(glyph, width_axis)
            for master in font.masters:
                wide_layer, removed_count = create_wide_layer(glyph, master, width_axis)
                removed_existing_count += removed_count
                if wide_layer is not None:
                    created_count += 1
                    print("Created layer: %s" % wide_layer.name)
        finally:
            font.enableUpdateInterface()

        print("")
        print("%s smart glyph axis %s: %s..%s" % (
            "Created" if smart_axis_created else "Updated",
            SMART_AXIS_NAME,
            SMART_AXIS_BOTTOM_VALUE,
            SMART_AXIS_TOP_VALUE,
        ))
        print("Set %s=off on %i master layer(s)." % (SMART_AXIS_NAME, master_property_count))
        print("Set %s=%s on %i High layer(s)." % (SMART_AXIS_NAME, SMART_AXIS_BOTTOM_VALUE, high_width_low_count))
        print("Set %s=on on %i Wide layer(s)." % (SMART_AXIS_NAME, created_count))
        print("Removed %i existing matching Wide layer(s)." % removed_existing_count)
        print("Done. Created %i Wide layer(s)." % created_count)
