# -*- coding: utf-8 -*-

"""
Design-space axis rotation helpers for Glyphs 3.

The public function in this file copies layers from a source glyph into a
destination glyph while moving the effect of one design axis onto another. The
axis tags, axis values, and glyphs are supplied by the caller; this file does
not assume specific axis names or fixed axis positions.
"""

import uuid
from GlyphsApp import GSLayer


def print_warning(message):
    print("🔴 WARNING: %s" % message)


def axis_tag(axis):
    for attribute_name in ("tag", "axisTag"):
        value = getattr(axis, attribute_name, None)
        if callable(value):
            try:
                value = value()
            except Exception:
                value = None
        if value:
            return str(value)
    return ""


def axis_id(axis):
    for attribute_name in ("axisId", "id"):
        value = getattr(axis, attribute_name, None)
        if callable(value):
            try:
                value = value()
            except Exception:
                value = None
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


def master_for_id(font, master_id):
    for master in font.masters:
        if master.id == master_id:
            return master
    return None


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


def attribute_value(layer, key):
    attributes = getattr(layer, "attributes", None)
    if not attributes:
        return None

    try:
        return attributes[key]
    except Exception:
        return None


def copied_attribute_value(value):
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return [copied_axis_rule(item) if hasattr(item, "keys") else item for item in value]
    try:
        return value.copy()
    except Exception:
        pass
    if hasattr(value, "keys"):
        return dict(value)
    try:
        return list(value)
    except Exception:
        return value


def set_layer_attribute(layer, key, value):
    copied_value = copied_attribute_value(value)
    for method_name in ("setAttribute_forKey_", "setValue_forKey_"):
        method = getattr(layer, method_name, None)
        if method is None:
            continue
        try:
            method(copied_value, key)
            return
        except Exception:
            pass
    layer.attributes[key] = copied_value


def set_layer_axis_rules(layer, axis_rules):
    set_layer_attribute(layer, "axisRules", axis_rules)


def has_axis_rules_attribute(layer):
    return attribute_value(layer, "axisRules") is not None


def axis_rules_key(axis_rules):
    if hasattr(axis_rules, "keys"):
        key = []
        rule_map = {}
        for axis_key in axis_rules.keys():
            rule_map[str(axis_key)] = copied_axis_rule(axis_rules[axis_key])
        for axis_key in sorted(rule_map.keys()):
            copied_rule = rule_map[axis_key]
            key.append((
                axis_key,
                copied_rule.get("min"),
                copied_rule.get("max"),
            ))
        return tuple(key)

    key = []
    for rule in axis_rule_items(axis_rules):
        copied_rule = copied_axis_rule(rule)
        key.append((
            copied_rule.get("min"),
            copied_rule.get("max"),
        ))
    return tuple(key)


def axis_rules_match(first_axis_rules, second_axis_rules):
    return axis_rules_key(first_axis_rules) == axis_rules_key(second_axis_rules)


def axis_rule_items(axis_rules):
    if axis_rules is None:
        return []
    try:
        return list(axis_rules)
    except Exception:
        return []


def copied_axis_rule(rule):
    if rule is None:
        return {}
    if hasattr(rule, "keys"):
        copied_rule = {}
        for key in rule.keys():
            copied_rule[key] = rule[key]
        return copied_rule
    try:
        return dict(rule)
    except Exception:
        return {}


def mutable_copy(value):
    if value is None:
        return None
    method = getattr(value, "mutableCopy", None)
    if method is not None:
        try:
            return method()
        except Exception:
            pass
    method = getattr(value, "copy", None)
    if method is not None:
        try:
            return method()
        except Exception:
            pass
    return None


def set_rule_limit(rule, key, value):
    try:
        rule[key] = value
        return True
    except Exception:
        pass
    method = getattr(rule, "setObject_forKey_", None)
    if method is not None:
        try:
            method(value, key)
            return True
        except Exception:
            pass
    return False


def remove_rule_limit(rule, key):
    try:
        if key in rule:
            del rule[key]
        return True
    except Exception:
        pass
    method = getattr(rule, "removeObjectForKey_", None)
    if method is not None:
        try:
            method(key)
            return True
        except Exception:
            pass
    return False


def replace_rule(rules, index, rule):
    try:
        rules[index] = rule
        return True
    except Exception:
        pass
    method = getattr(rules, "replaceObjectAtIndex_withObject_", None)
    if method is not None:
        try:
            method(index, rule)
            return True
        except Exception:
            pass
    return False


def axis_rule_has_limits(rule):
    if rule is None:
        return False
    try:
        return "min" in rule or "max" in rule
    except Exception:
        return False


def remap_axis_rules(axis_rules, source_axis_index, target_axis_index):
    rules = [copied_axis_rule(rule) for rule in axis_rule_items(axis_rules)]
    if (
        source_axis_index is None
        or target_axis_index is None
        or source_axis_index >= len(rules)
        or target_axis_index >= len(rules)
    ):
        return copied_attribute_value(axis_rules), False

    source_rule = copied_axis_rule(rules[source_axis_index])
    if not axis_rule_has_limits(source_rule):
        return copied_attribute_value(axis_rules), False

    target_rule = copied_axis_rule(rules[target_axis_index])
    for limit_name in ("min", "max"):
        if limit_name in source_rule:
            target_rule[limit_name] = source_rule[limit_name]

    rules[source_axis_index] = {}
    rules[target_axis_index] = target_rule
    return rules, True


def remap_axis_rules_by_axis_id(axis_rules, source_axis_id, target_axis_id):
    if not hasattr(axis_rules, "keys"):
        return copied_attribute_value(axis_rules), False

    rules = {}
    for key in axis_rules.keys():
        rules[str(key)] = copied_axis_rule(axis_rules[key])
    source_key = str(source_axis_id)
    target_key = str(target_axis_id)

    source_rule = copied_axis_rule(rules.get(source_key))
    if not axis_rule_has_limits(source_rule):
        return copied_attribute_value(axis_rules), False

    target_rule = copied_axis_rule(rules.get(target_key))
    for limit_name in ("min", "max"):
        if limit_name in source_rule:
            target_rule[limit_name] = source_rule[limit_name]

    rules[source_key] = {}
    rules[target_key] = target_rule
    return rules, True


def remap_axis_rules_native(axis_rules, source_axis_index, target_axis_index, source_axis_id=None, target_axis_id=None):
    if source_axis_id is not None and target_axis_id is not None:
        remapped_rules, remapped = remap_axis_rules_by_axis_id(axis_rules, source_axis_id, target_axis_id)
        if remapped:
            return remapped_rules, True

    rules = mutable_copy(axis_rules)
    if rules is None:
        return remap_axis_rules(axis_rules, source_axis_index, target_axis_index)

    try:
        source_rule = mutable_copy(rules[source_axis_index])
        target_rule = mutable_copy(rules[target_axis_index])
    except Exception:
        return remap_axis_rules(axis_rules, source_axis_index, target_axis_index)

    if source_rule is None or target_rule is None or not axis_rule_has_limits(source_rule):
        return remap_axis_rules(axis_rules, source_axis_index, target_axis_index)

    changed = False
    for limit_name in ("min", "max"):
        source_values = copied_axis_rule(source_rule)
        if limit_name not in source_values:
            continue
        if set_rule_limit(target_rule, limit_name, source_values[limit_name]):
            remove_rule_limit(source_rule, limit_name)
            changed = True

    if not changed:
        return remap_axis_rules(axis_rules, source_axis_index, target_axis_index)

    replace_rule(rules, source_axis_index, source_rule)
    replace_rule(rules, target_axis_index, target_rule)
    return rules, True


def force_layer_rules_to_target_axis(layer, source_axis_index, target_axis_index, source_axis_id=None, target_axis_id=None):
    axis_rules = attribute_value(layer, "axisRules")
    remapped_axis_rules, remapped = remap_axis_rules_native(
        axis_rules,
        source_axis_index,
        target_axis_index,
        source_axis_id,
        target_axis_id,
    )
    if remapped:
        set_layer_axis_rules(layer, remapped_axis_rules)
    return remapped, remapped_axis_rules


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


def corresponding_master_for_axis_value(font, coordinates, source_axis_id, target_axis_id, source_axis_value):
    if coordinates is None:
        return None

    target_coordinates = dict(coordinates)
    target_coordinates[str(source_axis_id)] = float(source_axis_value)

    ignored_axis_ids = [target_axis_id]
    for master in font.masters:
        master_coords = master_coordinates(font, master)
        if master_coords is None:
            continue
        if coordinates_match_except_axes(font, master_coords, target_coordinates, ignored_axis_ids):
            return master
    return None


def intermediate_layer_name(master, target_axis_tag, target_axis_value):
    return "%s %s %s" % (master.name, target_axis_tag, target_axis_value)


def alternate_rules_name(master, axis_rules, font):
    parts = []
    if hasattr(axis_rules, "keys"):
        axis_tags_by_id = {}
        for axis in font.axes:
            current_axis_id = axis_id(axis)
            if current_axis_id is not None:
                axis_tags_by_id[str(current_axis_id)] = axis_tag(axis)
        rule_map = {}
        for key in axis_rules.keys():
            rule_map[str(key)] = copied_axis_rule(axis_rules[key])
        for axis_key in sorted(rule_map.keys()):
            copied_rule = rule_map[axis_key]
            if not copied_rule:
                continue
            axis_tag_label = axis_tags_by_id.get(axis_key, axis_key)
            if "max" in copied_rule:
                parts.append("%s<%s" % (axis_tag_label, copied_rule["max"]))
            if "min" in copied_rule:
                parts.append("%s>%s" % (axis_tag_label, copied_rule["min"]))
    else:
        for index, rule in enumerate(axis_rule_items(axis_rules)):
            copied_rule = copied_axis_rule(rule)
            if not copied_rule:
                continue
            try:
                axis_tag_label = axis_tag(font.axes[index])
            except Exception:
                axis_tag_label = "axis%s" % index
            if "max" in copied_rule:
                parts.append("%s<%s" % (axis_tag_label, copied_rule["max"]))
            if "min" in copied_rule:
                parts.append("%s>%s" % (axis_tag_label, copied_rule["min"]))
    if not parts:
        return "%s alternate" % master.name
    return "%s [%s]" % (master.name, ", ".join(parts))


def matching_special_layer(
    font,
    glyph,
    associated_master_id,
    coordinates=None,
    axis_rules=None,
    name=None,
    has_coordinates=None,
    has_axis_rules=None,
):
    for layer in glyph.layers:
        if layer.isMasterLayer:
            continue
        if associated_master_id is not None and getattr(layer, "associatedMasterId", None) != associated_master_id:
            continue
        if has_coordinates is not None and has_coordinates_attribute(layer) != has_coordinates:
            continue
        if has_axis_rules is not None and has_axis_rules_attribute(layer) != has_axis_rules:
            continue
        if name is not None and layer.name != name:
            continue
        if coordinates is not None and not coordinates_match(font, layer_coordinates(font, layer), coordinates):
            continue
        if axis_rules is not None and not axis_rules_match(attribute_value(layer, "axisRules"), axis_rules):
            continue
        if name is not None or coordinates is not None or axis_rules is not None:
            return layer
    return None


def special_layer_shell(layer_id, name, coordinates, axis_rules, associated_master_id, width):
    layer = GSLayer()
    layer.layerId = layer_id
    layer.associatedMasterId = associated_master_id
    layer.name = name
    if coordinates is not None:
        layer.attributes["coordinates"] = copied_attribute_value(coordinates)
    if axis_rules is not None:
        set_layer_axis_rules(layer, axis_rules)
    layer.width = width
    return layer


def layer_index(glyph, layer):
    return list(glyph.layers).index(layer)


def replace_layer_contents(target_layer, coordinates, axis_rules, associated_master_id, width):
    refreshed_layer = special_layer_shell(
        target_layer.layerId,
        target_layer.name,
        coordinates,
        axis_rules,
        associated_master_id,
        width,
    )
    glyph = target_layer.parent
    index = layer_index(glyph, target_layer)
    del glyph.layers[index]
    glyph.layers.insert(index, refreshed_layer)
    if axis_rules is not None:
        set_layer_axis_rules(refreshed_layer, axis_rules)
    return refreshed_layer


def remove_layer(glyph, layer):
    try:
        index = layer_index(glyph, layer)
    except Exception:
        return False
    try:
        del glyph.layers[index]
        return True
    except Exception:
        return False


def remove_stale_special_layers(font, glyph, keep_layer, stale_axis_rules, name, associated_master_id, coordinates, has_coordinates):
    if stale_axis_rules is None:
        return 0

    removed = 0
    for layer in list(glyph.layers):
        if keep_layer is not None and layer is keep_layer:
            continue
        if layer.isMasterLayer:
            continue
        if associated_master_id is not None and getattr(layer, "associatedMasterId", None) != associated_master_id:
            continue
        if name is not None and layer.name != name:
            continue
        if has_coordinates is not None and has_coordinates_attribute(layer) != has_coordinates:
            continue
        if coordinates is not None and not coordinates_match(font, layer_coordinates(font, layer), coordinates):
            continue
        if not axis_rules_match(attribute_value(layer, "axisRules"), stale_axis_rules):
            continue
        if remove_layer(glyph, layer):
            removed += 1

    return removed


def create_intermediate_layer(glyph, master_layer, master, coordinates, width, target_axis_tag, target_axis_value):
    new_layer = special_layer_shell(
        str(uuid.uuid4()).upper(),
        intermediate_layer_name(master, target_axis_tag, target_axis_value),
        coordinates,
        None,
        master.id,
        width,
    )
    glyph.layers.insert(layer_index(glyph, master_layer) + 1, new_layer)
    return new_layer


def create_special_layer_after(glyph, previous_layer, name, associated_master_id, coordinates, axis_rules, width):
    new_layer = special_layer_shell(
        str(uuid.uuid4()).upper(),
        name,
        coordinates,
        axis_rules,
        associated_master_id,
        width,
    )
    glyph.layers.insert(layer_index(glyph, previous_layer) + 1, new_layer)
    set_layer_axis_rules(new_layer, axis_rules)
    return new_layer


def create_rotated_coordinate_layer_after(glyph, previous_layer, name, associated_master_id, coordinates, axis_rules, width):
    new_layer = special_layer_shell(
        str(uuid.uuid4()).upper(),
        name,
        coordinates,
        axis_rules,
        associated_master_id,
        width,
    )
    glyph.layers.insert(layer_index(glyph, previous_layer) + 1, new_layer)
    return new_layer


def has_coordinates_attribute(layer):
    return attribute_value(layer, "coordinates") is not None


def source_coordinate_layers(source_glyph):
    layers = []
    for layer in source_glyph.layers:
        if layer.isMasterLayer:
            continue
        if has_coordinates_attribute(layer):
            layers.append(layer)
    return layers


def source_alternate_layers(source_glyph):
    alternates = []
    for layer in source_glyph.layers:
        if layer.isMasterLayer or has_coordinates_attribute(layer):
            continue
        if has_axis_rules_attribute(layer):
            alternates.append(layer)
    return alternates


def source_alternate_layer_for_rules(source_glyph, associated_master_id, axis_rules):
    for layer in source_alternate_layers(source_glyph):
        if getattr(layer, "associatedMasterId", None) != associated_master_id:
            continue
        if axis_rules_match(attribute_value(layer, "axisRules"), axis_rules):
            return layer
    return None


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


def source_layer_for_target_layer(
    font,
    source_glyph,
    target_layer,
    source_axis_id,
    target_axis_id,
    source_low_value,
    source_high_value,
    intermediate_coordinates_by_layer_id,
    source_layers_by_target_layer_id,
):
    mapped_source_layer = source_layers_by_target_layer_id.get(target_layer.layerId)
    if mapped_source_layer is not None:
        return mapped_source_layer, None

    coordinates = intermediate_coordinates_by_layer_id.get(target_layer.layerId)
    if coordinates is None:
        coordinates = coordinates_for_layer(font, target_layer)

    axis_rules = attribute_value(target_layer, "axisRules")
    if target_layer.isMasterLayer or (axis_rules is not None and not has_coordinates_attribute(target_layer)):
        source_axis_value = source_low_value
    else:
        source_axis_value = source_high_value

    source_master = corresponding_master_for_axis_value(
        font,
        coordinates,
        source_axis_id,
        target_axis_id,
        source_axis_value,
    )
    if source_master is None:
        return None, source_axis_value

    if axis_rules is not None:
        source_layer = source_alternate_layer_for_rules(source_glyph, source_master.id, axis_rules)
    else:
        source_layer = source_glyph.layers[source_master.id]
    return source_layer, source_axis_value


def copy_source_layers_into_target(
    font,
    glyph,
    source_glyph,
    source_axis_tag,
    source_axis_id,
    target_axis_id,
    source_low_value,
    source_high_value,
    intermediate_coordinates_by_layer_id,
    source_layers_by_target_layer_id,
):
    copied = 0
    skipped = 0

    for layer in glyph.layers:
        source_layer, source_axis_value = source_layer_for_target_layer(
            font,
            source_glyph,
            layer,
            source_axis_id,
            target_axis_id,
            source_low_value,
            source_high_value,
            intermediate_coordinates_by_layer_id,
            source_layers_by_target_layer_id,
        )
        if source_layer is None:
            skipped += 1
            print_warning("%s: could not find source layer for %s=%s" % (
                layer.name or layer.layerId,
                source_axis_tag,
                source_axis_value,
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


def rotated_coordinate_layer_name(master, source_layer, target_axis_tag, target_axis_value, axis_rules, font):
    if axis_rules is not None:
        return "%s %s %s" % (
            alternate_rules_name(master, axis_rules, font),
            target_axis_tag,
            target_axis_value,
        )
    if source_layer.name:
        return "%s %s %s" % (master.name, target_axis_tag, target_axis_value)
    return intermediate_layer_name(master, target_axis_tag, target_axis_value)


def create_rotated_source_coordinate_layers(
    font,
    source_glyph,
    destination_glyph,
    source_axis_tag,
    target_axis_tag,
    source_axis_id,
    target_axis_id,
    source_axis_index,
    target_axis_index,
    source_layers_by_target_layer_id,
):
    created = 0
    refreshed = 0
    skipped = 0

    for source_layer in source_coordinate_layers(source_glyph):
        source_coordinates = coordinates_for_layer(font, source_layer)
        if source_coordinates is None:
            skipped += 1
            print_warning("%s: skipped source coordinate layer %s, could not read coordinates" % (
                destination_glyph.name,
                source_layer.name or source_layer.layerId,
            ))
            continue

        try:
            target_axis_value = float(source_coordinates[str(source_axis_id)])
        except Exception:
            skipped += 1
            print_warning("%s: skipped source coordinate layer %s, could not read %s coordinate" % (
                destination_glyph.name,
                source_layer.name or source_layer.layerId,
                source_axis_tag,
            ))
            continue

        source_axis_rules = attribute_value(source_layer, "axisRules")
        target_axis_rules = None
        remapped_source_rule = False
        if source_axis_rules is not None:
            target_axis_rules, remapped_source_rule = remap_axis_rules_native(
                source_axis_rules,
                source_axis_index,
                target_axis_index,
                source_axis_id,
                target_axis_id,
            )

        matched_master_count = 0
        for master in font.masters:
            master_coordinates_for_match = master_coordinates(font, master)
            if master_coordinates_for_match is None:
                continue
            if not coordinates_match_except_axes(
                font,
                master_coordinates_for_match,
                source_coordinates,
                [source_axis_id, target_axis_id],
            ):
                continue

            matched_master_count += 1
            destination_coordinates = dict(master_coordinates_for_match)
            destination_coordinates[str(target_axis_id)] = target_axis_value
            layer_name = rotated_coordinate_layer_name(
                master,
                source_layer,
                target_axis_tag,
                target_axis_value,
                target_axis_rules,
                font,
            )

            if remapped_source_rule:
                stale_removed = remove_stale_special_layers(
                    font,
                    destination_glyph,
                    None,
                    source_axis_rules,
                    None,
                    master.id,
                    destination_coordinates,
                    True,
                )
                if stale_removed:
                    print("%s: deleted %i old rotated coordinate layer(s) using %s rules before recreating with %s rules" % (
                        master.name,
                        stale_removed,
                        source_axis_tag,
                        target_axis_tag,
                    ))

            existing_layer = matching_special_layer(
                font,
                destination_glyph,
                master.id,
                destination_coordinates,
                target_axis_rules,
                name=None,
                has_coordinates=True,
                has_axis_rules=target_axis_rules is not None,
            )
            if existing_layer is None:
                previous_layer = destination_glyph.layers[master.id]
                if previous_layer is None:
                    skipped += 1
                    print_warning("%s: skipped rotated source coordinate for %s, no destination master layer" % (
                        destination_glyph.name,
                        master.name,
                    ))
                    continue
                destination_layer = create_rotated_coordinate_layer_after(
                    destination_glyph,
                    previous_layer,
                    layer_name,
                    master.id,
                    destination_coordinates,
                    target_axis_rules,
                    source_layer.width,
                )
                created += 1
                action = "created"
            else:
                destination_layer = replace_layer_contents(
                    existing_layer,
                    destination_coordinates,
                    target_axis_rules,
                    master.id,
                    source_layer.width,
                )
                refreshed += 1
                action = "refreshed"

            destination_layer.name = layer_name
            if remapped_source_rule:
                force_layer_rules_to_target_axis(
                    destination_layer,
                    source_axis_index,
                    target_axis_index,
                    source_axis_id,
                    target_axis_id,
                )
                destination_layer.name = layer_name
            source_layers_by_target_layer_id[destination_layer.layerId] = source_layer
            print("%s: %s rotated coordinate layer %s from source %s at %s" % (
                master.name,
                action,
                layer_name,
                source_layer.name or source_layer.layerId,
                destination_coordinates,
            ))

        if matched_master_count == 0:
            skipped += 1
            print_warning("%s: skipped source coordinate layer %s, no matching destination master location" % (
                destination_glyph.name,
                source_layer.name or source_layer.layerId,
            ))

    return created, refreshed, skipped


def rotate_glyph_designspace(
    font,
    source_glyph,
    destination_glyph,
    source_axis_tag,
    target_axis_tag,
    source_low_value,
    source_high_value,
    target_axis_value,
):
    source_axis_id = axis_id_for_tag(font, source_axis_tag)
    if source_axis_id is None:
        print_warning("Could not find axis %s in the open font." % source_axis_tag)
        return process_stats(copy_layers_skipped=len(destination_glyph.layers))

    target_axis_id = axis_id_for_tag(font, target_axis_tag)
    if target_axis_id is None:
        print_warning("Could not find axis %s in the open font." % target_axis_tag)
        return process_stats(copy_layers_skipped=len(destination_glyph.layers))

    source_axis_index = axis_index(font, source_axis_tag)
    target_axis_index = axis_index(font, target_axis_tag)
    created = 0
    refreshed = 0
    alternates_created = 0
    alternates_refreshed = 0
    skipped = 0
    layers_copied = 0
    copy_layers_skipped = 0
    intermediate_coordinates_by_layer_id = {}
    source_layers_by_target_layer_id = {}

    print("")
    print("[%s]" % destination_glyph.name)

    for master in font.masters:
        master_layer = destination_glyph.layers[master.id]
        if master_layer is None:
            skipped += 1
            print_warning("%s: skipped, no master layer found" % master.name)
            continue

        coordinates = master_coordinates(font, master)
        if coordinates is None:
            skipped += 1
            print_warning("%s: skipped, could not read master coordinates" % master.name)
            continue
        coordinates[str(target_axis_id)] = float(target_axis_value)

        layer_name = intermediate_layer_name(master, target_axis_tag, target_axis_value)
        existing_layer = matching_special_layer(
            font,
            destination_glyph,
            master.id,
            coordinates,
            None,
            name=layer_name,
            has_coordinates=True,
            has_axis_rules=False,
        )
        if existing_layer is None:
            layer = create_intermediate_layer(
                destination_glyph,
                master_layer,
                master,
                coordinates,
                master_layer.width,
                target_axis_tag,
                target_axis_value,
            )
            intermediate_coordinates_by_layer_id[layer.layerId] = dict(coordinates)
            created += 1
            print("%s: created intermediate layer at %s" % (
                master.name,
                coordinates,
            ))
        else:
            layer = replace_layer_contents(existing_layer, coordinates, None, master.id, master_layer.width)
            intermediate_coordinates_by_layer_id[layer.layerId] = dict(coordinates)
            refreshed += 1
            print("%s: refreshed intermediate layer at %s" % (
                master.name,
                coordinates,
            ))

    coord_created, coord_refreshed, coord_skipped = create_rotated_source_coordinate_layers(
        font,
        source_glyph,
        destination_glyph,
        source_axis_tag,
        target_axis_tag,
        source_axis_id,
        target_axis_id,
        source_axis_index,
        target_axis_index,
        source_layers_by_target_layer_id,
    )
    created += coord_created
    refreshed += coord_refreshed
    skipped += coord_skipped

    for source_alternate_layer in source_alternate_layers(source_glyph):
        axis_rules = attribute_value(source_alternate_layer, "axisRules")
        target_axis_rules, remapped_source_rule = remap_axis_rules_native(
            axis_rules,
            source_axis_index,
            target_axis_index,
            source_axis_id,
            target_axis_id,
        )
        associated_master_id = getattr(source_alternate_layer, "associatedMasterId", None)
        master = master_for_id(font, associated_master_id)
        if master is None or axis_rules is None:
            skipped += 1
            print_warning("%s: skipped source alternate layer %s, could not read master/rules" % (
                destination_glyph.name,
                source_alternate_layer.name or source_alternate_layer.layerId,
            ))
            continue

        master_layer = destination_glyph.layers[master.id]
        if master_layer is None:
            skipped += 1
            print_warning("%s: skipped alternate for %s, no target master layer" % (destination_glyph.name, master.name))
            continue

        master_coords = master_coordinates(font, master)
        if master_coords is None:
            skipped += 1
            print_warning("%s: skipped alternate for %s, could not read master coordinates" % (destination_glyph.name, master.name))
            continue

        low_source_master = corresponding_master_for_axis_value(
            font,
            master_coords,
            source_axis_id,
            target_axis_id,
            source_low_value,
        )
        high_source_master = corresponding_master_for_axis_value(
            font,
            master_coords,
            source_axis_id,
            target_axis_id,
            source_high_value,
        )
        low_source_alternate = None
        high_source_alternate = None
        if low_source_master is not None:
            low_source_alternate = source_alternate_layer_for_rules(source_glyph, low_source_master.id, axis_rules)
        if high_source_master is not None:
            high_source_alternate = source_alternate_layer_for_rules(source_glyph, high_source_master.id, axis_rules)

        if low_source_alternate is None or high_source_alternate is None:
            skipped += 1
            print_warning("%s: skipped alternate for %s, could not find matching low/high source alternates" % (
                destination_glyph.name,
                master.name,
            ))
            continue

        alternate_name = alternate_rules_name(master, target_axis_rules, font)
        if remapped_source_rule:
            stale_removed = remove_stale_special_layers(
                font,
                destination_glyph,
                None,
                axis_rules,
                None,
                master.id,
                None,
                False,
            )
            if stale_removed:
                print("%s: deleted %i old alternate layer(s) using %s rules before recreating with %s rules" % (
                    master.name,
                    stale_removed,
                    source_axis_tag,
                    target_axis_tag,
                ))

        existing_alternate = matching_special_layer(
            font,
            destination_glyph,
            master.id,
            None,
            target_axis_rules,
            name=alternate_name,
            has_coordinates=False,
            has_axis_rules=True,
        )

        alternate_source_layer = high_source_alternate if remapped_source_rule else low_source_alternate
        if existing_alternate is None:
            alternate_layer = create_special_layer_after(
                destination_glyph,
                master_layer,
                alternate_name,
                master.id,
                None,
                target_axis_rules,
                alternate_source_layer.width,
            )
            alternates_created += 1
            if remapped_source_rule:
                print("%s: created alternate layer %s with %s rule remapped to %s" % (master.name, alternate_name, source_axis_tag, target_axis_tag))
            else:
                print("%s: created alternate layer %s" % (master.name, alternate_name))
        else:
            alternate_layer = replace_layer_contents(existing_alternate, None, target_axis_rules, master.id, alternate_source_layer.width)
            alternates_refreshed += 1
            if remapped_source_rule:
                print("%s: refreshed alternate layer %s with %s rule remapped to %s" % (master.name, alternate_name, source_axis_tag, target_axis_tag))
            else:
                print("%s: refreshed alternate layer %s" % (master.name, alternate_name))
        if remapped_source_rule:
            force_layer_rules_to_target_axis(
                alternate_layer,
                source_axis_index,
                target_axis_index,
                source_axis_id,
                target_axis_id,
            )
            alternate_layer.name = alternate_name
        source_layers_by_target_layer_id[alternate_layer.layerId] = alternate_source_layer

        alternate_coordinates = dict(master_coords)
        alternate_coordinates[str(target_axis_id)] = float(target_axis_value)
        alternate_intermediate_name = "%s %s %s" % (alternate_name, target_axis_tag, target_axis_value)
        if remapped_source_rule:
            stale_removed = remove_stale_special_layers(
                font,
                destination_glyph,
                None,
                axis_rules,
                None,
                master.id,
                alternate_coordinates,
                True,
            )
            if stale_removed:
                print("%s: deleted %i old alternate intermediate layer(s) using %s rules before recreating with %s rules" % (
                    master.name,
                    stale_removed,
                    source_axis_tag,
                    target_axis_tag,
                ))

        existing_alternate_intermediate = matching_special_layer(
            font,
            destination_glyph,
            master.id,
            alternate_coordinates,
            target_axis_rules,
            name=alternate_intermediate_name,
            has_coordinates=True,
            has_axis_rules=True,
        )

        if existing_alternate_intermediate is None:
            alternate_intermediate_layer = create_special_layer_after(
                destination_glyph,
                alternate_layer,
                alternate_intermediate_name,
                master.id,
                alternate_coordinates,
                target_axis_rules,
                high_source_alternate.width,
            )
            alternates_created += 1
            if remapped_source_rule:
                print("%s: created alternate intermediate layer %s with %s rule remapped to %s at %s" % (
                    master.name,
                    alternate_intermediate_name,
                    source_axis_tag,
                    target_axis_tag,
                    alternate_coordinates,
                ))
            else:
                print("%s: created alternate intermediate layer %s at %s" % (
                    master.name,
                    alternate_intermediate_name,
                    alternate_coordinates,
                ))
        else:
            alternate_intermediate_layer = replace_layer_contents(
                existing_alternate_intermediate,
                alternate_coordinates,
                target_axis_rules,
                master.id,
                high_source_alternate.width,
            )
            alternates_refreshed += 1
            if remapped_source_rule:
                print("%s: refreshed alternate intermediate layer %s with %s rule remapped to %s at %s" % (
                    master.name,
                    alternate_intermediate_name,
                    source_axis_tag,
                    target_axis_tag,
                    alternate_coordinates,
                ))
            else:
                print("%s: refreshed alternate intermediate layer %s at %s" % (
                    master.name,
                    alternate_intermediate_name,
                    alternate_coordinates,
                ))
        if remapped_source_rule:
            force_layer_rules_to_target_axis(
                alternate_intermediate_layer,
                source_axis_index,
                target_axis_index,
                source_axis_id,
                target_axis_id,
            )
            alternate_intermediate_layer.name = alternate_intermediate_name
        intermediate_coordinates_by_layer_id[alternate_intermediate_layer.layerId] = dict(alternate_coordinates)
        source_layers_by_target_layer_id[alternate_intermediate_layer.layerId] = high_source_alternate

    copied, copy_skipped = copy_source_layers_into_target(
        font,
        destination_glyph,
        source_glyph,
        source_axis_tag,
        source_axis_id,
        target_axis_id,
        source_low_value,
        source_high_value,
        intermediate_coordinates_by_layer_id,
        source_layers_by_target_layer_id,
    )
    layers_copied += copied
    copy_layers_skipped += copy_skipped

    print("%s summary: created %i, refreshed %i, alternate created %i, alternate refreshed %i, skipped %i" % (
        destination_glyph.name,
        created,
        refreshed,
        alternates_created,
        alternates_refreshed,
        skipped,
    ))

    return process_stats(
        created=created,
        refreshed=refreshed,
        skipped=skipped,
        layers_copied=layers_copied,
        copy_layers_skipped=copy_layers_skipped,
        alternates_created=alternates_created,
        alternates_refreshed=alternates_refreshed,
        modified=True,
    )


def process_stats(
    created=0,
    refreshed=0,
    skipped=0,
    layers_copied=0,
    copy_layers_skipped=0,
    alternates_created=0,
    alternates_refreshed=0,
    modified=False,
):
    return {
        "created": created,
        "refreshed": refreshed,
        "alternates_created": alternates_created,
        "alternates_refreshed": alternates_refreshed,
        "skipped": skipped,
        "layers_copied": layers_copied,
        "copy_layers_skipped": copy_layers_skipped,
        "modified": int(bool(modified)),
    }
