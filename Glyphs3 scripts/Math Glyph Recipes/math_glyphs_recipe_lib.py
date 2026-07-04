# -*- coding: utf-8 -*-

"""Shared helpers for plist-driven Glyphs recipe scripts."""

import os
import plistlib
import re
import uuid

from GlyphsApp import (
    Glyphs,
    GSGlyph,
    GSComponent,
    GSGlyphReference,
    GSSmartComponentAxis,
)


SCRIPT_VERSION = "2026-07-03 14:48 CDT pair-anchor-master-source"
DEFAULT_RECIPE_FILE = "triple_integral_recipe.plist"
VERBOSE = True
VARIABLE_PATTERN = re.compile(r"\$\{([^}]+)\}")
WHOLE_VARIABLE_PATTERN = re.compile(r"^\$\{([^}]+)\}$")
SMART_MASTER_SELECTION_VALUE = 1
SMART_HIGH_SELECTION_VALUE = 2
MATH_PLUGIN_VARIANTS_USER_DATA_KEY = "com.nagwa.MATHPlugin.variants"
MATH_PLUGIN_CONSTANTS_PARAMETER = "com.nagwa.MATHPlugin.constants"
MATH_PLUGIN_VARIANT_KEYS = dict(
    height="vVariants",
    width="hVariants",
)
GLYPHS_COLOR_INDEXES = dict(
    red=0,
    orange=1,
    brown=2,
    yellow=3,
    lightgreen=4,
    darkgreen=5,
    lightblue=6,
    darkblue=7,
    purple=8,
    magenta=9,
    lightgray=10,
    darkgray=11,
    none=None,
)


class RecipeStopped(Exception):
    pass


def script_directory():
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except Exception:
        return os.getcwd()


def recipe_path(file_name):
    if os.path.isabs(file_name):
        return file_name
    return os.path.join(script_directory(), file_name)


def log(message, verbose=True):
    if verbose:
        print(message)


def print_warning(message):
    print("WARNING: %s" % message)


def safe_call(value, default=None):
    if callable(value):
        try:
            return value()
        except Exception:
            return default
    return value


def clean_number(value):
    value = float(value)
    if value.is_integer():
        return int(value)
    return value


def format_xy(xy):
    if xy is None:
        return "none"
    return "(%.3f, %.3f)" % (xy[0], xy[1])


def numeric_value(value):
    try:
        return float(value)
    except Exception:
        return None


def number_list(values):
    if values is None:
        return None
    if isinstance(values, str):
        values = [item.strip() for item in values.split(",")]
    result = []
    for value in values:
        number = numeric_value(value)
        if number is None:
            continue
        result.append(clean_number(number))
    return result


def unique_strings(values):
    seen = set()
    result = []
    for value in values or []:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def color_value(value):
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip().lower().replace(" ", "").replace("_", "").replace("-", "")
        if not cleaned:
            return None
        if cleaned in GLYPHS_COLOR_INDEXES:
            return GLYPHS_COLOR_INDEXES[cleaned]
    try:
        return int(value)
    except Exception:
        return value


def boolean_value(value):
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


def set_glyph_color(glyph, color=None):
    color = color_value(color)
    if color is None:
        return False
    try:
        glyph.color = color
        return True
    except Exception:
        pass
    method = getattr(glyph, "setColor_", None)
    if method is not None:
        try:
            method(color)
            return True
        except Exception:
            pass
    return False


def layer_name(layer):
    return str(safe_call(getattr(layer, "name", ""), "") or "")


def layer_id(layer):
    value = safe_call(getattr(layer, "layerId", None))
    return str(value) if value is not None else None


def layer_width(layer):
    value = safe_call(getattr(layer, "width", None))
    try:
        return float(value)
    except Exception:
        return None


def is_master_layer(layer):
    return bool(safe_call(getattr(layer, "isMasterLayer", False), False))


def associated_master_id(layer):
    value = safe_call(getattr(layer, "associatedMasterId", None))
    return str(value) if value is not None else None


def master_for_layer(font, layer):
    layer_id_value = layer_id(layer)
    if layer_id_value:
        try:
            master = font.masters[layer_id_value]
            if master is not None:
                return master
        except Exception:
            pass

    associated_master_id_value = associated_master_id(layer)
    if associated_master_id_value:
        try:
            master = font.masters[associated_master_id_value]
            if master is not None:
                return master
        except Exception:
            pass

    return safe_call(getattr(font, "selectedFontMaster", None))


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
        name = safe_call(getattr(parameter, "name", None))
        if name == parameter_name:
            return safe_call(getattr(parameter, "value", None))
    return None


def user_data_value(owner, key):
    user_data = getattr(owner, "userData", None)
    if not user_data:
        return None

    try:
        value = user_data[key]
        if value is not None:
            return value
    except Exception:
        pass

    for method_name in ("objectForKey_", "valueForKey_"):
        method = getattr(user_data, method_name, None)
        if method is None:
            continue
        try:
            value = method(key)
        except Exception:
            continue
        if value is not None:
            return value
    return None


def math_constant_value(font, master, constant_name):
    for owner in (master, font):
        if owner is None:
            continue
        for constants in (
            custom_parameter_value(owner, MATH_PLUGIN_CONSTANTS_PARAMETER),
            user_data_value(owner, MATH_PLUGIN_CONSTANTS_PARAMETER),
        ):
            try:
                if constants and constant_name in constants:
                    return constants[constant_name]
            except Exception:
                pass

            for method_name in ("objectForKey_", "valueForKey_"):
                method = getattr(constants, method_name, None)
                if method is None:
                    continue
                try:
                    value = method(constant_name)
                except Exception:
                    continue
                if value is not None:
                    return value
    return None


def metric_value(master, attribute_name, fallback=0):
    value = safe_call(getattr(master, attribute_name, None)) if master is not None else None
    if value is None:
        return fallback
    return value


def math_axis_for_layer(font, layer):
    master = master_for_layer(font, layer)
    axis_height = math_constant_value(font, master, "AxisHeight")
    if axis_height is None:
        axis_height = metric_value(master, "xHeight", 0)
    try:
        return float(axis_height)
    except Exception:
        return 0.0


def glyph_for_name(font, glyph_name):
    try:
        return font.glyphs[glyph_name]
    except Exception:
        return None


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


def clear_proxy(proxy):
    if proxy is None:
        return False
    try:
        proxy.clear()
        return True
    except Exception:
        pass
    changed = False
    while True:
        try:
            if not len(proxy):
                return changed
        except Exception:
            return changed
        try:
            proxy.remove(proxy[-1])
            changed = True
            continue
        except Exception:
            pass
        try:
            del proxy[-1]
            changed = True
            continue
        except Exception:
            return changed


def proxy_has_items(proxy):
    if proxy is None:
        return False
    try:
        return len(proxy) > 0
    except Exception:
        pass
    try:
        for _item in proxy:
            return True
    except Exception:
        pass
    return False


def layer_has_paths_components_or_anchors(layer):
    for proxy_name in ("paths", "components", "anchors"):
        if proxy_has_items(getattr(layer, proxy_name, None)):
            return True

    for shape in safe_call(getattr(layer, "shapes", None), []) or []:
        try:
            if shape.__class__.__name__ in ("GSPath", "GSComponent"):
                return True
        except Exception:
            return True
    return False


def glyph_is_empty(glyph):
    if glyph is None:
        return True
    for layer in glyph.layers:
        if layer_has_paths_components_or_anchors(layer):
            return False
    return True


def clear_glyph(glyph):
    for layer in reversed(list(glyph.layers)):
        if is_master_layer(layer):
            continue
        remove_layer(glyph, layer)

    for layer in glyph.layers:
        for proxy_name in ("shapes", "components", "paths", "anchors", "hints"):
            clear_proxy(getattr(layer, proxy_name, None))

    for attribute_name in ("smartComponentAxes", "stems"):
        try:
            setattr(glyph, attribute_name, [])
        except Exception:
            pass

    try:
        if MATH_PLUGIN_VARIANTS_USER_DATA_KEY in glyph.userData:
            del glyph.userData[MATH_PLUGIN_VARIANTS_USER_DATA_KEY]
    except Exception:
        pass


def make_component(component_name):
    for value in (component_name,):
        try:
            return GSComponent(value)
        except Exception:
            pass
    component = GSComponent()
    try:
        component.componentName = component_name
    except Exception:
        try:
            component.name = component_name
        except Exception:
            pass
    return component


def layer_components(layer):
    try:
        return list(layer.components)
    except Exception:
        return []


def matching_layer(source_glyph, target_layer):
    target_layer_id = layer_id(target_layer)
    if target_layer_id is not None:
        try:
            source_layer = source_glyph.layers[target_layer_id]
            if source_layer is not None:
                return source_layer
        except Exception:
            pass

    target_name = layer_name(target_layer)
    target_master_id = associated_master_id(target_layer)
    for source_layer in source_glyph.layers:
        if layer_name(source_layer) != target_name:
            continue
        if associated_master_id(source_layer) == target_master_id:
            return source_layer
    for source_layer in source_glyph.layers:
        if layer_name(source_layer) == target_name:
            return source_layer
    return None


def set_layer_metric(layer, attribute_name, value):
    if value is None:
        return False
    try:
        setattr(layer, attribute_name, value)
        return True
    except Exception:
        pass
    method = getattr(layer, "set%s_" % attribute_name, None)
    if method is not None:
        try:
            method(value)
            return True
        except Exception:
            pass
    return False


def set_layer_metrics_key(layer, attribute_name, key_value):
    try:
        setattr(layer, attribute_name, key_value)
        return True
    except Exception:
        pass
    method = getattr(layer, "set%s_" % attribute_name, None)
    if method is not None:
        try:
            method(key_value)
            return True
        except Exception:
            pass
    return False


def copy_layer_metrics(source_layer, target_layer, source_glyph_name=None):
    changed = 0
    width = layer_width(source_layer)
    if width is not None and set_layer_metric(target_layer, "width", width):
        changed += 1

    if source_glyph_name:
        key_value = "=%s" % source_glyph_name
        for attribute_name in ("leftMetricsKey", "rightMetricsKey"):
            if set_layer_metrics_key(target_layer, attribute_name, key_value):
                changed += 1
    else:
        for attribute_name in ("leftMetricsKey", "rightMetricsKey", "widthMetricsKey"):
            try:
                setattr(target_layer, attribute_name, getattr(source_layer, attribute_name))
            except Exception:
                pass

    width_key = safe_call(getattr(source_layer, "widthMetricsKey", None))
    if width_key and set_layer_metrics_key(target_layer, "widthMetricsKey", width_key):
        changed += 1

    return changed


def append_component_to_layer(layer, component_name):
    component = make_component(component_name)
    try:
        layer.components.append(component)
        return True
    except Exception:
        pass
    try:
        components = list(layer.components or [])
        components.append(component)
        layer.components = components
        return True
    except Exception:
        return False


def component_name(component):
    for attribute_name in ("componentName", "name"):
        value = safe_call(getattr(component, attribute_name, None))
        if value:
            return str(value)

    for attribute_name in ("component", "glyph"):
        glyph = safe_call(getattr(component, attribute_name, None))
        if glyph is not None:
            value = safe_call(getattr(glyph, "name", None))
            if value:
                return str(value)
    return None


def transform_values(component):
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
            if len(values) >= 6:
                return tuple(float(value) for value in values[:6])
        except Exception:
            pass
    return (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def disable_component_alignment(component):
    method = getattr(component, "setDisableAlignment_", None)
    if method is not None:
        try:
            method(True)
            return True
        except Exception:
            pass

    try:
        component.automaticAlignment = False
        return True
    except Exception:
        pass

    try:
        component.disableAlignment = True
        return True
    except Exception:
        pass

    try:
        component.alignment = -1
        return True
    except Exception:
        return False


def set_component_transform(component, values):
    for method_name in ("setTransform_",):
        method = getattr(component, method_name, None)
        if method is None:
            continue
        try:
            method(values)
            return True
        except Exception:
            pass
    try:
        component.transform = values
        return True
    except Exception:
        return False


def set_component_scale(component, x_scale, y_scale):
    x_scale = clean_number(x_scale)
    y_scale = clean_number(y_scale)
    setter = getattr(component, "setScale_", None)
    for value in ((x_scale, y_scale),):
        if setter is not None:
            try:
                setter(value)
                return True
            except Exception:
                pass
        try:
            component.scale = value
            return True
        except Exception:
            pass

    a, b, c, d, tx, ty = transform_values(component)
    return set_component_transform(component, (float(x_scale), b, c, float(y_scale), tx, ty))


def bounds_y_values(obj):
    bounds = safe_call(getattr(obj, "bounds", None))
    if bounds is None:
        return None, None, None
    try:
        min_y = float(bounds.origin.y)
        height = float(bounds.size.height)
        return min_y, min_y + height, min_y + (height / 2.0)
    except Exception:
        pass
    try:
        origin = bounds[0]
        size = bounds[1]
        min_y = float(origin[1])
        height = float(size[1])
        return min_y, min_y + height, min_y + (height / 2.0)
    except Exception:
        return None, None, None


def translate_component_y(component, dy):
    if abs(float(dy)) <= 0.000001:
        return True
    a, b, c, d, tx, ty = transform_values(component)
    if set_component_transform(component, (a, b, c, d, tx, ty + float(dy))):
        return True

    position = safe_call(getattr(component, "position", None))
    if position is not None:
        try:
            position.y = float(position.y) + float(dy)
            component.position = position
            return True
        except Exception:
            pass
    return False


def flip_component_across_horizontal_center(component):
    old_min_y, old_max_y, center_y = bounds_y_values(component)
    if center_y is None:
        return False
    a, b, c, d, tx, ty = transform_values(component)
    if not set_component_transform(component, (a, -b, c, -d, tx, (2.0 * center_y) - ty)):
        return False

    new_min_y, new_max_y, new_center_y = bounds_y_values(component)
    if old_min_y is None or new_min_y is None:
        return True
    return translate_component_y(component, old_min_y - new_min_y)


def component_glyph(font, component):
    for attribute_name in ("component", "glyph"):
        glyph = safe_call(getattr(component, attribute_name, None))
        if glyph is not None and safe_call(getattr(glyph, "name", None)):
            return glyph

    name = component_name(component)
    if name is None:
        return None
    return glyph_for_name(font, name)


def point_xy(point):
    if point is None:
        return None
    x_value = safe_call(getattr(point, "x", None))
    y_value = safe_call(getattr(point, "y", None))
    if x_value is None or y_value is None:
        try:
            values = list(point)
            x_value = values[0]
            y_value = values[1]
        except Exception:
            return None
    try:
        return float(x_value), float(y_value)
    except Exception:
        return None


def anchor_xy(anchor):
    if anchor is None:
        return None
    position = safe_call(getattr(anchor, "position", None))
    xy = point_xy(position)
    if xy is not None:
        return xy
    return point_xy(anchor)


def anchor_name(anchor):
    value = safe_call(getattr(anchor, "name", None))
    return str(value) if value is not None else None


def layer_anchor(layer, names):
    anchors = safe_call(getattr(layer, "anchors", None))
    if anchors is None:
        return None

    for name in names:
        try:
            anchor = anchors[name]
            if anchor is not None:
                return anchor
        except Exception:
            pass

    try:
        anchor_list = list(anchors)
    except Exception:
        return None
    wanted = set(names)
    for anchor in anchor_list:
        if anchor_name(anchor) in wanted:
            return anchor
    return None


def layer_anchor_list(layer):
    anchors = safe_call(getattr(layer, "anchors", None))
    if anchors is None:
        return []
    try:
        return list(anchors)
    except Exception:
        return []


def transformed_anchor_records(component, records):
    result = []
    for name, xy in records:
        result.append((name, transformed_point(component, xy)))
    return result


def effective_layer_anchor_records(font, layer, reference_layer=None, visited=None):
    if visited is None:
        visited = set()

    parent = safe_call(getattr(layer, "parent", None))
    parent_name = safe_call(getattr(parent, "name", None)) if parent is not None else None
    current_key = (str(parent_name or ""), str(layer_id(layer) or id(layer)))
    if current_key in visited:
        return []
    visited.add(current_key)

    records = []
    for anchor in layer_anchor_list(layer):
        name = anchor_name(anchor)
        xy = anchor_xy(anchor)
        if name and xy is not None:
            records.append((name, xy))

    for component in layer_components(layer):
        glyph = component_glyph(font, component)
        if glyph is None:
            continue
        component_layer = matching_layer(glyph, reference_layer or layer)
        if component_layer is None:
            continue
        component_records = effective_layer_anchor_records(
            font,
            component_layer,
            reference_layer or layer,
            set(visited),
        )
        records.extend(transformed_anchor_records(component, component_records))
    return records


def effective_layer_anchor_xy(font, layer, names):
    wanted = set(names or [])
    for name, xy in effective_layer_anchor_records(font, layer):
        if name in wanted:
            return xy
    return None


def first_matching_anchor_pair(font, previous_layer, next_layer, preferred_names=None):
    if isinstance(preferred_names, str):
        preferred_names = [preferred_names]

    previous_records = dict(effective_layer_anchor_records(font, previous_layer))
    next_records = dict(effective_layer_anchor_records(font, next_layer))
    for name in preferred_names or []:
        if not name:
            continue
        previous_xy = previous_records.get(name)
        next_xy = next_records.get("_%s" % name)
        if previous_xy is not None and next_xy is not None:
            return previous_xy, next_xy

    for name, previous_xy in previous_records.items():
        if not name or name.startswith("_"):
            continue
        next_xy = next_records.get("_%s" % name)
        if next_xy is not None:
            return previous_xy, next_xy
    return None, None


def component_source_layer(font, component, target_layer):
    glyph = component_glyph(font, component)
    if glyph is None:
        return None
    source_layer = matching_layer(glyph, target_layer)
    if source_layer is not None:
        return source_layer
    try:
        return glyph.layers[0]
    except Exception:
        return None


def component_source_master_layer(font, component, target_layer):
    glyph = component_glyph(font, component)
    if glyph is None:
        return None
    master_id = associated_master_id(target_layer) or layer_id(target_layer)
    if master_id:
        try:
            source_layer = glyph.layers[master_id]
            if source_layer is not None:
                return source_layer
        except Exception:
            pass
    return component_source_layer(font, component, target_layer)


def transformed_point(component, xy):
    x_value, y_value = xy
    a, b, c, d, tx, ty = transform_values(component)
    return (
        (a * x_value) + (c * y_value) + tx,
        (b * x_value) + (d * y_value) + ty,
    )


def move_component_local_point_to(component, local_xy, target_xy):
    current_x, current_y = transformed_point(component, local_xy)
    target_x, target_y = target_xy
    dx = target_x - current_x
    dy = target_y - current_y
    a, b, c, d, tx, ty = transform_values(component)
    return set_component_transform(component, (a, b, c, d, tx + dx, ty + dy))


def move_component_by(component, dx=0, dy=0):
    a, b, c, d, tx, ty = transform_values(component)
    return set_component_transform(component, (a, b, c, d, tx + dx, ty + dy))


def ordered_components_for_sequence(layer, names=None):
    components = layer_components(layer)
    if isinstance(names, str):
        names = [names]
    if not names:
        return components

    result = []
    start_index = 0
    for expected_name in names:
        for index in range(start_index, len(components)):
            component = components[index]
            if component_name(component) != expected_name:
                continue
            result.append(component)
            start_index = index + 1
            break
    return result


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


def set_associated_master_id(layer, master_id):
    method = getattr(layer, "setAssociatedMasterId_", None)
    if method is not None:
        try:
            method(master_id)
            return
        except Exception:
            pass
    try:
        layer.associatedMasterId = master_id
    except Exception:
        pass


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


def axis_identifier(axis):
    for attribute_name in ("id", "axisId"):
        value = safe_call(getattr(axis, attribute_name, None))
        if value:
            return str(value)
    return None


def smart_axis_name(axis):
    return str(safe_call(getattr(axis, "name", None), "") or "")


def glyph_smart_axes(glyph):
    try:
        return list(glyph.smartComponentAxes or [])
    except Exception:
        return []


def smart_axis_for_name(glyph, wanted_name):
    for axis in glyph_smart_axes(glyph):
        if smart_axis_name(axis) == wanted_name:
            return axis
    return None


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


def ensure_smart_axis(glyph, axis_name_value, bottom_value=0, top_value=100):
    axis = smart_axis_for_name(glyph, axis_name_value)
    created = False
    if axis is None:
        axis = GSSmartComponentAxis()
        if not append_smart_axis(glyph, axis):
            raise RuntimeError("%s: could not add smart axis %s." % (glyph.name, axis_name_value))
        created = True
    set_object_attribute(axis, "name", axis_name_value)
    set_object_attribute(axis, "bottomValue", bottom_value)
    set_object_attribute(axis, "topValue", top_value)
    return axis, created


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


def set_height_layer_properties(layer, axis_name_value, axis, selection_value):
    try:
        part_selection = dict(layer_attribute(layer, "partSelection") or {})
    except Exception:
        part_selection = {}
    part_selection[axis_name_value] = selection_value

    changed = False
    if set_layer_attribute(layer, "partSelection", part_selection):
        changed = True
    if set_smart_component_pole_mapping(layer, axis, selection_value):
        changed = True
    return changed


def high_layer_name(master):
    return "%s High" % master.name


def remove_existing_high_layers(glyph, master):
    removed = 0
    expected_name = high_layer_name(master)
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


def layer_index(glyph, target_layer):
    for index, layer in enumerate(glyph.layers):
        if layer is target_layer:
            return index
    return len(glyph.layers) - 1


def set_component_smart_value(component, axis_id_value, value):
    if not hasattr(component, "smartComponentValues"):
        return False
    value = clean_number(value)
    try:
        component.smartComponentValues[axis_id_value] = value
        return True
    except Exception:
        pass
    try:
        values = dict(component.smartComponentValues or {})
        values[axis_id_value] = value
        component.smartComponentValues = values
        return True
    except Exception:
        return False


def smart_axis_id_for_component(font, component, axis_name_value):
    glyph = component_glyph(font, component)
    if glyph is None:
        return None
    axis = smart_axis_for_name(glyph, axis_name_value)
    return axis_identifier(axis) if axis is not None else None


def component_axis_value(font, component, axis_name_value):
    glyph = component_glyph(font, component)
    axis = smart_axis_for_name(glyph, axis_name_value) if glyph is not None else None
    axis_id = axis_identifier(axis) if axis is not None else None
    if axis_id is None:
        return None
    try:
        values = dict(component.smartComponentValues or {})
    except Exception:
        values = {}
    for key in (axis_id, axis_name_value):
        if key in values:
            value = numeric_value(values[key])
            if value is not None:
                return value
    for attribute_name in ("bottomValue", "topValue"):
        value = numeric_value(safe_call(getattr(axis, attribute_name, None)))
        if value is not None:
            return value
    return None


def variant_name(source_name, number):
    return "%s.s%02i" % (source_name, number)


def variant_names(source_name, variant_count, start_number=1):
    return [source_name] + [
        variant_name(source_name, number)
        for number in range(int(start_number), int(start_number) + int(variant_count))
    ]


def glyph_reference_for_name(font, glyph_name):
    glyph = glyph_for_name(font, glyph_name)
    if glyph is None:
        return None
    try:
        return GSGlyphReference(glyph)
    except Exception:
        return None


def store_math_plugin_variants_on_glyph(font, glyph, variant_count, axis_name_value, start_number=1):
    variant_key = MATH_PLUGIN_VARIANT_KEYS.get(axis_name_value)
    if variant_key is None:
        return False
    references = []
    for name in variant_names(glyph.name, variant_count, start_number):
        reference = glyph_reference_for_name(font, name)
        if reference is None:
            return False
        references.append(reference)
    try:
        math_plugin_variants = dict(glyph.userData[MATH_PLUGIN_VARIANTS_USER_DATA_KEY] or {})
    except Exception:
        math_plugin_variants = {}
    math_plugin_variants[variant_key] = references
    try:
        glyph.userData[MATH_PLUGIN_VARIANTS_USER_DATA_KEY] = math_plugin_variants
        return True
    except Exception:
        return False


def copy_glyph_metadata(source_glyph, target_glyph):
    for attribute_name in ("category", "subCategory", "script", "leftMetricsKey", "rightMetricsKey", "widthMetricsKey"):
        try:
            setattr(target_glyph, attribute_name, getattr(source_glyph, attribute_name))
        except Exception:
            pass
    try:
        target_glyph.export = source_glyph.export
    except Exception:
        pass


def remove_non_master_layers(glyph):
    removed = 0
    for layer in list(glyph.layers):
        if is_master_layer(layer):
            continue
        if remove_layer(glyph, layer):
            removed += 1
    return removed


def copied_layer(source_layer):
    layer = source_layer.copy()
    if not layer_id(layer):
        layer.layerId = str(uuid.uuid4()).upper()
    return layer


def set_layer_component_axis_increment(font, layer, axis_name_value, increment):
    changed = 0
    skipped = 0
    for component in layer_components(layer):
        axis_id = smart_axis_id_for_component(font, component, axis_name_value)
        base_value = component_axis_value(font, component, axis_name_value)
        if axis_id is None or base_value is None:
            skipped += 1
            continue
        if set_component_smart_value(component, axis_id, base_value + increment):
            changed += 1
        else:
            skipped += 1
    return changed, skipped


def populate_variant_from_source(font, source_glyph, target_glyph, axis_name_value, increment):
    remove_non_master_layers(target_glyph)
    copied_master_layers = 0
    copied_special_layers = 0
    smart_components_set = 0
    smart_components_skipped = 0
    for source_layer in source_glyph.layers:
        if is_master_layer(source_layer):
            source_layer_id = layer_id(source_layer)
            new_layer = copied_layer(source_layer)
            new_layer.layerId = source_layer_id
            set_associated_master_id(new_layer, source_layer_id)
            changed, skipped = set_layer_component_axis_increment(font, new_layer, axis_name_value, increment)
            smart_components_set += changed
            smart_components_skipped += skipped
            target_glyph.layers[source_layer_id] = new_layer
            copied_master_layers += 1
            continue
        new_layer = copied_layer(source_layer)
        changed, skipped = set_layer_component_axis_increment(font, new_layer, axis_name_value, increment)
        smart_components_set += changed
        smart_components_skipped += skipped
        target_glyph.layers.append(new_layer)
        copied_special_layers += 1
    copy_glyph_metadata(source_glyph, target_glyph)
    return copied_master_layers, copied_special_layers, smart_components_set, smart_components_skipped


def load_plist(file_name):
    path = recipe_path(file_name)
    with open(path, "rb") as handle:
        return plistlib.load(handle), path


def merge_parameters(defaults, overrides):
    parameters = dict(defaults or {})
    parameters.update(dict(overrides or {}))
    return parameters


def expand_value(value, parameters):
    if isinstance(value, dict):
        return {key: expand_value(item, parameters) for key, item in value.items()}
    if isinstance(value, list):
        return [expand_value(item, parameters) for item in value]
    if not isinstance(value, str):
        return value

    whole_match = WHOLE_VARIABLE_PATTERN.match(value)
    if whole_match:
        key = whole_match.group(1)
        return parameters.get(key, value)

    def replace(match):
        key = match.group(1)
        return str(parameters.get(key, match.group(0)))

    return VARIABLE_PATTERN.sub(replace, value)


def expanded_actions_from_recipe(recipe_file):
    recipe, recipe_path_value = load_plist(recipe_file)
    if recipe.get("kind") == "macro":
        template_file = recipe["template"]
        template, template_path_value = load_plist(template_file)
        parameters = merge_parameters(template.get("parameters", {}), recipe.get("parameters", {}))
        actions = expand_value(template.get("actions", []), parameters)
        return recipe, template, parameters, actions, recipe_path_value, template_path_value

    parameters = dict(recipe.get("parameters", {}))
    actions = expand_value(recipe.get("actions", []), parameters)
    return recipe, recipe, parameters, actions, recipe_path_value, recipe_path_value


def action_create_glyph(font, verbose=False, glyph=None, export=True, overwrite=False, color=None, **_kwargs):
    existing = glyph_for_name(font, glyph)
    if existing is not None:
        if overwrite:
            clear_glyph(existing)
            existing.export = bool(export)
            set_glyph_color(existing, color)
            log("Overwrote existing glyph %s." % glyph, verbose)
            return existing
        if glyph_is_empty(existing):
            clear_glyph(existing)
            existing.export = bool(export)
            set_glyph_color(existing, color)
            log("Using existing empty glyph %s." % glyph, verbose)
            return existing
        raise RecipeStopped("Glyph %s already exists. Enable 'Overwrite glyphs' to replace it." % glyph)
    new_glyph = GSGlyph(glyph)
    new_glyph.export = bool(export)
    set_glyph_color(new_glyph, color)
    font.glyphs.append(new_glyph)
    log("Created glyph %s export=%s." % (glyph, bool(export)), verbose)
    return new_glyph


def action_add_component(font, verbose=False, glyph=None, component=None, **_kwargs):
    target_glyph = glyph_for_name(font, glyph)
    if target_glyph is None:
        raise RuntimeError("Missing glyph: %s" % glyph)
    changed = 0
    for layer in target_glyph.layers:
        if append_component_to_layer(layer, component):
            changed += 1
    log("%s: added component %s to %i layer(s)." % (glyph, component, changed), verbose)
    return changed


def action_add_components(font, verbose=False, glyph=None, components=None, **_kwargs):
    target_glyph = glyph_for_name(font, glyph)
    if target_glyph is None:
        raise RuntimeError("Missing glyph: %s" % glyph)
    if isinstance(components, str):
        components = [components]
    changed = 0
    for layer in target_glyph.layers:
        for component in components:
            if append_component_to_layer(layer, component):
                changed += 1
    log("%s: added %i component instance(s) on each layer (%i total)." % (
        glyph,
        len(components or []),
        changed,
    ), verbose)
    return changed


def action_disable_component_alignment(font, verbose=False, glyph=None, components=None, enabled=True, **_kwargs):
    if not boolean_value(enabled):
        log("%s: automatic alignment left enabled." % glyph, verbose)
        return 0

    target_glyph = glyph_for_name(font, glyph)
    if target_glyph is None:
        raise RuntimeError("Missing glyph: %s" % glyph)
    if isinstance(components, str):
        components = [components]
    wanted_components = set(components or [])
    changed = 0
    for layer in target_glyph.layers:
        for component in layer_components(layer):
            if wanted_components and component_name(component) not in wanted_components:
                continue
            if disable_component_alignment(component):
                changed += 1
    log("%s: disabled automatic alignment on %i component(s)%s." % (
        glyph,
        changed,
        " matching %s" % ", ".join(components) if components else "",
    ), verbose)
    return changed


def action_place_component_sequence_by_widths(
    font,
    verbose=False,
    glyph=None,
    components=None,
    enabled=False,
    **_kwargs
):
    if not boolean_value(enabled):
        log("%s: width-based component placement skipped." % glyph, verbose)
        return 0

    target_glyph = glyph_for_name(font, glyph)
    if target_glyph is None:
        raise RuntimeError("Missing glyph: %s" % glyph)
    if isinstance(components, str):
        components = [components]

    changed = 0
    skipped = 0
    for layer in target_glyph.layers:
        sequence = ordered_components_for_sequence(layer, components)
        if len(sequence) != len(components or []):
            skipped += 1
            continue

        x_offset = 0.0
        for component in sequence:
            a, b, c, d, _tx, ty = transform_values(component)
            if set_component_transform(component, (a, b, c, d, x_offset, ty)):
                changed += 1
            source_layer = component_source_layer(font, component, layer)
            width = layer_width(source_layer) if source_layer is not None else None
            if width is None:
                skipped += 1
                width = 0.0
            x_offset += width
        set_layer_metric(layer, "width", x_offset)

    log("%s: placed %i component(s) by source widths%s." % (
        glyph,
        changed,
        "; skipped %i layer(s)/width(s)" % skipped if skipped else "",
    ), verbose)
    return changed


def action_align_component_sequence_anchors(
    font,
    verbose=False,
    glyph=None,
    components=None,
    enabled=False,
    autoMatching=True,
    matchingAnchors=None,
    exitAnchors=None,
    entryAnchors=None,
    **_kwargs
):
    use_named_exit_entry = boolean_value(enabled)
    use_auto_matching = boolean_value(autoMatching)
    if not use_named_exit_entry and not use_auto_matching:
        log("%s: anchor alignment skipped." % glyph, verbose)
        return 0

    target_glyph = glyph_for_name(font, glyph)
    if target_glyph is None:
        raise RuntimeError("Missing glyph: %s" % glyph)
    if isinstance(components, str):
        components = [components]
    if isinstance(exitAnchors, str):
        exitAnchors = [exitAnchors]
    if isinstance(entryAnchors, str):
        entryAnchors = [entryAnchors]
    exitAnchors = exitAnchors or ["#exit", "exit"]
    entryAnchors = entryAnchors or ["#entry", "entry"]

    changed = 0
    skipped = 0
    auto_matched = 0
    for layer in target_glyph.layers:
        sequence = ordered_components_for_sequence(layer, components)
        if len(sequence) < 2:
            skipped += 1
            continue

        for previous_component, next_component in zip(sequence[:-1], sequence[1:]):
            previous_layer = component_source_layer(font, previous_component, layer)
            next_layer = component_source_layer(font, next_component, layer)
            if previous_layer is None or next_layer is None:
                skipped += 1
                continue

            exit_xy = None
            entry_xy = None
            if use_named_exit_entry:
                exit_xy = effective_layer_anchor_xy(font, previous_layer, exitAnchors)
                entry_xy = effective_layer_anchor_xy(font, next_layer, entryAnchors)
            if (exit_xy is None or entry_xy is None) and use_auto_matching:
                exit_xy, entry_xy = first_matching_anchor_pair(
                    font,
                    previous_layer,
                    next_layer,
                    matchingAnchors,
                )
                if exit_xy is not None and entry_xy is not None:
                    auto_matched += 1
            if exit_xy is None or entry_xy is None:
                skipped += 1
                continue

            exit_target_xy = transformed_point(previous_component, exit_xy)
            if move_component_local_point_to(next_component, entry_xy, exit_target_xy):
                changed += 1
            else:
                skipped += 1

    log("%s: aligned %i component pair(s) by anchors%s." % (
        glyph,
        changed,
        "; auto-matched %i; skipped %i" % (auto_matched, skipped) if auto_matched or skipped else "",
    ), verbose)
    return changed


def action_align_component_midpoint_to_math_axis(
    font,
    verbose=False,
    glyph=None,
    components=None,
    enabled=False,
    anchorName="center",
    disableAlignment=True,
    **_kwargs
):
    if not boolean_value(enabled):
        log("%s: center midpoint math-axis alignment skipped." % glyph, verbose)
        return 0

    target_glyph = glyph_for_name(font, glyph)
    if target_glyph is None:
        raise RuntimeError("Missing glyph: %s" % glyph)
    if isinstance(components, str):
        components = [components]
    if len(components or []) != 2:
        raise RuntimeError("%s: midpoint math-axis alignment needs exactly two components." % glyph)

    changed = 0
    skipped = 0
    for layer in target_glyph.layers:
        layer_label = layer_name(layer) or layer_id(layer) or "<unnamed layer>"
        sequence = ordered_components_for_sequence(layer, components)
        if len(sequence) != 2:
            log("%s/%s: midpoint skipped, found %i matching component(s), expected 2." % (
                glyph,
                layer_label,
                len(sequence),
            ), verbose)
            skipped += 1
            continue

        anchor_positions = []
        debug_records = []
        for component in sequence:
            component_label = component_name(component) or "<unnamed component>"
            source_layer = component_source_layer(font, component, layer)
            if source_layer is None:
                debug_records.append("%s: missing source layer" % component_label)
                break
            local_xy = effective_layer_anchor_xy(font, source_layer, [anchorName])
            if local_xy is None:
                debug_records.append("%s/%s: missing anchor %s" % (
                    component_label,
                    layer_name(source_layer) or layer_id(source_layer) or "<unnamed source layer>",
                    anchorName,
                ))
                break
            transformed_xy = transformed_point(component, local_xy)
            anchor_positions.append(transformed_xy)
            debug_records.append("%s/%s: local %s -> placed %s" % (
                component_label,
                layer_name(source_layer) or layer_id(source_layer) or "<unnamed source layer>",
                format_xy(local_xy),
                format_xy(transformed_xy),
            ))
        if len(anchor_positions) != 2:
            log("%s/%s: midpoint skipped; %s." % (
                glyph,
                layer_label,
                "; ".join(debug_records) if debug_records else "no anchor records",
            ), verbose)
            skipped += 1
            continue

        midpoint_y = (anchor_positions[0][1] + anchor_positions[1][1]) / 2.0
        math_axis = math_axis_for_layer(font, layer)
        dy = math_axis - midpoint_y
        log("%s/%s: %s; midpointY %.3f, mathAxis %.3f, dy %.3f." % (
            glyph,
            layer_label,
            "; ".join(debug_records),
            midpoint_y,
            math_axis,
            dy,
        ), verbose)
        if abs(dy) < 0.0001:
            continue

        moved = 0
        for component in sequence:
            if boolean_value(disableAlignment):
                disable_component_alignment(component)
            if move_component_by(component, dy=dy):
                moved += 1
        if moved:
            changed += moved
        else:
            skipped += 1

    log("%s: moved %i component(s) to center midpoint on math axis%s." % (
        glyph,
        changed,
        "; skipped %i layer(s)" % skipped if skipped else "",
    ), verbose)
    return changed


def action_align_component_pairs_by_anchors(
    font,
    verbose=False,
    glyph=None,
    components=None,
    pairs=None,
    disableAlignment=True,
    **_kwargs
):
    if not pairs:
        log("%s: explicit component pair alignment skipped." % glyph, verbose)
        return 0

    target_glyph = glyph_for_name(font, glyph)
    if target_glyph is None:
        raise RuntimeError("Missing glyph: %s" % glyph)
    if isinstance(components, str):
        components = [components]

    changed = 0
    skipped = 0
    for layer in target_glyph.layers:
        sequence = ordered_components_for_sequence(layer, components)
        for pair in pairs:
            try:
                component_indexes = list(pair.get("componentIndexes", []))
                base_index = int(component_indexes[0])
                mark_index = int(component_indexes[1])
            except Exception:
                skipped += 1
                continue
            if base_index >= len(sequence) or mark_index >= len(sequence):
                skipped += 1
                continue

            base_component = sequence[base_index]
            mark_component = sequence[mark_index]
            base_source = component_source_master_layer if boolean_value(pair.get("baseUseAssociatedMasterLayer")) else component_source_layer
            mark_source = component_source_master_layer if boolean_value(pair.get("markUseAssociatedMasterLayer")) else component_source_layer
            base_layer = base_source(font, base_component, layer)
            mark_layer = mark_source(font, mark_component, layer)
            if base_layer is None or mark_layer is None:
                skipped += 1
                continue

            base_anchor = pair.get("baseAnchor")
            mark_anchor = pair.get("markAnchor")
            base_xy = effective_layer_anchor_xy(font, base_layer, [base_anchor])
            mark_xy = effective_layer_anchor_xy(font, mark_layer, [mark_anchor])
            if base_xy is None or mark_xy is None:
                skipped += 1
                continue

            if boolean_value(disableAlignment):
                disable_component_alignment(mark_component)
            target_xy = transformed_point(base_component, base_xy)
            if move_component_local_point_to(mark_component, mark_xy, target_xy):
                changed += 1
            else:
                skipped += 1

    log("%s: aligned %i explicit component pair(s) by anchors%s." % (
        glyph,
        changed,
        "; skipped %i" % skipped if skipped else "",
    ), verbose)
    return changed


def action_flip_components(font, verbose=False, glyph=None, components=None, **_kwargs):
    target_glyph = glyph_for_name(font, glyph)
    if target_glyph is None:
        raise RuntimeError("Missing glyph: %s" % glyph)
    if isinstance(components, str):
        components = [components]
    wanted_components = set(components or [])
    changed = 0
    skipped = 0
    for layer in target_glyph.layers:
        for component in layer_components(layer):
            if wanted_components and component_name(component) not in wanted_components:
                continue
            disable_component_alignment(component)
            if flip_component_across_horizontal_center(component):
                changed += 1
            else:
                skipped += 1
    log("%s: flipped %i component(s)%s." % (
        glyph,
        changed,
        "; skipped %i" % skipped if skipped else "",
    ), verbose)
    return changed


def action_copy_layer_metrics(font, verbose=False, glyph=None, sourceGlyph=None, **_kwargs):
    target_glyph = glyph_for_name(font, glyph)
    source_glyph = glyph_for_name(font, sourceGlyph)
    if target_glyph is None:
        raise RuntimeError("Missing glyph: %s" % glyph)
    if source_glyph is None:
        raise RuntimeError("Missing source glyph: %s" % sourceGlyph)

    changed_layers = 0
    skipped_layers = 0
    for target_layer in target_glyph.layers:
        source_layer = matching_layer(source_glyph, target_layer)
        if source_layer is None:
            skipped_layers += 1
            continue
        copy_layer_metrics(source_layer, target_layer, sourceGlyph)
        changed_layers += 1
    log("%s: copied metrics from %s to %i layer(s)%s." % (
        glyph,
        sourceGlyph,
        changed_layers,
        "; skipped %i" % skipped_layers if skipped_layers else "",
    ), verbose)
    return changed_layers


def action_set_side_metrics_from_component_sequence(
    font,
    verbose=False,
    glyph=None,
    components=None,
    leftGlyph=None,
    rightGlyph=None,
    **_kwargs
):
    target_glyph = glyph_for_name(font, glyph)
    if target_glyph is None:
        raise RuntimeError("Missing glyph: %s" % glyph)
    if isinstance(components, str):
        components = [components]
    if not components:
        raise RuntimeError("%s: no components supplied for side metrics." % glyph)

    leftGlyph = leftGlyph or components[0]
    rightGlyph = rightGlyph or components[-1]
    left_key = "=%s" % leftGlyph
    right_key = "=%s" % rightGlyph
    layer_count = 0
    changed = 0
    for layer in target_glyph.layers:
        layer_count += 1
        if set_layer_metrics_key(layer, "leftMetricsKey", left_key):
            changed += 1
        if set_layer_metrics_key(layer, "rightMetricsKey", right_key):
            changed += 1
    log("%s: set LSB key %s and RSB key %s on %i layer(s)." % (
        glyph,
        left_key,
        right_key,
        layer_count,
    ), verbose)
    return changed


def sync_layer_metrics(layer):
    for method_name in ("syncMetrics", "updateMetrics", "updateMetrics_"):
        method = getattr(layer, method_name, None)
        if method is None:
            continue
        try:
            method()
            return True
        except TypeError:
            try:
                method(None)
                return True
            except Exception:
                pass
        except Exception:
            pass
    return False


def action_update_metrics(font, verbose=False, glyph=None, mastersOnly=True, **_kwargs):
    target_glyph = glyph_for_name(font, glyph)
    if target_glyph is None:
        raise RuntimeError("Missing glyph: %s" % glyph)

    changed = 0
    skipped = 0
    for layer in target_glyph.layers:
        if boolean_value(mastersOnly) and not is_master_layer(layer):
            continue
        if sync_layer_metrics(layer):
            changed += 1
        else:
            skipped += 1
    log("%s: updated metrics on %i layer(s)%s." % (
        glyph,
        changed,
        "; skipped %i" % skipped if skipped else "",
    ), verbose)
    return changed


def action_create_high_layers(font, verbose=False, glyph=None, axis="height", lowValue=0, highValue=100, **_kwargs):
    target_glyph = glyph_for_name(font, glyph)
    if target_glyph is None:
        raise RuntimeError("Missing glyph: %s" % glyph)
    height_axis, created_axis = ensure_smart_axis(target_glyph, axis, lowValue, highValue)
    master_properties = 0
    for layer in target_glyph.layers:
        if is_master_layer(layer) and set_height_layer_properties(layer, axis, height_axis, SMART_MASTER_SELECTION_VALUE):
            master_properties += 1
    created_layers = 0
    removed_layers = 0
    for master in font.masters:
        removed_layers += remove_existing_high_layers(target_glyph, master)
        master_layer = target_glyph.layers[master.id]
        if master_layer is None:
            continue
        high_layer = master_layer.copy()
        high_layer.layerId = str(uuid.uuid4()).upper()
        set_associated_master_id(high_layer, master.id)
        high_layer.name = high_layer_name(master)
        set_height_layer_properties(high_layer, axis, height_axis, SMART_HIGH_SELECTION_VALUE)
        target_glyph.layers.insert(layer_index(target_glyph, master_layer) + 1, high_layer)
        created_layers += 1
    log("%s: %s smart axis %s, set %i master layer(s), created %i High layer(s), removed %i old High layer(s)." % (
        glyph,
        "created" if created_axis else "updated",
        axis,
        master_properties,
        created_layers,
        removed_layers,
    ), verbose)
    return created_layers


def component_matches_filter(component, component_filter):
    if not component_filter:
        return True
    name = component_name(component)
    components = component_filter.get("components")
    component = component_filter.get("component")
    if components is not None:
        return name in components
    if component is not None:
        return name == component
    return True


def action_set_component_axis_low_high(font, verbose=False, glyph=None, axis="height", lowValue=0, highValue=100, componentFilter=None, **_kwargs):
    target_glyph = glyph_for_name(font, glyph)
    if target_glyph is None:
        raise RuntimeError("Missing glyph: %s" % glyph)
    changed = 0
    skipped = 0
    for layer in target_glyph.layers:
        is_high = "high" in layer_name(layer).lower()
        value = highValue if is_high else lowValue
        for component in layer_components(layer):
            if not component_matches_filter(component, componentFilter):
                continue
            axis_id = smart_axis_id_for_component(font, component, axis)
            if axis_id is None:
                skipped += 1
                continue
            if set_component_smart_value(component, axis_id, value):
                changed += 1
            else:
                skipped += 1
    log("%s: set %s low/high on %i component(s)%s." % (
        glyph,
        axis,
        changed,
        "; skipped %i" % skipped if skipped else "",
    ), verbose)
    return changed


def action_set_component_axis_value(font, verbose=False, glyph=None, axis="height", value=0, componentFilter=None, **_kwargs):
    target_glyph = glyph_for_name(font, glyph)
    if target_glyph is None:
        raise RuntimeError("Missing glyph: %s" % glyph)
    changed = 0
    skipped = 0
    for layer in target_glyph.layers:
        for component in layer_components(layer):
            if not component_matches_filter(component, componentFilter):
                continue
            axis_id = smart_axis_id_for_component(font, component, axis)
            if axis_id is None:
                skipped += 1
                continue
            if set_component_smart_value(component, axis_id, value):
                changed += 1
            else:
                skipped += 1
    log("%s: set %s=%s on %i component(s)%s." % (
        glyph,
        axis,
        value,
        changed,
        "; skipped %i" % skipped if skipped else "",
    ), verbose)
    return changed


def layer_matches_name_rule(layer_label, rule):
    contains = rule.get("contains")
    if isinstance(contains, str):
        contains = [contains]
    if contains:
        lowered = layer_label.lower()
        for item in contains:
            if str(item).lower() not in lowered:
                return False
    return True


def scale_pair_from_rule(rule):
    if "scale" in rule:
        value = rule.get("scale")
        return value, value
    if "xScale" in rule or "yScale" in rule:
        x_value = rule.get("xScale", rule.get("yScale", 1))
        y_value = rule.get("yScale", x_value)
        return x_value, y_value
    return None


def action_set_component_scale_by_layer_name(font, verbose=False, glyph=None, componentFilter=None, rules=None, defaultScale=None, **_kwargs):
    target_glyph = glyph_for_name(font, glyph)
    if target_glyph is None:
        raise RuntimeError("Missing glyph: %s" % glyph)
    if not rules and defaultScale is None:
        log("%s: component scale by layer name skipped." % glyph, verbose)
        return 0

    changed = 0
    skipped = 0
    for layer in target_glyph.layers:
        label = layer_name(layer) or ""
        scale_pair = None
        for rule in rules or []:
            if layer_matches_name_rule(label, rule):
                scale_pair = scale_pair_from_rule(rule)
                break
        if scale_pair is None and defaultScale is not None:
            scale_pair = (defaultScale, defaultScale)
        if scale_pair is None:
            skipped += 1
            continue

        for component in layer_components(layer):
            if not component_matches_filter(component, componentFilter):
                continue
            if set_component_scale(component, scale_pair[0], scale_pair[1]):
                changed += 1
            else:
                skipped += 1

    log("%s: set component scale on %i component(s)%s." % (
        glyph,
        changed,
        "; skipped %i" % skipped if skipped else "",
    ), verbose)
    return changed


def action_create_smart_component_variants(font, verbose=False, glyph=None, values=None, N=None, step=None, axis="height", color=None, overwrite=False, startNumber=1, **_kwargs):
    source_glyph = glyph_for_name(font, glyph)
    if source_glyph is None:
        raise RuntimeError("Missing glyph: %s" % glyph)
    variant_values = number_list(values)
    if variant_values is None:
        variant_count = int(N if N is not None else 1)
        step = float(step if step is not None else 1)
        variant_values = [0] + [clean_number(number * step) for number in range(1, variant_count + 1)]
    if not variant_values:
        raise RuntimeError("%s: createSmartComponentVariants needs at least one value." % glyph)
    base_value = variant_values[0]
    variant_count = max(0, len(variant_values) - 1)
    created = 0
    refreshed = 0
    for number, value in zip(
        range(int(startNumber), int(startNumber) + variant_count),
        variant_values[1:],
    ):
        target_name = variant_name(source_glyph.name, number)
        target_glyph = glyph_for_name(font, target_name)
        did_create = False
        if target_glyph is None:
            target_glyph = GSGlyph(target_name)
            copy_glyph_metadata(source_glyph, target_glyph)
            set_glyph_color(target_glyph, color)
            font.glyphs.append(target_glyph)
            did_create = True
        else:
            if not overwrite and not glyph_is_empty(target_glyph):
                raise RecipeStopped("Glyph %s already exists. Enable 'Overwrite glyphs' to replace it." % target_name)
            clear_glyph(target_glyph)
            set_glyph_color(target_glyph, color)
        populate_variant_from_source(font, source_glyph, target_glyph, axis, value - base_value)
        if did_create:
            created += 1
        else:
            refreshed += 1
    stored_variants = store_math_plugin_variants_on_glyph(font, source_glyph, variant_count, axis, startNumber)
    log("%s: created %i variant glyph(s), updated %i existing; values=%s; stored MATH plugin variants=%s." % (
        glyph,
        created,
        refreshed,
        ",".join(str(value) for value in variant_values),
        stored_variants,
    ), verbose)
    return dict(created=created, refreshed=refreshed)


ACTION_REGISTRY = {
    "createGlyph": action_create_glyph,
    "addComponent": action_add_component,
    "addComponents": action_add_components,
    "disableComponentAlignment": action_disable_component_alignment,
    "placeComponentSequenceByWidths": action_place_component_sequence_by_widths,
    "alignComponentSequenceAnchors": action_align_component_sequence_anchors,
    "alignComponentMidpointToMathAxis": action_align_component_midpoint_to_math_axis,
    "alignComponentPairsByAnchors": action_align_component_pairs_by_anchors,
    "flipComponents": action_flip_components,
    "copyLayerMetrics": action_copy_layer_metrics,
    "setSideMetricsFromComponentSequence": action_set_side_metrics_from_component_sequence,
    "updateMetrics": action_update_metrics,
    "createHighLayers": action_create_high_layers,
    "setComponentAxisLowHigh": action_set_component_axis_low_high,
    "setComponentAxisValue": action_set_component_axis_value,
    "setComponentScaleByLayerName": action_set_component_scale_by_layer_name,
    "createSmartComponentVariants": action_create_smart_component_variants,
}


def run_action(font, action, verbose=False, overwrite_glyphs=False):
    function_name = action.get("function")
    function = ACTION_REGISTRY.get(function_name)
    if function is None:
        raise RuntimeError("Unknown recipe function: %s" % function_name)
    arguments = dict(action.get("arguments", {}))
    if function_name in ("createGlyph", "createSmartComponentVariants"):
        arguments["overwrite"] = bool(overwrite_glyphs)
    return function(font, verbose=verbose, **arguments)


def glyph_names_touched_by_action(action):
    if action.get("type") != "call":
        return []

    function_name = action.get("function")
    arguments = dict(action.get("arguments", {}))
    if function_name == "createGlyph":
        glyph_name = arguments.get("glyph")
        return [glyph_name] if glyph_name else []

    if function_name == "createSmartComponentVariants":
        glyph_name = arguments.get("glyph")
        if not glyph_name:
            return []
        values = number_list(arguments.get("values"))
        if values is None:
            try:
                variant_count = int(arguments.get("N", 1))
            except Exception:
                variant_count = 1
        else:
            variant_count = max(0, len(values) - 1)
        try:
            start_number = int(arguments.get("startNumber", 1))
        except Exception:
            start_number = 1
        return [
            variant_name(glyph_name, number)
            for number in range(start_number, start_number + variant_count)
        ]

    return []


def run_recipe(recipe_file=DEFAULT_RECIPE_FILE, verbose=VERBOSE, overwrite_glyphs=False):
    font = Glyphs.font
    if font is None:
        raise RuntimeError("No font open.")
    recipe, template, parameters, actions, recipe_path_value, template_path_value = expanded_actions_from_recipe(recipe_file)
    log("Run Math Glyphs Recipe", verbose)
    log("Script version: %s" % SCRIPT_VERSION, verbose)
    log("Recipe: %s" % recipe_path_value, verbose)
    log("Template: %s" % template_path_value, verbose)
    log("Name: %s" % recipe.get("name", template.get("name", "<unnamed>")), verbose)
    log("Actions: %i" % len(actions), verbose)
    log("Overwrite glyphs: %s" % ("yes" if overwrite_glyphs else "no"), verbose)
    log("", verbose)
    touched_glyphs = []
    font.disableUpdateInterface()
    try:
        for index, action in enumerate(actions, 1):
            log("%i. %s" % (index, action.get("function")), verbose)
            run_action(font, action, verbose=verbose, overwrite_glyphs=overwrite_glyphs)
            touched_glyphs.extend(glyph_names_touched_by_action(action))
    finally:
        font.enableUpdateInterface()
    log("", verbose)
    log("Done.", verbose)
    return dict(glyphs=unique_strings(touched_glyphs))
