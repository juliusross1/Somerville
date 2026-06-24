#MenuTitle: Align Component Centers to Math Axis
# -*- coding: utf-8 -*-

try:
    from Foundation import NSPoint
except Exception:
    NSPoint = None

from GlyphsApp import Glyphs


SCRIPT_VERSION = "2026-06-24 13:29 CDT master-math-axis-parameter"
CENTER_ANCHOR_NAME = "center"
MATH_AXIS_PARAMETER = "Math Axis"
POSITION_TOLERANCE = 0.001


def print_warning(message):
    print("WARNING: %s" % message)


def safe_call(value, default=None):
    if callable(value):
        try:
            return value()
        except Exception:
            return default
    return value


def selected_glyph(font):
    selected_layers = list(font.selectedLayers or [])
    if not selected_layers:
        return None
    return selected_layers[0].parent


def layer_name(layer):
    return str(safe_call(getattr(layer, "name", ""), "") or "")


def layer_label(layer):
    return layer_name(layer) or str(getattr(layer, "layerId", "") or "<unnamed layer>")


def call_method(obj, method_name):
    method = getattr(obj, method_name, None)
    if callable(method):
        try:
            method()
        except Exception:
            pass


def xy_values(point):
    try:
        return float(point.x), float(point.y)
    except Exception:
        pass

    try:
        return float(point[0]), float(point[1])
    except Exception:
        return 0.0, 0.0


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


def numeric_value(value):
    if value is None:
        return None

    try:
        return float(value)
    except Exception:
        pass

    for attribute_name in ("position", "pos", "value"):
        try:
            attribute_value = getattr(value, attribute_name)
        except Exception:
            continue
        try:
            return float(attribute_value)
        except Exception:
            pass

    return None


def master_for_layer(font, layer):
    master = getattr(layer, "master", None)
    if master is not None:
        return master

    associated_master_id = getattr(layer, "associatedMasterId", None)
    if associated_master_id:
        try:
            master = font.masters[associated_master_id]
            if master is not None:
                return master
        except Exception:
            pass

    layer_id = getattr(layer, "layerId", None)
    if layer_id:
        try:
            master = font.masters[layer_id]
            if master is not None:
                return master
        except Exception:
            pass

    return font.selectedFontMaster


def metric_name(metric):
    return str(safe_call(getattr(metric, "name", None), "") or "")


def metric_id(metric):
    value = safe_call(getattr(metric, "id", None))
    if value is None:
        return None
    return value


def master_metric_value_for_metric(master, metric, index):
    metric_id_value = metric_id(metric)
    if metric_id_value is not None:
        method = getattr(master, "metricValueForId_", None)
        if method is not None:
            try:
                value = method(metric_id_value)
                if value is not None:
                    return value
            except Exception:
                pass

        try:
            value = master.metricValues[metric_id_value]
            if value is not None:
                return value
        except Exception:
            pass

    for attribute_name in ("metrics", "metricValues"):
        try:
            values = list(getattr(master, attribute_name))
        except Exception:
            continue

        if index < len(values):
            value = values[index]
            if value is not None:
                return value

    return None


def math_axis_for_layer(font, layer):
    master = master_for_layer(font, layer)
    custom_parameter_axis = numeric_value(custom_parameter_value(master, MATH_AXIS_PARAMETER))
    if custom_parameter_axis is not None:
        return custom_parameter_axis, "master custom parameter %s" % MATH_AXIS_PARAMETER

    try:
        metrics = list(font.metrics)
    except Exception:
        metrics = []

    for index, metric in enumerate(metrics):
        if metric_name(metric) != MATH_AXIS_PARAMETER:
            continue

        metric_value = numeric_value(master_metric_value_for_metric(master, metric, index))
        if metric_value is not None:
            return metric_value, "master metric %s" % MATH_AXIS_PARAMETER

    return None, None


def layer_components(layer):
    try:
        return list(layer.components)
    except Exception:
        return []


def component_name(component):
    for attribute_name in ("componentName", "name"):
        value = safe_call(getattr(component, attribute_name, None))
        if value:
            return str(value)

    component_glyph = safe_call(getattr(component, "component", None))
    if component_glyph is not None:
        value = safe_call(getattr(component_glyph, "name", None))
        if value:
            return str(value)

    glyph = safe_call(getattr(component, "glyph", None))
    if glyph is not None:
        value = safe_call(getattr(glyph, "name", None))
        if value:
            return str(value)
    return "<unnamed component>"


def component_glyph(component):
    glyph = safe_call(getattr(component, "component", None))
    if glyph is not None:
        return glyph

    glyph = safe_call(getattr(component, "glyph", None))
    if glyph is not None:
        return glyph
    return None


def component_layer_for_parent(component, parent_layer):
    component_layer = getattr(component, "componentLayer", None)
    if component_layer is not None:
        return component_layer

    glyph = component_glyph(component)
    if glyph is None:
        return None

    layer_id = getattr(parent_layer, "associatedMasterId", None) or getattr(parent_layer, "layerId", None)
    if layer_id:
        try:
            component_layer = glyph.layers[layer_id]
            if component_layer is not None:
                return component_layer
        except Exception:
            pass

    return None


def anchor_named(layer, anchor_name):
    try:
        for anchor in list(layer.anchors):
            if getattr(anchor, "name", None) == anchor_name:
                return anchor
    except Exception:
        pass

    try:
        return layer.anchors[anchor_name]
    except Exception:
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

    position = safe_call(getattr(component, "position", None))
    if position is not None:
        x, y = xy_values(position)
        return (1.0, 0.0, 0.0, 1.0, x, y)

    return (
        1.0,
        0.0,
        0.0,
        1.0,
        float(getattr(component, "x", 0) or 0),
        float(getattr(component, "y", 0) or 0),
    )


def transformed_point(component, point):
    a, b, c, d, tx, ty = transform_values(component)
    x, y = point
    return (
        (a * float(x)) + (c * float(y)) + tx,
        (b * float(x)) + (d * float(y)) + ty,
    )


def first_center_anchor_point_in_layer(layer, seen=None):
    if seen is None:
        seen = set()

    layer_key = (getattr(layer.parent, "name", None), getattr(layer, "layerId", None))
    if layer_key in seen:
        return None
    seen.add(layer_key)

    anchor = anchor_named(layer, CENTER_ANCHOR_NAME)
    if anchor is not None:
        return xy_values(anchor.position), "direct"

    for component in layer_components(layer):
        child_layer = component_layer_for_parent(component, layer)
        if child_layer is None:
            continue

        child_result = first_center_anchor_point_in_layer(child_layer, seen)
        if child_result is None:
            continue

        child_point, source = child_result
        return transformed_point(component, child_point), "component:%s/%s" % (
            component_name(component),
            source,
        )

    return None


def point_to_position(point):
    x, y = point
    if NSPoint is not None:
        try:
            return NSPoint(float(x), float(y))
        except Exception:
            pass
    return (float(x), float(y))


def set_component_position(component, point):
    position = point_to_position(point)
    setter = getattr(component, "setPosition_", None)
    if setter is not None:
        try:
            setter(position)
            return True
        except Exception:
            pass

    try:
        component.position = position
        return True
    except Exception:
        pass

    try:
        component.position.x = float(point[0])
        component.position.y = float(point[1])
        return True
    except Exception:
        return False


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


def set_component_transform_translation_y(component, dy):
    transform = safe_call(getattr(component, "transform", None))
    if transform is None:
        return False

    a, b, c, d, tx, ty = transform_values(component)
    new_transform = (a, b, c, d, tx, ty + dy)
    setter = getattr(component, "setTransform_", None)
    if setter is not None:
        try:
            setter(new_transform)
            return True
        except Exception:
            pass

    try:
        component.transform = new_transform
        return True
    except Exception:
        return False


def move_component_y(component, dy):
    if abs(float(dy)) <= POSITION_TOLERANCE:
        return True

    position = safe_call(getattr(component, "position", None))
    if position is not None:
        try:
            x, y = xy_values(position)
            return set_component_position(component, (x, y + float(dy)))
        except Exception:
            pass

    if set_component_transform_translation_y(component, dy):
        return True

    try:
        component.y = float(getattr(component, "y", 0) or 0) + float(dy)
        return True
    except Exception:
        return False


def align_component_on_layer(font, layer, component):
    axis_y, axis_source = math_axis_for_layer(font, layer)
    if axis_y is None:
        return "skipped", "no master Math Axis value found", None

    component_layer = component_layer_for_parent(component, layer)
    if component_layer is None:
        return "skipped", "no component layer", None

    anchor_result = first_center_anchor_point_in_layer(component_layer)
    if anchor_result is None:
        return "skipped", "no center anchor", None

    local_anchor_point, source = anchor_result
    anchor_point = transformed_point(component, local_anchor_point)
    dy = axis_y - anchor_point[1]

    if abs(dy) <= POSITION_TOLERANCE:
        return "already", "%s already on %s" % (source, axis_source), dy

    if move_component_y(component, dy):
        return "moved", "%s to %s" % (source, axis_source), dy

    return "skipped", "could not move component", dy


def align_selected_glyph_components():
    font = Glyphs.font
    if font is None:
        print_warning("No font open.")
        return

    glyph = selected_glyph(font)
    if glyph is None:
        print_warning("No glyph selected.")
        return

    moved = 0
    already = 0
    skipped = 0
    alignment_disabled = 0
    alignment_disable_failed = 0
    layers_seen = 0
    components_seen = 0

    font.disableUpdateInterface()
    call_method(glyph, "beginUndo")
    try:
        for layer in glyph.layers:
            layers_seen += 1
            components = layer_components(layer)
            if not components:
                continue

            layer_moved = 0
            layer_already = 0
            layer_skipped = 0

            for component in components:
                components_seen += 1
                if disable_component_alignment(component):
                    alignment_disabled += 1
                else:
                    alignment_disable_failed += 1
                    print_warning("%s / %s / %s: could not disable automatic alignment before moving." % (
                        glyph.name,
                        layer_label(layer),
                        component_name(component),
                    ))

                status, detail, dy = align_component_on_layer(font, layer, component)
                if status == "moved":
                    moved += 1
                    layer_moved += 1
                    print("%s / %s: moved %s by y=%g (%s)" % (
                        glyph.name,
                        layer_label(layer),
                        component_name(component),
                        dy,
                        detail,
                    ))
                elif status == "already":
                    already += 1
                    layer_already += 1
                else:
                    skipped += 1
                    layer_skipped += 1
                    print_warning("%s / %s / %s: skipped, %s." % (
                        glyph.name,
                        layer_label(layer),
                        component_name(component),
                        detail,
                    ))

            if layer_already and not layer_moved and not layer_skipped:
                print("%s / %s: %i component(s) already aligned" % (
                    glyph.name,
                    layer_label(layer),
                    layer_already,
                ))
    finally:
        call_method(glyph, "endUndo")
        font.enableUpdateInterface()

    print("")
    print("Done.")
    print("Glyph: %s" % glyph.name)
    print("Layers checked: %i" % layers_seen)
    print("Components checked: %i" % components_seen)
    print("Components moved: %i" % moved)
    print("Components already aligned: %i" % already)
    print("Components skipped: %i" % skipped)
    print("Components with automatic alignment disabled: %i" % alignment_disabled)
    if alignment_disable_failed:
        print_warning("Could not disable automatic alignment on %i component(s)." % alignment_disable_failed)


try:
    Glyphs.clearLog()
    Glyphs.showMacroWindow()
    print("Align Component Centers to Math Axis")
    print("Script version: %s" % SCRIPT_VERSION)
    print("")
    align_selected_glyph_components()
except Exception as error:
    import traceback

    Glyphs.clearLog()
    Glyphs.showMacroWindow()
    print("Align Component Centers to Math Axis")
    print("")
    print_warning("Could not align component centers: %s" % error)
    print_warning(traceback.format_exc())
