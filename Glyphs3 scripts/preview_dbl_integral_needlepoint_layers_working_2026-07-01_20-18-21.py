#MenuTitle: Backup - Preview dblIntegral Needlepoint Layers (Working 2026-07-01)
# -*- coding: utf-8 -*-

import uuid

import vanilla
from AppKit import (
    NSAffineTransform,
    NSBezierPath,
    NSColor,
    NSImage,
    NSMakeRect,
    NSMakeSize,
)
from Foundation import NSTimer
from GlyphsApp import Glyphs, GSLayer


SCRIPT_VERSION = "2026-07-01 21:58 CDT selected-glyph-height-axis-restored"
BOX_MASTER_NAMES = (
    "Needlepoint SemiCondensed Upright",
    "Needlepoint SemiExpanded Upright",
    "Needlepoint Black SemiCondensed Upright",
    "Needlepoint Black SemiExpanded Upright",
    "Agate SemiCondensed Upright",
    "Agate SemiExpanded Upright",
    "Agate Black SemiCondensed Upright",
    "Agate Black SemiExpanded Upright",
)
SAMPLE_STEPS = (0.0, 0.5, 1.0)
SMART_HEIGHT_AXIS_NAME = "height"
SMART_HEIGHT_VALUES = (0.0, 50.0, 100.0)
WINDOW_SIZE = (1120, 980)
WINDOW_MIN_SIZE = (1040, 740)
REDRAW_INTERVAL = 0.85
FIXED_DESIGN_WIDTH = 1800.0
FIXED_DESIGN_HEIGHT = 7200.0
DEFAULT_GLYPH_SCALE = 0.92


def print_warning(message):
    print("WARNING: %s" % message)


def safe_call(value, default=None):
    if callable(value):
        try:
            return value()
        except Exception:
            return default
    return value


def master_name(master):
    return str(safe_call(getattr(master, "name", None), "") or "")


def glyph_name(glyph):
    return str(safe_call(getattr(glyph, "name", None), "") or "")


def glyph_for_name(font, glyph_name):
    try:
        return font.glyphs[glyph_name]
    except Exception:
        return None


def selected_glyph(font):
    try:
        selected_layers = list(font.selectedLayers or [])
    except Exception:
        selected_layers = []
    if selected_layers:
        glyph = safe_call(getattr(selected_layers[0], "parent", None))
        if glyph is not None:
            return glyph
    try:
        return font.glyphs[0]
    except Exception:
        return None


def component_name(component):
    for attribute_name in ("componentName", "name"):
        value = safe_call(getattr(component, attribute_name, None))
        if value:
            return str(value)
    return ""


def component_glyph(font, component):
    name = component_name(component)
    if not name:
        return None
    return glyph_for_name(font, name)


def layer_name(layer):
    return str(safe_call(getattr(layer, "name", None), "") or "")


def layer_id(layer):
    value = safe_call(getattr(layer, "layerId", None))
    if value is None:
        return None
    return str(value)


def axis_id(axis):
    for attribute_name in ("axisId", "id"):
        value = safe_call(getattr(axis, attribute_name, None))
        if value:
            return str(value)
    return None


def axis_name(axis):
    return str(safe_call(getattr(axis, "name", None), "") or "")


def smart_axis_name(axis):
    return str(safe_call(getattr(axis, "name", None), "") or "")


def smart_axis_for_name(glyph, wanted_name):
    if glyph is None:
        return None
    try:
        axes = list(glyph.smartComponentAxes or [])
    except Exception:
        axes = []
    for axis in axes:
        if smart_axis_name(axis).lower() == str(wanted_name).lower():
            return axis
    return None


def smart_axis_id_for_component(font, component, smart_axis_name_value):
    glyph = component_glyph(font, component)
    axis = smart_axis_for_name(glyph, smart_axis_name_value)
    return axis_id(axis) if axis is not None else None


def set_component_smart_value(component, smart_axis_id, value):
    if smart_axis_id is None or not hasattr(component, "smartComponentValues"):
        return False
    try:
        component.smartComponentValues[smart_axis_id] = value
        return True
    except Exception:
        pass
    try:
        values = dict(component.smartComponentValues or {})
        values[smart_axis_id] = value
        component.smartComponentValues = values
        return True
    except Exception:
        return False


def compact_name(name):
    return str(name or "").lower().replace(" ", "")


def master_for_name(font, wanted_name):
    try:
        masters = list(font.masters)
    except Exception:
        masters = []

    for master in masters:
        if master_name(master) == wanted_name:
            return master

    wanted_compact = compact_name(wanted_name)
    for master in masters:
        if compact_name(master_name(master)) == wanted_compact:
            return master

    return None


def layer_for_master(glyph, master):
    if glyph is None or master is None:
        return None

    master_id = getattr(master, "id", None)
    if master_id:
        try:
            layer = glyph.layers[master_id]
            if layer is not None:
                return layer
        except Exception:
            pass

    for layer in glyph.layers:
        if getattr(layer, "associatedMasterId", None) == master_id:
            return layer
        if getattr(layer, "layerId", None) == master_id:
            return layer

    return None


def layer_for_hint(glyph, hint_layer):
    if glyph is None or hint_layer is None:
        return None

    hint_layer_id = getattr(hint_layer, "layerId", None)
    if hint_layer_id:
        try:
            layer = glyph.layers[hint_layer_id]
            if layer is not None:
                return layer
        except Exception:
            pass

    hint_associated_master_id = getattr(hint_layer, "associatedMasterId", None)
    hint_name = layer_name(hint_layer)
    for layer in glyph.layers:
        if hint_name and layer_name(layer) == hint_name:
            return layer
        if hint_associated_master_id and getattr(layer, "associatedMasterId", None) == hint_associated_master_id:
            return layer

    return None


def master_coordinates(font, master):
    coordinates = {}
    try:
        axes = list(font.axes)
    except Exception:
        axes = []

    for index, axis in enumerate(axes):
        current_axis_id = axis_id(axis)
        if current_axis_id is None:
            return None
        try:
            coordinates[current_axis_id] = float(master.axisValueValueForId_(current_axis_id))
            continue
        except Exception:
            pass
        try:
            coordinates[current_axis_id] = float(master.axesValues[index])
            continue
        except Exception:
            return None

    return coordinates


def axis_infos(font):
    try:
        axes = list(font.axes)
    except Exception:
        axes = []

    infos = []
    for axis in axes:
        current_axis_id = axis_id(axis)
        if current_axis_id is not None:
            infos.append((axis, current_axis_id))
    return infos


def master_coordinate_records(font, master_names):
    records = []
    missing = []
    for name in master_names:
        master = master_for_name(font, name)
        if master is None:
            missing.append(name)
            continue
        coordinates = master_coordinates(font, master)
        if coordinates is None:
            missing.append("%s coordinates" % name)
            continue
        records.append((master, coordinates))
    return records, missing


def box_axis_ids(font, records):
    infos = axis_infos(font)
    varying = []
    for _axis, current_axis_id in infos:
        values = sorted(set(coordinates[current_axis_id] for _master, coordinates in records))
        if len(values) > 1:
            varying.append(current_axis_id)
        if len(varying) == 3:
            break
    return varying


def axis_sample_values(records, current_axis_id):
    values = sorted(set(coordinates[current_axis_id] for _master, coordinates in records))
    if not values:
        return None
    if len(values) == 1:
        return (values[0], values[0], values[0])
    low = values[0]
    high = values[-1]
    return (low, (low + high) / 2.0, high)


def sample_labels_for_dimension(axis_label, samples):
    normalized = axis_label.lower()
    if "optical" in normalized:
        return ("Agate", "Optical midpoint", "Needlepoint")
    if "width" in normalized:
        return ("SemiCondensed", "Width midpoint", "SemiExpanded")
    if "weight" in normalized:
        return ("Normal", "Weight midpoint", "Black")
    if axis_label == SMART_HEIGHT_AXIS_NAME:
        return ("Low", "Medium", "High")
    return tuple(str(value) for value in samples)


def box_model(font, glyph, smart_height_values=None):
    records, missing = master_coordinate_records(font, BOX_MASTER_NAMES)
    if missing:
        return None, missing
    if not records:
        return None, ["box masters"]

    varying_axis_ids = box_axis_ids(font, records)
    if len(varying_axis_ids) < 3:
        return None, ["three varying box axes"]

    base_coordinates = dict(records[0][1])
    samples = {}
    for current_axis_id in varying_axis_ids:
        values = axis_sample_values(records, current_axis_id)
        if values is None:
            return None, ["axis samples"]
        samples[current_axis_id] = values

    dimensions = []
    for current_axis_id in varying_axis_ids:
        axis_label = current_axis_id
        for axis, axis_id_value in axis_infos(font):
            if axis_id_value == current_axis_id:
                axis_label = axis_name(axis) or current_axis_id
                break
        dimensions.append({
            "kind": "font",
            "id": current_axis_id,
            "label": axis_label,
            "samples": samples[current_axis_id],
            "sample_labels": sample_labels_for_dimension(axis_label, samples[current_axis_id]),
        })

    height_samples = tuple(smart_height_values or SMART_HEIGHT_VALUES)
    dimensions.append({
        "kind": "smart",
        "id": SMART_HEIGHT_AXIS_NAME,
        "label": SMART_HEIGHT_AXIS_NAME,
        "samples": height_samples,
        "sample_labels": sample_labels_for_dimension(SMART_HEIGHT_AXIS_NAME, height_samples),
    })

    return {
        "records": records,
        "axis_ids": varying_axis_ids,
        "base_coordinates": base_coordinates,
        "samples": samples,
        "dimensions": dimensions,
    }, []


def sample_for_grid_position(model, axis_order, axis_enabled, fixed_indices, outer_row, outer_col, inner_row, inner_col):
    position_values = (outer_row, outer_col, inner_row, inner_col)
    coordinates = dict(model["base_coordinates"])
    smart_values = {}

    for position_index, sample_index in enumerate(position_values):
        axis_index = axis_order[position_index]
        if axis_index < 0 or axis_index >= len(model["dimensions"]):
            continue
        dimension = model["dimensions"][axis_index]
        sample_index = effective_sample_index(axis_enabled[position_index], fixed_indices[position_index], sample_index)
        value = dimension["samples"][sample_index]
        if dimension["kind"] == "font":
            coordinates[dimension["id"]] = value
        else:
            smart_values[dimension["id"]] = value

    return coordinates, smart_values


def effective_sample_index(enabled, fixed_index, sample_index):
    if enabled:
        return sample_index
    return fixed_index


def cell_coordinate_text(model, axis_order, axis_enabled, fixed_indices, outer_row, outer_col, inner_row, inner_col):
    position_values = (outer_row, outer_col, inner_row, inner_col)
    label_parts = []
    detail_parts = []
    for position_index, sample_index in enumerate(position_values):
        axis_index = axis_order[position_index]
        if axis_index < 0 or axis_index >= len(model["dimensions"]):
            continue
        dimension = model["dimensions"][axis_index]
        sample_index = effective_sample_index(axis_enabled[position_index], fixed_indices[position_index], sample_index)
        sample_label = dimension["sample_labels"][sample_index]
        sample_value = dimension["samples"][sample_index]
        label_parts.append(sample_label)
        detail_parts.append("%s: %s (%s)" % (dimension["label"], sample_label, sample_value))
    return "%s\n%s" % (" ".join(label_parts), "\n".join(detail_parts))


def coordinate_distance(first, second, axis_ids):
    distance = 0.0
    for current_axis_id in axis_ids:
        distance += abs(float(first[current_axis_id]) - float(second[current_axis_id]))
    return distance


def nearest_master_record(model, coordinates):
    records = model["records"]
    axis_ids = model["axis_ids"]
    return min(records, key=lambda record: coordinate_distance(record[1], coordinates, axis_ids))


def copied_value(value):
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return [copied_value(item) for item in value]
    if hasattr(value, "keys"):
        return dict(value)
    return value


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


def set_layer_part_selection(layer, values):
    if not values:
        return True
    try:
        layer.partSelection = dict(values)
    except Exception:
        pass
    return set_layer_attribute(layer, "partSelection", dict(values))


def set_associated_master_id(layer, associated_master_id):
    method = getattr(layer, "setAssociatedMasterId_", None)
    if method is not None:
        try:
            method(associated_master_id)
            return True
        except Exception:
            pass
    try:
        layer.associatedMasterId = associated_master_id
        return True
    except Exception:
        return False


def glyph_has_layer_id(glyph, target_layer_id):
    if target_layer_id is None:
        return False
    for layer in glyph.layers:
        if layer_id(layer) == target_layer_id:
            return True
    return False


def remove_layer(glyph, layer):
    target_layer_id = layer_id(layer)
    for method_name in ("remove_", "removeObject_", "removeObject", "removeLayer_"):
        method = getattr(glyph.layers, method_name, None)
        if method is None:
            continue
        try:
            method(layer)
            if not glyph_has_layer_id(glyph, target_layer_id):
                return True
        except Exception:
            pass

    if target_layer_id is not None:
        try:
            del glyph.layers[target_layer_id]
            if not glyph_has_layer_id(glyph, target_layer_id):
                return True
        except Exception:
            pass
    return False


def call_layer_method(layer, method_name):
    method = getattr(layer, method_name, None)
    if method is None:
        return False
    try:
        method()
        return True
    except Exception:
        return False


def interpolated_layer_for_coordinates(glyph, model, coordinates, smart_values=None):
    base_master, _base_coordinates = nearest_master_record(model, coordinates)
    base_layer = layer_for_master(glyph, base_master)
    if base_layer is None:
        return None, ["source layer: %s" % master_name(base_master)]

    layer = base_layer.copy()
    layer.layerId = str(uuid.uuid4()).upper()
    layer.name = "__tmp_%s_grid" % glyph_name(glyph)
    set_associated_master_id(layer, base_master.id)
    set_layer_attribute(layer, "coordinates", coordinates)

    glyph.layers.append(layer)
    try:
        call_layer_method(layer, "reinterpolate")
        call_layer_method(layer, "reinterpolateMetrics")
        call_layer_method(layer, "syncMetrics")
        return layer, []
    except Exception:
        remove_layer(glyph, layer)
        return None, ["grid interpolation"]


def image_for_coordinates(glyph, model, coordinates, smart_values, width, height, normalize_size=True, glyph_scale=1.0):
    layer, missing = interpolated_layer_for_coordinates(glyph, model, coordinates, smart_values)
    if layer is None:
        return image_for_layer(None, width, height, smart_values, normalize_size, glyph_scale), missing

    try:
        return image_for_layer(layer, width, height, smart_values, normalize_size, glyph_scale), missing
    finally:
        remove_layer(glyph, layer)


def append_path(target_path, source_path):
    if source_path is None:
        return False

    try:
        if source_path.isEmpty():
            return False
    except Exception:
        pass

    try:
        target_path.appendBezierPath_(source_path)
        return True
    except Exception:
        return False


def layer_direct_path(layer):
    path = NSBezierPath.bezierPath()
    appended = False

    try:
        layer_paths = list(layer.paths)
    except Exception:
        layer_paths = []

    for layer_path_item in layer_paths:
        for attribute_name in ("bezierPath", "completeBezierPath"):
            path_value = safe_call(getattr(layer_path_item, attribute_name, None))
            if append_path(path, path_value):
                appended = True
                break

    return path if appended else None


def component_transform_values(component):
    transform = safe_call(getattr(component, "transform", None))
    if transform is not None:
        try:
            return (
                float(transform.m11),
                float(transform.m12),
                float(transform.m21),
                float(transform.m22),
                float(transform.tX),
                float(transform.tY),
            )
        except Exception:
            pass
        try:
            values = list(transform)
            if len(values) == 6:
                return tuple(float(value) for value in values)
        except Exception:
            pass

    return (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def affine_transform_from_values(values):
    transform = NSAffineTransform.transform()
    try:
        transform_struct = transform.transformStruct()
        (
            transform_struct.m11,
            transform_struct.m12,
            transform_struct.m21,
            transform_struct.m22,
            transform_struct.tX,
            transform_struct.tY,
        ) = values
        transform.setTransformStruct_(transform_struct)
    except Exception:
        pass
    return transform


def point_tuple(value):
    if value is None:
        return None
    try:
        return (float(value.x), float(value.y))
    except Exception:
        pass
    try:
        values = list(value)
        if len(values) >= 2:
            return (float(values[0]), float(values[1]))
    except Exception:
        pass
    return None


def anchor_position(layer, anchor_name):
    if layer is None:
        return None

    try:
        anchors = list(layer.anchors)
    except Exception:
        anchors = []

    for anchor in anchors:
        if str(safe_call(getattr(anchor, "name", None), "") or "") != anchor_name:
            continue
        for attribute_name in ("position", "pos"):
            position = point_tuple(safe_call(getattr(anchor, attribute_name, None)))
            if position is not None:
                return position
    return None


def layer_part_selection_value(layer, key):
    if layer is None:
        return None
    for source in (
        safe_call(getattr(layer, "partSelection", None)),
        safe_call(getattr(layer, "attr", None)),
        safe_call(getattr(layer, "attributes", None)),
    ):
        if not source:
            continue
        try:
            if key in source:
                return source[key]
        except Exception:
            pass
        try:
            part_selection = source["partSelection"]
            if key in part_selection:
                return part_selection[key]
        except Exception:
            pass
    return None


def smart_anchor_position(component, smart_axis_name_value, smart_axis_value, anchor_name):
    glyph = component_glyph(Glyphs.font, component)
    hint_layer = safe_call(getattr(component, "componentLayer", None))
    if glyph is None or hint_layer is None:
        return None

    associated_master_id = getattr(hint_layer, "associatedMasterId", None) or layer_id(hint_layer)
    low_layer = None
    high_layer = None
    for layer in glyph.layers:
        if associated_master_id and getattr(layer, "associatedMasterId", None) not in (None, associated_master_id):
            continue
        selection = layer_part_selection_value(layer, smart_axis_name_value)
        if selection == 1:
            low_layer = layer
        elif selection == 2:
            high_layer = layer

    if low_layer is None:
        low_layer = layer_for_hint(glyph, hint_layer)
    if high_layer is None:
        high_layer = low_layer

    low_anchor = anchor_position(low_layer, anchor_name)
    high_anchor = anchor_position(high_layer, anchor_name)
    if low_anchor is None:
        return high_anchor
    if high_anchor is None:
        return low_anchor

    factor = max(0.0, min(1.0, float(smart_axis_value) / 100.0))
    return (
        low_anchor[0] + (high_anchor[0] - low_anchor[0]) * factor,
        low_anchor[1] + (high_anchor[1] - low_anchor[1]) * factor,
    )


def transformed_point(values, point):
    if point is None:
        return None

    m11, m12, m21, m22, tx, ty = values
    x, y = point
    return (
        m11 * x + m21 * y + tx,
        m12 * x + m22 * y + ty,
    )


def values_with_translation(values, tx, ty):
    m11, m12, m21, m22, _old_tx, _old_ty = values
    return (m11, m12, m21, m22, tx, ty)


def values_aligned_to_entry(values, entry_point, target_point):
    if entry_point is None or target_point is None:
        return values

    m11, m12, m21, m22, _tx, _ty = values
    entry_x, entry_y = entry_point
    target_x, target_y = target_point
    return values_with_translation(
        values,
        target_x - (m11 * entry_x + m21 * entry_y),
        target_y - (m12 * entry_x + m22 * entry_y),
    )


def component_source_layer(component):
    component_layer_hint = safe_call(getattr(component, "componentLayer", None))
    component_layer = component_layer_hint
    name = component_name(component)
    if name:
        component_glyph = glyph_for_name(Glyphs.font, name)
        live_layer = layer_for_hint(component_glyph, component_layer_hint)
        if live_layer is not None:
            component_layer = live_layer

    return component_layer


def component_layer_path(component, seen, draw_smart_values=None, transform_values=None):
    component_layer = component_source_layer(component)
    source_path = layer_path(component_layer, seen, draw_smart_values)
    if source_path is None:
        return None

    if transform_values is None:
        transform_values = component_transform_values(component)

    transformed_path = source_path.copy()
    transformed_path.transformUsingAffineTransform_(
        affine_transform_from_values(transform_values)
    )
    return transformed_path


def layer_component_path(layer, seen, draw_smart_values=None):
    path = NSBezierPath.bezierPath()
    appended = False
    previous_exit = None

    try:
        components = list(layer.components)
    except Exception:
        components = []

    for component in components:
        applied_smart_values = {}
        if draw_smart_values:
            for smart_axis_name_value, smart_axis_value in draw_smart_values.items():
                smart_axis_id = smart_axis_id_for_component(Glyphs.font, component, smart_axis_name_value)
                if set_component_smart_value(component, smart_axis_id, smart_axis_value):
                    applied_smart_values[smart_axis_name_value] = smart_axis_value

        component_layer = component_source_layer(component)
        original_transform_values = component_transform_values(component)
        transform_values = original_transform_values
        entry_point = None
        for smart_axis_name_value, smart_axis_value in applied_smart_values.items():
            entry_point = smart_anchor_position(component, smart_axis_name_value, smart_axis_value, "#entry")
            if entry_point is not None:
                break
        if entry_point is None:
            entry_point = anchor_position(component_layer, "#entry")
        transform_values = values_aligned_to_entry(transform_values, entry_point, previous_exit)

        path_value = None
        if applied_smart_values:
            path_value = safe_call(getattr(component, "bezierPath", None))
            if path_value is not None:
                path_value = path_value.copy()
                translation = NSAffineTransform.transform()
                translation.translateXBy_yBy_(
                    transform_values[4] - original_transform_values[4],
                    transform_values[5] - original_transform_values[5],
                )
                path_value.transformUsingAffineTransform_(translation)
            if append_path(path, path_value):
                appended = True
        if path_value is None:
            path_value = component_layer_path(component, seen, draw_smart_values, transform_values)
            if append_path(path, path_value):
                appended = True
            else:
                path_value = safe_call(getattr(component, "bezierPath", None))
                if append_path(path, path_value):
                    appended = True

        exit_point = None
        for smart_axis_name_value, smart_axis_value in applied_smart_values.items():
            exit_point = smart_anchor_position(component, smart_axis_name_value, smart_axis_value, "#exit")
            if exit_point is not None:
                break
        if exit_point is None:
            exit_point = anchor_position(component_layer, "#exit")
        previous_exit = transformed_point(transform_values, exit_point)

    return path if appended else None


def layer_path(layer, seen=None, draw_smart_values=None):
    if layer is None:
        return None

    if seen is None:
        seen = set()
    layer_key = id(layer)
    if layer_key in seen:
        return None
    seen = set(seen)
    seen.add(layer_key)

    path = NSBezierPath.bezierPath()
    appended = False

    if append_path(path, layer_direct_path(layer)):
        appended = True
    if append_path(path, layer_component_path(layer, seen, draw_smart_values)):
        appended = True
    if appended:
        return path

    for attribute_name in ("bezierPath", "completeBezierPath"):
        value = safe_call(getattr(layer, attribute_name, None))
        if value is not None:
            return value
    return None


def image_for_layer(layer, width, height, draw_smart_values=None, normalize_size=True, glyph_scale=1.0):
    image = NSImage.alloc().initWithSize_(NSMakeSize(width, height))
    image.lockFocus()
    try:
        rect = NSMakeRect(0, 0, width, height)
        NSColor.whiteColor().set()
        NSBezierPath.fillRect_(rect)
        NSColor.lightGrayColor().set()
        NSBezierPath.strokeRect_(rect)

        path = layer_path(layer, draw_smart_values=draw_smart_values)
        if path is None:
            return image

        path_bounds = path.bounds()
        if path_bounds.size.width <= 0 or path_bounds.size.height <= 0:
            return image

        margin = 18.0
        draw_rect = NSMakeRect(margin, margin, width - 2 * margin, height - 2 * margin)
        if normalize_size:
            scale_x = draw_rect.size.width / path_bounds.size.width
            scale_y = draw_rect.size.height / path_bounds.size.height
        else:
            scale_x = draw_rect.size.width / FIXED_DESIGN_WIDTH
            scale_y = draw_rect.size.height / FIXED_DESIGN_HEIGHT
        scale = min(scale_x, scale_y) * float(glyph_scale)

        transform = NSAffineTransform.transform()
        target_x = draw_rect.origin.x + (draw_rect.size.width - path_bounds.size.width * scale) / 2.0
        target_y = draw_rect.origin.y + (draw_rect.size.height - path_bounds.size.height * scale) / 2.0
        transform.translateXBy_yBy_(target_x, target_y)
        transform.scaleXBy_yBy_(scale, scale)
        transform.translateXBy_yBy_(-path_bounds.origin.x, -path_bounds.origin.y)

        drawn_path = path.copy()
        drawn_path.transformUsingAffineTransform_(transform)
        NSColor.blackColor().set()
        drawn_path.fill()
    finally:
        image.unlockFocus()
    return image


class DblIntegralNeedlepointPreview(object):

    def __init__(self):
        self.font = Glyphs.font
        if self.font is None:
            print_warning("No font open.")
            return
        self.glyph = selected_glyph(self.font)
        if self.glyph is None:
            print_warning("No glyph selected.")
            return
        self.glyph_name = glyph_name(self.glyph)
        self.has_smart_height_axis = True

        self.smart_height_values = list(SMART_HEIGHT_VALUES)
        model, _missing = box_model(self.font, self.glyph, self.smart_height_values)
        if model is not None:
            self.dimension_labels = [dimension["label"] for dimension in model["dimensions"]]
        else:
            self.dimension_labels = ["Axis 1", "Axis 2", "Axis 3"]
        dimension_count = len(self.dimension_labels)
        self.axis_order = list(range(min(4, dimension_count))) + [-1] * max(0, 4 - dimension_count)
        self.axis_enabled = [index < dimension_count for index in range(4)]
        self.axis_fixed_indices = [1, 1, 1, 0]
        self.normalize_size = True
        self.glyph_scale = DEFAULT_GLYPH_SCALE
        self.needs_redraw = False
        self.is_updating = False
        self.info_window = None

        self.image_width = 80
        self.image_height = 80
        self.w = vanilla.FloatingWindow(
            WINDOW_SIZE,
            "%s Needlepoint Preview" % self.glyph_name,
            minSize=WINDOW_MIN_SIZE,
        )
        self.w.title = vanilla.TextBox((15, 12, -15, 18), "%s grid preview" % self.glyph_name)
        self.w.outerRowLabel = vanilla.TextBox((20, 38, 70, 18), "Outer row")
        self.w.outerRowEnable = vanilla.CheckBox((76, 35, 18, 20), "", value=True, callback=self.axis_enabled_changed)
        self.w.outerRow = vanilla.PopUpButton((90, 34, 125, 24), self.dimension_labels, callback=self.axis_order_changed)
        self.w.outerRowFixed = vanilla.PopUpButton((0, 0, 55, 24), ["Low", "Middle", "High"], callback=self.axis_fixed_changed)
        self.w.outerColLabel = vanilla.TextBox((230, 38, 70, 18), "Outer column")
        self.w.outerColEnable = vanilla.CheckBox((286, 35, 18, 20), "", value=True, callback=self.axis_enabled_changed)
        self.w.outerCol = vanilla.PopUpButton((300, 34, 125, 24), self.dimension_labels, callback=self.axis_order_changed)
        self.w.outerColFixed = vanilla.PopUpButton((0, 0, 55, 24), ["Low", "Middle", "High"], callback=self.axis_fixed_changed)
        self.w.innerRowLabel = vanilla.TextBox((440, 38, 70, 18), "Inner row")
        self.w.innerRowEnable = vanilla.CheckBox((496, 35, 18, 20), "", value=True, callback=self.axis_enabled_changed)
        self.w.innerRow = vanilla.PopUpButton((510, 34, 125, 24), self.dimension_labels, callback=self.axis_order_changed)
        self.w.innerRowFixed = vanilla.PopUpButton((0, 0, 55, 24), ["Low", "Middle", "High"], callback=self.axis_fixed_changed)
        self.w.innerColLabel = vanilla.TextBox((650, 38, 70, 18), "Inner column")
        self.w.innerColEnable = vanilla.CheckBox((706, 35, 18, 20), "", value=True, callback=self.axis_enabled_changed)
        self.w.innerCol = vanilla.PopUpButton((720, 34, 125, 24), self.dimension_labels, callback=self.axis_order_changed)
        self.w.innerColFixed = vanilla.PopUpButton((0, 0, 55, 24), ["Low", "Middle", "High"], callback=self.axis_fixed_changed)
        self.w.heightLabel = vanilla.TextBox((20, 66, 94, 18), "Height values")
        self.w.heightLow = vanilla.EditText((114, 62, 58, 24), "0", callback=self.height_values_changed)
        self.w.heightMid = vanilla.EditText((178, 62, 58, 24), "50", callback=self.height_values_changed)
        self.w.heightHigh = vanilla.EditText((242, 62, 58, 24), "100", callback=self.height_values_changed)
        self.w.normalizeSize = vanilla.CheckBox((320, 64, 130, 20), "Normalize size", value=True, callback=self.normalize_size_changed)
        self.w.scaleLabel = vanilla.TextBox((462, 66, 66, 18), "Size 92%")
        self.w.scaleSlider = vanilla.Slider((526, 62, 160, 24), minValue=0.45, maxValue=2.0, value=DEFAULT_GLYPH_SCALE, callback=self.glyph_scale_changed)
        self.reset_axis_popups()
        self.reset_fixed_popups()
        self.update_axis_slot_enabled()
        self.update_fixed_popup_enabled()
        self.update_smart_height_controls()

        self.image_records = []

        for outer_row in range(3):
            for outer_col in range(3):
                for inner_row in range(3):
                    for inner_col in range(3):
                        image_view = vanilla.ImageView((0, 0, 10, 10))
                        image_name = "image_%i_%i_%i_%i" % (outer_row, outer_col, inner_row, inner_col)
                        setattr(self.w, image_name, image_view)
                        info_button = vanilla.Button((0, 0, 16, 16), "i", callback=self.cell_info_clicked)
                        button_name = "info_%i_%i_%i_%i" % (outer_row, outer_col, inner_row, inner_col)
                        setattr(self.w, button_name, info_button)
                        self.image_records.append((image_view, info_button, outer_row, outer_col, inner_row, inner_col))

        self.w.status = vanilla.TextBox((15, -24, -15, 16), "Ready")
        try:
            self.w.bind("resize", self.window_resized)
        except Exception:
            pass
        self.layout_grid()
        self.update_images()
        self.w.open()
        self.w.makeKey()

        self.timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            REDRAW_INTERVAL,
            self,
            "timerCallback:",
            None,
            True,
        )

        print("%s Needlepoint Preview" % self.glyph_name)
        print("Script version: %s" % SCRIPT_VERSION)
        print("Redraw interval: %.2fs" % REDRAW_INTERVAL)

    def content_size(self):
        try:
            size = self.w.getNSWindow().contentView().frame().size
            return float(size.width), float(size.height)
        except Exception:
            try:
                _left, _top, width, height = self.w.getPosSize()
                return float(width), float(height)
            except Exception:
                return WINDOW_SIZE

    def layout_grid(self, model=None):
        content_width, content_height = self.content_size()
        if model is None:
            model, _missing = box_model(self.font, self.glyph, self.smart_height_values)
        if model is None:
            visible = [[0, 1, 2], [0, 1, 2], [0, 1, 2], [0, 1, 2]]
        else:
            visible = self.visible_indices(model)
        visible_sets = [set(values) for values in visible]

        control_left = 20.0
        control_gap = 8.0
        label_width = 86.0
        checkbox_width = 18.0
        fixed_width = 64.0
        fixed_slots = sum(1 for position_index in range(4) if self.fixed_popup_should_show(position_index))
        popup_width = max(72.0, min(124.0, (content_width - 2.0 * control_left - 4.0 * (label_width + checkbox_width) - fixed_slots * fixed_width - 3.0 * control_gap) / 4.0))
        x = control_left
        for position_index, (label, checkbox, popup, fixed_popup) in enumerate((
            (self.w.outerRowLabel, self.w.outerRowEnable, self.w.outerRow, self.w.outerRowFixed),
            (self.w.outerColLabel, self.w.outerColEnable, self.w.outerCol, self.w.outerColFixed),
            (self.w.innerRowLabel, self.w.innerRowEnable, self.w.innerRow, self.w.innerRowFixed),
            (self.w.innerColLabel, self.w.innerColEnable, self.w.innerCol, self.w.innerColFixed),
        )):
            label.setPosSize((int(round(x)), 38, int(label_width), 18))
            x += label_width
            checkbox.setPosSize((int(round(x)), 35, int(checkbox_width), 20))
            x += checkbox_width
            popup.setPosSize((int(round(x)), 34, int(round(popup_width)), 24))
            x += popup_width
            if self.fixed_popup_should_show(position_index):
                fixed_popup.setPosSize((int(round(x)), 34, int(fixed_width), 24))
                x += fixed_width
            else:
                fixed_popup.setPosSize((-1000, -1000, 1, 1))
            x += control_gap
        self.w.heightLabel.setPosSize((20, 66, 94, 18))
        self.w.heightLow.setPosSize((114, 62, 58, 24))
        self.w.heightMid.setPosSize((178, 62, 58, 24))
        self.w.heightHigh.setPosSize((242, 62, 58, 24))
        self.w.normalizeSize.setPosSize((320, 64, 130, 20))
        self.w.scaleLabel.setPosSize((462, 66, 66, 18))
        self.w.scaleSlider.setPosSize((526, 62, max(90, int(content_width - 548)), 24))

        grid_left = 14.0
        grid_right = 14.0
        grid_top = 104.0
        grid_bottom = 28.0
        outer_gap = max(4.0, min(9.0, content_width * 0.007))
        inner_gap = max(1.0, min(2.0, content_width * 0.002))

        available_width = max(120.0, content_width - grid_left - grid_right)
        available_height = max(120.0, content_height - grid_top - grid_bottom)
        outer_row_count = len(visible[0])
        outer_col_count = len(visible[1])
        inner_row_count = len(visible[2])
        inner_col_count = len(visible[3])
        total_cols = outer_col_count * inner_col_count
        total_rows = outer_row_count * inner_row_count
        used_inner_col_gaps = outer_col_count * max(0, inner_col_count - 1)
        used_inner_row_gaps = outer_row_count * max(0, inner_row_count - 1)
        used_outer_col_gaps = max(0, outer_col_count - 1)
        used_outer_row_gaps = max(0, outer_row_count - 1)
        image_size = max(12.0, min(
            (available_width - used_inner_col_gaps * inner_gap - used_outer_col_gaps * outer_gap) / total_cols,
            (available_height - used_inner_row_gaps * inner_gap - used_outer_row_gaps * outer_gap) / total_rows,
        ))

        used_width = (
            image_size * total_cols
            + inner_gap * used_inner_col_gaps
            + outer_gap * used_outer_col_gaps
        )
        grid_origin_x = grid_left + max(0.0, (available_width - used_width) / 2.0)
        outer_row_positions = {value: index for index, value in enumerate(visible[0])}
        outer_col_positions = {value: index for index, value in enumerate(visible[1])}
        inner_row_positions = {value: index for index, value in enumerate(visible[2])}
        inner_col_positions = {value: index for index, value in enumerate(visible[3])}

        self.image_width = int(round(image_size))
        self.image_height = int(round(image_size))

        for image_view, info_button, outer_row, outer_col, inner_row, inner_col in self.image_records:
            is_visible = (
                outer_row in visible_sets[0]
                and outer_col in visible_sets[1]
                and inner_row in visible_sets[2]
                and inner_col in visible_sets[3]
            )
            try:
                image_view.show(is_visible)
                info_button.show(is_visible)
            except Exception:
                try:
                    image_view.getNSImageView().setHidden_(not is_visible)
                    info_button.getNSButton().setHidden_(not is_visible)
                except Exception:
                    pass
            if not is_visible:
                try:
                    image_view.setPosSize((-1000, -1000, 1, 1))
                    info_button.setPosSize((-1000, -1000, 1, 1))
                except Exception:
                    pass
                continue

            outer_col_index = outer_col_positions[outer_col]
            outer_row_index = outer_row_positions[outer_row]
            inner_col_index = inner_col_positions[inner_col]
            inner_row_index = inner_row_positions[inner_row]
            flat_col = outer_col_index * inner_col_count + inner_col_index
            flat_row = outer_row_index * inner_row_count + inner_row_index
            x = (
                grid_origin_x
                + flat_col * image_size
                + (outer_col_index * max(0, inner_col_count - 1) + inner_col_index) * inner_gap
                + outer_col_index * outer_gap
            )
            y = (
                grid_top
                + flat_row * image_size
                + (outer_row_index * max(0, inner_row_count - 1) + inner_row_index) * inner_gap
                + outer_row_index * outer_gap
            )
            try:
                image_view.setPosSize((
                    int(round(x)),
                    int(round(y)),
                    self.image_width,
                    self.image_height,
                ))
                button_size = max(14, min(18, int(round(self.image_width * 0.22))))
                info_button.setPosSize((
                    int(round(x + self.image_width - button_size - 2)),
                    int(round(y + 2)),
                    button_size,
                    button_size,
                ))
            except Exception:
                pass

    def window_resized(self, sender):
        self.layout_grid()
        self.request_redraw()

    def reset_axis_popups(self):
        for popup, index in (
            (self.w.outerRow, self.axis_order[0]),
            (self.w.outerCol, self.axis_order[1]),
            (self.w.innerRow, self.axis_order[2]),
            (self.w.innerCol, self.axis_order[3]),
        ):
            try:
                if index >= 0:
                    popup.set(index)
            except Exception:
                pass

    def axis_popups(self):
        return [self.w.outerRow, self.w.outerCol, self.w.innerRow, self.w.innerCol]

    def update_axis_slot_enabled(self):
        for position_index, (popup, checkbox, axis_index) in enumerate(zip(self.axis_popups(), self.axis_enable_widgets(), self.axis_order)):
            slot_is_active = 0 <= axis_index < len(self.dimension_labels)
            try:
                popup.enable(slot_is_active)
            except Exception:
                try:
                    popup.getNSPopUpButton().setEnabled_(slot_is_active)
                except Exception:
                    pass
            try:
                checkbox.enable(slot_is_active)
                checkbox.set(bool(slot_is_active and self.axis_enabled[position_index]))
            except Exception:
                try:
                    checkbox.getNSButton().setEnabled_(slot_is_active)
                except Exception:
                    pass

    def update_smart_height_controls(self):
        for control in (self.w.heightLabel, self.w.heightLow, self.w.heightMid, self.w.heightHigh):
            try:
                control.show(self.has_smart_height_axis)
            except Exception:
                pass
            try:
                control.enable(self.has_smart_height_axis)
            except Exception:
                try:
                    control.getNSControl().setEnabled_(self.has_smart_height_axis)
                except Exception:
                    pass

    def fixed_popups(self):
        return [self.w.outerRowFixed, self.w.outerColFixed, self.w.innerRowFixed, self.w.innerColFixed]

    def reset_fixed_popups(self):
        for popup, index in zip(self.fixed_popups(), self.axis_fixed_indices):
            try:
                popup.set(index)
            except Exception:
                pass

    def fixed_popup_should_show(self, position_index):
        if position_index < 0 or position_index >= len(self.axis_order):
            return False
        axis_index = self.axis_order[position_index]
        return 0 <= axis_index < len(self.dimension_labels) and not self.axis_enabled[position_index]

    def update_fixed_popup_enabled(self):
        for position_index, popup in enumerate(self.fixed_popups()):
            should_show = self.fixed_popup_should_show(position_index)
            try:
                popup.show(should_show)
            except Exception:
                try:
                    popup.getNSPopUpButton().setHidden_(not should_show)
                except Exception:
                    pass
            try:
                popup.enable(should_show)
            except Exception:
                try:
                    popup.getNSPopUpButton().setEnabled_(should_show)
                except Exception:
                    pass

    def axis_enable_widgets(self):
        return [self.w.outerRowEnable, self.w.outerColEnable, self.w.innerRowEnable, self.w.innerColEnable]

    def axis_enabled_changed(self, sender):
        widgets = self.axis_enable_widgets()
        self.axis_enabled = [
            bool(widget.get()) and 0 <= axis_index < len(self.dimension_labels)
            for widget, axis_index in zip(widgets, self.axis_order)
        ]
        self.update_fixed_popup_enabled()
        self.layout_grid()
        self.request_redraw()

    def axis_fixed_changed(self, sender):
        values = []
        for popup, fallback in zip(self.fixed_popups(), self.axis_fixed_indices):
            try:
                values.append(int(popup.get()))
            except Exception:
                values.append(int(fallback))
        self.axis_fixed_indices = values
        self.request_redraw()

    def height_values_changed(self, sender):
        fields = [self.w.heightLow, self.w.heightMid, self.w.heightHigh]
        values = []
        for field, fallback in zip(fields, self.smart_height_values):
            try:
                values.append(float(field.get()))
            except Exception:
                values.append(float(fallback))
        self.smart_height_values = values
        self.request_redraw()

    def normalize_size_changed(self, sender):
        self.normalize_size = bool(sender.get())
        self.request_redraw()

    def glyph_scale_changed(self, sender):
        try:
            self.glyph_scale = float(sender.get())
        except Exception:
            self.glyph_scale = DEFAULT_GLYPH_SCALE
        try:
            self.w.scaleLabel.set("Size %i%%" % int(round(self.glyph_scale * 100)))
        except Exception:
            pass
        self.request_redraw()

    def request_redraw(self):
        self.needs_redraw = True

    def visible_indices(self, model):
        indices = []
        for position_index, enabled in enumerate(self.axis_enabled):
            if enabled:
                indices.append([0, 1, 2])
            else:
                indices.append([self.axis_fixed_indices[position_index]])
        return indices

    def axis_order_changed(self, sender):
        popups = [self.w.outerRow, self.w.outerCol, self.w.innerRow, self.w.innerCol]
        try:
            changed_index = popups.index(sender)
        except ValueError:
            self.reset_axis_popups()
            return

        selected_axis = sender.get()
        if selected_axis == self.axis_order[changed_index]:
            return

        try:
            previous_index = self.axis_order.index(selected_axis)
        except ValueError:
            self.reset_axis_popups()
            return

        new_order = list(self.axis_order)
        new_order[previous_index] = self.axis_order[changed_index]
        new_order[changed_index] = selected_axis
        self.axis_order = new_order
        self.reset_axis_popups()
        self.update_axis_slot_enabled()
        self.update_fixed_popup_enabled()
        self.layout_grid()
        self.request_redraw()

    def set_status(self, text):
        try:
            self.w.status.set(text)
        except Exception:
            pass

    def close_info_window(self, sender):
        if self.info_window is not None:
            try:
                self.info_window.close()
            except Exception:
                pass
            self.info_window = None

    def show_cell_info(self, text):
        self.close_info_window(None)
        lines = text.split("\n")
        title = lines[0] if lines else "Cell"
        details = "\n".join(lines[1:]) if len(lines) > 1 else ""
        self.info_window = vanilla.FloatingWindow((360, 170), "Cell coordinates")
        self.info_window.title = vanilla.TextBox((14, 12, -14, 20), title)
        self.info_window.details = vanilla.TextBox((14, 40, -14, 86), details)
        self.info_window.closeButton = vanilla.Button((-84, -34, 70, 24), "Close", callback=self.close_info_window)
        self.info_window.open()
        self.info_window.makeKey()

    def cell_info_clicked(self, sender):
        model, _missing = box_model(self.font, self.glyph, self.smart_height_values)
        if model is None:
            return

        for _image_view, info_button, outer_row, outer_col, inner_row, inner_col in self.image_records:
            if info_button is not sender:
                continue
            self.show_cell_info(cell_coordinate_text(
                model,
                self.axis_order,
                self.axis_enabled,
                self.axis_fixed_indices,
                outer_row,
                outer_col,
                inner_row,
                inner_col,
            ))
            return

    def update_images(self):
        if self.is_updating:
            return
        self.is_updating = True
        try:
            self.update_images_inner()
        finally:
            self.is_updating = False

    def update_images_inner(self):
        glyph = self.glyph
        if glyph is None:
            self.set_status("Missing glyph.")
            return

        model, missing = box_model(self.font, glyph, self.smart_height_values)
        if model is None:
            self.set_status("Missing: %s" % ", ".join(missing))
            return
        self.layout_grid(model)

        visible = self.visible_indices(model)
        visible_sets = [set(values) for values in visible]
        image_cache = {}
        for image_view, _info_button, outer_row, outer_col, inner_row, inner_col in self.image_records:
            if not (
                outer_row in visible_sets[0]
                and outer_col in visible_sets[1]
                and inner_row in visible_sets[2]
                and inner_col in visible_sets[3]
            ):
                continue

            coordinates, smart_values = sample_for_grid_position(
                model,
                self.axis_order,
                self.axis_enabled,
                self.axis_fixed_indices,
                outer_row,
                outer_col,
                inner_row,
                inner_col,
            )
            cache_key = (
                self.image_width,
                self.image_height,
                self.normalize_size,
                round(float(self.glyph_scale), 4),
                tuple(self.axis_fixed_indices),
                tuple(sorted((str(key), round(float(value), 6)) for key, value in coordinates.items())),
                tuple(sorted((str(key), round(float(value), 6)) for key, value in smart_values.items())),
            )
            cached = image_cache.get(cache_key)
            if cached is None:
                cached = image_for_coordinates(
                    glyph,
                    model,
                    coordinates,
                    smart_values,
                    self.image_width,
                    self.image_height,
                    self.normalize_size,
                    self.glyph_scale,
                )
                image_cache[cache_key] = cached
            image, image_missing = cached
            missing.extend(image_missing)
            image_view.getNSImageView().setImage_(image)

        if missing:
            self.set_status("Missing: %s" % ", ".join(missing))
        else:
            self.set_status("Live (%i render%s)" % (len(image_cache), "" if len(image_cache) == 1 else "s"))
        self.needs_redraw = False

    def timerCallback_(self, timer):
        try:
            visible = bool(self.w.getNSWindow().isVisible())
        except Exception:
            visible = False
        if not visible:
            try:
                timer.invalidate()
            except Exception:
                pass
            return
        self.update_images()


try:
    _dblIntegralNeedlepointPreview.timer.invalidate()
except Exception:
    pass

_dblIntegralNeedlepointPreview = DblIntegralNeedlepointPreview()
