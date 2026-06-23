# -*- coding: utf-8 -*-

"""
Design-space axis rotation helpers for Glyphs 3.

The public function in this file samples a source glyph at interpolated
design-space locations and writes the results into a destination glyph while
moving the effect of one design axis onto another. The axis tags, axis values,
and glyphs are supplied by the caller; this file does not assume specific axis
names or fixed axis positions.
"""

import uuid
from GlyphsApp import GSLayer


DESIGNSPACE_AXIS_ROTATION_VERSION = "2026-06-22 20:13 CDT preserve-component-smart-values"


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

    coordinates = attribute_value(layer, "coordinates")
    if coordinates is None:
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
    coordinates = attribute_value(layer, "coordinates")
    if coordinates is None:
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


def coordinate_axis_value(font, coordinates, axis_id_value, axis_index_value):
    if coordinates is None:
        return None

    if hasattr(coordinates, "keys"):
        try:
            return float(coordinates[str(axis_id_value)])
        except Exception:
            return None

    values = coordinate_values(font, coordinates)
    if values is None:
        return None
    try:
        return float(values[axis_index_value])
    except Exception:
        return None


def layer_name(layer):
    value = getattr(layer, "name", "")
    if callable(value):
        try:
            value = value()
        except Exception:
            value = ""
    return str(value or "")


def layer_id(layer):
    value = getattr(layer, "layerId", None)
    if callable(value):
        try:
            value = value()
        except Exception:
            value = None
    if value is None:
        return None
    return str(value)


def is_master_layer(layer):
    value = getattr(layer, "isMasterLayer", False)
    if callable(value):
        try:
            value = value()
        except Exception:
            value = False
    return bool(value)


def glyph_has_layer_id(glyph, target_layer_id):
    if target_layer_id is None:
        return False
    for layer in glyph.layers:
        if layer_id(layer) == target_layer_id:
            return True
    return False


def attribute_value(layer, key):
    for attribute_proxy_name in ("attributes", "attr"):
        attributes = getattr(layer, attribute_proxy_name, None)
        if attributes:
            try:
                return attributes[key]
            except Exception:
                pass

    for method_name in ("attributeForKey_", "valueForKey_"):
        method = getattr(layer, method_name, None)
        if method is None:
            continue
        try:
            return method(key)
        except Exception:
            pass

    for attribute_proxy_name in ("attributes", "attr"):
        try:
            return getattr(layer, attribute_proxy_name)[key]
        except Exception:
            pass
    return None


def copied_attribute_value(value):
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return [copied_attribute_value(item) if hasattr(item, "keys") else item for item in value]
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

    for attribute_proxy_name in ("attributes", "attr"):
        attributes = getattr(layer, attribute_proxy_name, None)
        if attributes is None:
            continue
        try:
            attributes[key] = copied_value
            return
        except Exception:
            pass


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


AXIS_RULE_MAX_SAMPLE_OFFSET = 0.1
AXIS_RULE_MIN_SAMPLE_OFFSET = 0.01


def format_number(value):
    try:
        numeric_value = float(value)
    except Exception:
        return str(value)
    if numeric_value.is_integer():
        return str(int(numeric_value))
    return str(numeric_value)


def axis_label_for_rule(font, axis_key, fallback_index=None):
    axis_key = str(axis_key)
    for axis in font.axes:
        if axis_id(axis) == axis_key:
            label = axis_tag(axis)
            return label or axis_key
    if fallback_index is not None:
        try:
            label = axis_tag(font.axes[fallback_index])
            return label or axis_key
        except Exception:
            pass
    return axis_key


def axis_rule_entries(font, axis_rules):
    if axis_rules is None:
        return []

    entries = []
    if hasattr(axis_rules, "keys"):
        for axis_key in axis_rules.keys():
            entries.append((
                str(axis_key),
                axis_label_for_rule(font, axis_key),
                copied_axis_rule(axis_rules[axis_key]),
            ))
        return entries

    for index, rule in enumerate(axis_rule_items(axis_rules)):
        try:
            current_axis_id = axis_id(font.axes[index])
        except Exception:
            current_axis_id = None
        if current_axis_id is None:
            continue
        entries.append((
            str(current_axis_id),
            axis_label_for_rule(font, current_axis_id, index),
            copied_axis_rule(rule),
        ))
    return entries


def axis_rule_limit_values(rule):
    copied_rule = copied_axis_rule(rule)
    minimum = copied_rule.get("min")
    maximum = copied_rule.get("max")

    minimum_value = None
    maximum_value = None
    if minimum is not None:
        try:
            minimum_value = float(minimum)
        except Exception:
            minimum_value = None
    if maximum is not None:
        try:
            maximum_value = float(maximum)
        except Exception:
            maximum_value = None
    return minimum_value, maximum_value


def coordinate_is_inside_axis_rule(value, rule):
    try:
        value = float(value)
    except Exception:
        return False

    minimum_value, maximum_value = axis_rule_limit_values(rule)
    if minimum_value is not None and value <= minimum_value:
        return False
    if maximum_value is not None and value >= maximum_value:
        return False
    return True


def sample_value_inside_axis_rule(rule):
    minimum_value, maximum_value = axis_rule_limit_values(rule)
    if minimum_value is not None and maximum_value is not None:
        if minimum_value >= maximum_value:
            return None, None
        return (minimum_value + maximum_value) / 2.0, ">%s,<%s" % (
            format_number(minimum_value),
            format_number(maximum_value),
        )
    if maximum_value is not None:
        return maximum_value - AXIS_RULE_MAX_SAMPLE_OFFSET, "<%s" % format_number(maximum_value)
    if minimum_value is not None:
        return minimum_value + AXIS_RULE_MIN_SAMPLE_OFFSET, ">%s" % format_number(minimum_value)
    return None, None


def coordinates_inside_axis_rules(font, coordinates, axis_rules):
    if coordinates is None:
        return None, []

    adjusted_coordinates = {}
    try:
        for key in coordinates.keys():
            adjusted_coordinates[str(key)] = float(coordinates[key])
    except Exception:
        values = coordinate_values(font, coordinates)
        if values is None:
            return coordinates, []
        for index, value in enumerate(values):
            current_axis_id = axis_id(font.axes[index])
            if current_axis_id is not None:
                adjusted_coordinates[str(current_axis_id)] = float(value)

    notes = []
    for axis_key, axis_label, rule in axis_rule_entries(font, axis_rules):
        sample_value, rule_label = sample_value_inside_axis_rule(rule)
        if sample_value is None:
            continue
        current_value = adjusted_coordinates.get(str(axis_key))
        if current_value is not None and coordinate_is_inside_axis_rule(current_value, rule):
            notes.append("%s%s keep %s" % (
                axis_label,
                rule_label,
                format_number(current_value),
            ))
            continue
        adjusted_coordinates[str(axis_key)] = sample_value
        notes.append("%s%s -> %s" % (
            axis_label,
            rule_label,
            format_number(sample_value),
        ))

    return adjusted_coordinates, notes


def coordinates_dict_for_adjustment(font, coordinates):
    if coordinates is None:
        return None

    adjusted_coordinates = {}
    try:
        for key in coordinates.keys():
            adjusted_coordinates[str(key)] = float(coordinates[key])
        return adjusted_coordinates
    except Exception:
        pass

    values = coordinate_values(font, coordinates)
    if values is None:
        return None
    for index, value in enumerate(values):
        current_axis_id = axis_id(font.axes[index])
        if current_axis_id is not None:
            adjusted_coordinates[str(current_axis_id)] = float(value)
    return adjusted_coordinates


def sample_value_outside_axis_rule(value, rule):
    if not coordinate_is_inside_axis_rule(value, rule):
        return None, None

    minimum_value, maximum_value = axis_rule_limit_values(rule)
    if maximum_value is not None:
        return maximum_value + AXIS_RULE_MIN_SAMPLE_OFFSET, ">%s" % format_number(maximum_value)
    if minimum_value is not None:
        return minimum_value - AXIS_RULE_MAX_SAMPLE_OFFSET, "<%s" % format_number(minimum_value)
    return None, None


def coordinates_outside_axis_rules(font, coordinates, axis_rules_list):
    adjusted_coordinates = coordinates_dict_for_adjustment(font, coordinates)
    if adjusted_coordinates is None:
        return coordinates, []

    notes = []
    for axis_rules in axis_rules_list or []:
        for axis_key, axis_label, rule in axis_rule_entries(font, axis_rules):
            current_value = adjusted_coordinates.get(str(axis_key))
            if current_value is None:
                continue
            sample_value, rule_label = sample_value_outside_axis_rule(current_value, rule)
            if sample_value is None:
                continue
            adjusted_coordinates[str(axis_key)] = sample_value
            notes.append("%s%s -> %s" % (
                axis_label,
                rule_label,
                format_number(sample_value),
            ))

    return adjusted_coordinates, notes


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


def special_layer_shell(layer_id, name, coordinates, axis_rules, associated_master_id, width):
    layer = GSLayer()
    layer.layerId = layer_id
    layer.associatedMasterId = associated_master_id
    layer.name = name
    if coordinates is not None:
        set_layer_attribute(layer, "coordinates", coordinates)
    if axis_rules is not None:
        set_layer_axis_rules(layer, axis_rules)
    layer.width = width
    return layer


def layer_index(glyph, layer):
    return list(glyph.layers).index(layer)


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

        method = getattr(glyph.layers, "removeObjectForKey_", None)
        if method is not None:
            try:
                method(target_layer_id)
                if not glyph_has_layer_id(glyph, target_layer_id):
                    return True
            except Exception:
                pass

    try:
        index = layer_index(glyph, layer)
    except Exception:
        index = None

    if index is not None:
        try:
            del glyph.layers[index]
            if not glyph_has_layer_id(glyph, target_layer_id):
                return True
        except Exception:
            pass

    for index, existing_layer in reversed(list(enumerate(glyph.layers))):
        if layer_id(existing_layer) != target_layer_id:
            continue
        try:
            del glyph.layers[index]
            if not glyph_has_layer_id(glyph, target_layer_id):
                return True
        except Exception:
            pass

    return not glyph_has_layer_id(glyph, target_layer_id)


def delete_non_master_layers(glyph):
    removed = 0
    for layer in list(glyph.layers):
        if layer.isMasterLayer:
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
    seen = set()
    for layer in source_glyph.layers:
        if layer.isMasterLayer or has_coordinates_attribute(layer):
            continue
        if has_axis_rules_attribute(layer):
            key = (
                getattr(layer, "associatedMasterId", None),
                axis_rules_key(attribute_value(layer, "axisRules")),
            )
            if key in seen:
                continue
            seen.add(key)
            alternates.append(layer)
    return alternates


def source_alternate_layer_for_rules(source_glyph, associated_master_id, axis_rules):
    for layer in source_alternate_layers(source_glyph):
        if getattr(layer, "associatedMasterId", None) != associated_master_id:
            continue
        if axis_rules_match(attribute_value(layer, "axisRules"), axis_rules):
            return layer
    return None


def source_axis_rules_for_master(source_glyph, associated_master_id):
    axis_rules_list = []
    seen = set()
    for layer in source_alternate_layers(source_glyph):
        if getattr(layer, "associatedMasterId", None) != associated_master_id:
            continue
        axis_rules = attribute_value(layer, "axisRules")
        if axis_rules is None:
            continue
        key = axis_rules_key(axis_rules)
        if key in seen:
            continue
        seen.add(key)
        axis_rules_list.append(axis_rules)
    return axis_rules_list


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


def component_name_from_object(component):
    for attribute_name in ("componentName", "name"):
        value = getattr(component, attribute_name, None)
        if value:
            return str(value)
    return None


def set_component_name(component, component_name):
    did_set = False
    for attribute_name in ("componentName", "name"):
        if not hasattr(component, attribute_name):
            continue
        try:
            setattr(component, attribute_name, component_name)
            did_set = True
        except Exception:
            pass

    for method_name in ("setComponentName_", "setName_"):
        method = getattr(component, method_name, None)
        if method is None:
            continue
        try:
            method(component_name)
            did_set = True
        except Exception:
            pass
    return did_set


def boolean_attribute_value(object_value, attribute_name, default=False):
    value = getattr(object_value, attribute_name, default)
    if callable(value):
        try:
            value = value()
        except Exception:
            return default
    return bool(value)


def is_brace_layer(layer):
    if boolean_attribute_value(layer, "isBraceLayer", False):
        return True
    return bool(boolean_attribute_value(layer, "isSpecialLayer", False) and "{" in layer_name(layer) and "}" in layer_name(layer))


def is_bracket_layer(layer):
    if boolean_attribute_value(layer, "isBracketLayer", False):
        return True
    return bool(boolean_attribute_value(layer, "isSpecialLayer", False) and "[" in layer_name(layer) and "]" in layer_name(layer))


def is_axis_rule_layer(layer):
    return has_axis_rules_attribute(layer) or is_bracket_layer(layer)


def layer_has_same_name_and_master(glyph, source_layer):
    source_name = layer_name(source_layer)
    source_master_id = getattr(source_layer, "associatedMasterId", None)
    for layer in glyph.layers:
        if layer_name(layer) != source_name:
            continue
        if getattr(layer, "associatedMasterId", None) == source_master_id:
            return True
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


def copy_layer_attributes(source_layer, target_layer):
    copied_keys = set()
    for attribute_proxy_name in ("attributes", "attr"):
        attributes = getattr(source_layer, attribute_proxy_name, None)
        if not attributes:
            continue

        try:
            keys = list(attributes.keys())
        except Exception:
            keys = []

        for key in keys:
            if key in copied_keys:
                continue
            try:
                set_layer_attribute(target_layer, key, attributes[key])
                copied_keys.add(key)
            except Exception:
                pass


def call_layer_method(layer, method_name):
    method = getattr(layer, method_name, None)
    if method is None:
        return False
    try:
        method()
        return True
    except Exception:
        return False


def glyph_is_smart(glyph):
    method = getattr(glyph, "isSmartGlyph", None)
    if method is not None:
        try:
            return bool(method())
        except Exception:
            pass
    return False


def sync_component_alignment_from_master(master_layer, special_layer):
    try:
        master_components = list(master_layer.components)
        special_components = list(special_layer.components)
    except Exception:
        return

    for index, master_component in enumerate(master_components):
        try:
            special_component = special_components[index]
        except Exception:
            continue

        alignment = getattr(master_component, "alignment", None)
        method = getattr(special_component, "setAlignment_", None)
        if method is not None and alignment is not None:
            try:
                method(alignment)
            except Exception:
                pass

        method = getattr(special_component, "setIsAligned_", None)
        is_aligned = getattr(master_component, "isAligned", None)
        if method is not None and is_aligned is not None:
            try:
                method(is_aligned() if callable(is_aligned) else is_aligned)
            except Exception:
                pass


def component_mapping_value(component, key):
    value = getattr(component, key, None)
    if value:
        copied = copied_attribute_value(value)
        try:
            return dict(copied)
        except Exception:
            return copied

    method = getattr(component, "valueForKey_", None)
    if method is None:
        return None
    try:
        value = method(key)
    except Exception:
        return None
    if not value:
        return None
    copied = copied_attribute_value(value)
    try:
        return dict(copied)
    except Exception:
        return copied


def set_component_mapping_value(component, key, value):
    if value is None:
        return False

    copied_value = copied_attribute_value(value)
    did_set = False
    current_value = getattr(component, key, None)
    if hasattr(current_value, "keys"):
        try:
            for existing_key in list(current_value.keys()):
                try:
                    del current_value[existing_key]
                except Exception:
                    pass
            for value_key, value_item in copied_value.items():
                current_value[value_key] = value_item
            did_set = True
        except Exception:
            pass

    if not did_set and hasattr(component, key):
        try:
            setattr(component, key, copied_value)
            did_set = True
        except Exception:
            pass

    method = getattr(component, "setValue_forKey_", None)
    if method is not None:
        try:
            method(copied_value, key)
            did_set = True
        except Exception:
            pass

    return did_set


def copy_component_smart_values(reference_component, target_component):
    copied = 0
    for key in ("smartComponentValues", "piece"):
        value = component_mapping_value(reference_component, key)
        if value is not None and set_component_mapping_value(target_component, key, value):
            copied += 1
    return copied


def copy_layer_component_smart_values(reference_layer, target_layer):
    if reference_layer is None or target_layer is None:
        return 0

    try:
        reference_components = list(reference_layer.components)
        target_components = list(target_layer.components)
    except Exception:
        return 0

    copied = 0
    for index, reference_component in enumerate(reference_components):
        try:
            target_component = target_components[index]
        except Exception:
            continue

        reference_name = component_name_from_object(reference_component)
        target_name = component_name_from_object(target_component)
        if reference_name and target_name and reference_name != target_name:
            continue
        copied += copy_component_smart_values(reference_component, target_component)
    return copied


def add_component_special_layer_to_composite(font, composite_glyph, master_layer, component_special_layer):
    if layer_has_same_name_and_master(composite_glyph, component_special_layer):
        return None

    new_layer = GSLayer()
    new_layer.name = layer_name(component_special_layer)
    set_associated_master_id(new_layer, getattr(component_special_layer, "associatedMasterId", None))
    new_layer.width = component_special_layer.width
    copy_layer_attributes(component_special_layer, new_layer)

    composite_glyph.layers.append(new_layer)
    call_layer_method(new_layer, "reinterpolate")
    call_layer_method(new_layer, "reinterpolateMetrics")
    call_layer_method(new_layer, "syncMetrics")
    sync_component_alignment_from_master(master_layer, new_layer)
    copy_layer_component_smart_values(master_layer, new_layer)
    return new_layer


def add_component_special_layers_to_composite_source(font, composite_glyph):
    added = 0
    added_names = []
    master_layers = [layer for layer in composite_glyph.layers if is_master_layer(layer)]

    for master_layer in master_layers:
        try:
            components = list(master_layer.components)
        except Exception:
            components = []
        if not components:
            continue

        for component in components:
            component_name = component_name_from_object(component)
            if component_name is None:
                continue
            try:
                component_glyph = font.glyphs[component_name]
            except Exception:
                component_glyph = None
            if component_glyph is None:
                continue

            for component_layer in component_glyph.layers:
                if not (is_brace_layer(component_layer) or is_bracket_layer(component_layer)):
                    continue
                new_layer = add_component_special_layer_to_composite(
                    font,
                    composite_glyph,
                    master_layer,
                    component_layer,
                )
                if new_layer is None:
                    continue
                added += 1
                added_names.append(layer_name(new_layer) or layer_id(new_layer))

    return added, added_names


def prepared_composite_source_glyph(font, source_glyph):
    glyph_copy = source_glyph.copy()
    glyph_copy.name = "__tmp_composite_source_%s_%s" % (source_glyph.name, str(uuid.uuid4()).replace("-", ""))
    try:
        glyph_copy.export = False
    except Exception:
        pass

    font.glyphs.append(glyph_copy)
    added, added_names = add_component_special_layers_to_composite_source(font, glyph_copy)
    if added:
        print("%s: prepared temporary composite source with %i component brace/bracket layer(s): %s" % (
            source_glyph.name,
            added,
            ", ".join(added_names),
        ))
    else:
        print("%s: temporary composite source needed no component brace/bracket layers" % source_glyph.name)
    return glyph_copy, added


def remove_axis_rule_layers(glyph):
    removed = 0
    for layer in list(glyph.layers):
        if is_master_layer(layer):
            continue
        if not is_axis_rule_layer(layer):
            continue
        if remove_layer(glyph, layer):
            removed += 1
    return removed


def iter_layer_components(layer):
    seen = set()
    for proxy_name in ("components", "shapes"):
        try:
            values = list(getattr(layer, proxy_name))
        except Exception:
            values = []
        for value in values:
            if component_name_from_object(value) is None:
                continue
            identity = id(value)
            if identity in seen:
                continue
            seen.add(identity)
            yield value


def clone_plain_component_glyph(font, component_name, clone_names, temp_component_glyphs, removed_rule_layers, rewritten_references):
    if component_name in clone_names:
        return clone_names[component_name]

    try:
        component_glyph = font.glyphs[component_name]
    except Exception:
        component_glyph = None
    if component_glyph is None:
        return None

    glyph_copy = component_glyph.copy()
    glyph_copy.name = "__tmp_plain_component_%s_%s" % (
        component_glyph.name,
        str(uuid.uuid4()).replace("-", ""),
    )
    try:
        glyph_copy.export = False
    except Exception:
        pass

    font.glyphs.append(glyph_copy)
    temp_component_glyphs.append(glyph_copy)
    clone_names[component_name] = glyph_copy.name

    removed_rule_layers[0] += remove_axis_rule_layers(glyph_copy)
    rewrite_plain_component_references(font, glyph_copy, clone_names, temp_component_glyphs, removed_rule_layers, rewritten_references)
    return glyph_copy.name


def rewrite_plain_component_references(font, glyph, clone_names, temp_component_glyphs, removed_rule_layers, rewritten_references):
    for layer in glyph.layers:
        for component in iter_layer_components(layer):
            component_name = component_name_from_object(component)
            if component_name is None:
                continue
            replacement_name = clone_plain_component_glyph(
                font,
                component_name,
                clone_names,
                temp_component_glyphs,
                removed_rule_layers,
                rewritten_references,
            )
            if replacement_name is not None and replacement_name != component_name:
                if set_component_name(component, replacement_name):
                    rewritten_references[0] += 1
                else:
                    print_warning("%s: could not repoint component %s to temporary plain copy %s" % (
                        glyph.name,
                        component_name,
                        replacement_name,
                    ))


def prepared_plain_source_glyph(font, source_glyph):
    glyph_copy = source_glyph.copy()
    glyph_copy.name = "__tmp_plain_source_%s_%s" % (source_glyph.name, str(uuid.uuid4()).replace("-", ""))
    try:
        glyph_copy.export = False
    except Exception:
        pass

    font.glyphs.append(glyph_copy)

    removed = remove_axis_rule_layers(glyph_copy)
    temp_component_glyphs = []
    clone_names = {}
    component_rule_layers_removed = [0]
    rewritten_references = [0]
    rewrite_plain_component_references(
        font,
        glyph_copy,
        clone_names,
        temp_component_glyphs,
        component_rule_layers_removed,
        rewritten_references,
    )

    print("%s: prepared temporary plain source with %i source axis-rule layer(s), %i temporary component copy/copies, %i component reference(s) repointed, and %i component axis-rule layer(s) removed" % (
        source_glyph.name,
        removed,
        len(temp_component_glyphs),
        rewritten_references[0],
        component_rule_layers_removed[0],
    ))
    return glyph_copy, temp_component_glyphs


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


def shape_count(layer):
    try:
        return len(layer.shapes)
    except Exception:
        return 0


def anchor_count(layer):
    try:
        return len(layer.anchors)
    except Exception:
        return 0


def callable_attribute_value(object_value, attribute_name, default=None):
    value = getattr(object_value, attribute_name, default)
    if callable(value):
        try:
            return value()
        except Exception:
            return default
    return value


def node_signature(node):
    node_type = callable_attribute_value(node, "type", "")
    smooth = callable_attribute_value(node, "smooth", False)
    if smooth:
        return "%ss" % node_type
    return str(node_type)


def shape_signature(shape):
    try:
        nodes = list(shape.nodes)
    except Exception:
        nodes = None

    if nodes is not None:
        closed = callable_attribute_value(shape, "closed", None)
        if closed is None:
            closed = callable_attribute_value(shape, "isClosed", None)
        direction = callable_attribute_value(shape, "direction", "")
        return (
            "path",
            bool(closed),
            str(direction),
            tuple(node_signature(node) for node in nodes),
        )

    component_name = component_name_from_object(shape)
    if component_name is not None:
        return ("component", component_name)

    return ("shape", shape.__class__.__name__)


def layer_outline_signature(layer):
    try:
        shapes = list(layer.shapes)
    except Exception:
        shapes = []
    return tuple(shape_signature(shape) for shape in shapes)


def format_shape_signature(signature):
    parts = []
    for index, item in enumerate(signature):
        if not item:
            parts.append("s%i:empty" % index)
            continue
        if item[0] == "path":
            _, closed, direction, node_types = item
            parts.append("p%i:%s:dir=%s:n=%i:%s" % (
                index,
                "closed" if closed else "open",
                direction,
                len(node_types),
                "/".join(node_types),
            ))
        elif item[0] == "component":
            parts.append("c%i:%s" % (index, item[1]))
        else:
            parts.append("s%i:%s" % (index, item[-1]))
    return "; ".join(parts)


def compatibility_group_key(layer):
    axis_rules = attribute_value(layer, "axisRules")
    if axis_rules is None:
        return ("default",)
    return ("rules", axis_rules_key(axis_rules))


def compatibility_group_label(group_key):
    if group_key == ("default",):
        return "default/no axisRules"
    return str(group_key[1])


def report_outline_compatibility(glyph):
    groups = {}
    for layer in glyph.layers:
        signature = layer_outline_signature(layer)
        if not signature:
            continue
        groups.setdefault(compatibility_group_key(layer), []).append((layer, signature))

    for group_key in sorted(groups.keys(), key=lambda key: str(key)):
        records = groups[group_key]
        if len(records) < 2:
            continue
        reference_layer, reference_signature = records[0]
        mismatches = [
            (layer, signature)
            for layer, signature in records[1:]
            if signature != reference_signature
        ]
        if not mismatches:
            print("%s: compatibility signatures match for %s (%i layers)" % (
                glyph.name,
                compatibility_group_label(group_key),
                len(records),
            ))
            continue

        print_warning("%s: compatibility signature mismatch in %s" % (
            glyph.name,
            compatibility_group_label(group_key),
        ))
        print("  Reference %s: %s" % (
            layer_name(reference_layer) or layer_id(reference_layer),
            format_shape_signature(reference_signature),
        ))
        for layer, signature in mismatches:
            print("  Differs %s: %s" % (
                layer_name(layer) or layer_id(layer),
                format_shape_signature(signature),
            ))


def interpolated_source_layer_copy(
    source_glyph,
    coordinates,
    axis_rules,
    associated_master_id,
    name,
    reference_layer=None,
):
    interpolation_layer = special_layer_shell(
        str(uuid.uuid4()).upper(),
        name,
        coordinates,
        axis_rules,
        associated_master_id,
        0,
    )
    source_glyph.layers.append(interpolation_layer)
    try:
        call_layer_method(interpolation_layer, "reinterpolate")
        call_layer_method(interpolation_layer, "reinterpolateMetrics")
        call_layer_method(interpolation_layer, "syncMetrics")
        copy_layer_component_smart_values(reference_layer, interpolation_layer)
        decompose_interpolated_layer(interpolation_layer)
        return interpolation_layer.copy()
    finally:
        remove_layer(source_glyph, interpolation_layer)


def decompose_remaining_components(layer):
    changed = call_layer_method(layer, "decomposeComponents")
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
        if call_layer_method(layer, method_name):
            changed = True
    return changed


def decompose_interpolated_layer(layer):
    previous_state = None
    for _ in range(10):
        before = (count_components(layer), count_helper_hints(layer), shape_count(layer))
        decompose_remaining_components(layer)
        decompose_layer_helpers(layer)
        after = (count_components(layer), count_helper_hints(layer), shape_count(layer))
        if after == before or after == previous_state:
            break
        previous_state = before


def copy_metric_attribute(source_layer, target_layer, attribute_name):
    if not hasattr(source_layer, attribute_name) or not hasattr(target_layer, attribute_name):
        return
    try:
        setattr(target_layer, attribute_name, getattr(source_layer, attribute_name))
    except Exception:
        pass


def copy_interpolated_layer_contents(
    font,
    source_glyph,
    coordinates,
    axis_rules,
    avoid_axis_rules_list,
    associated_master_id,
    source_label,
    target_layer,
    reference_layer=None,
):
    if axis_rules is not None:
        sample_coordinates, axis_rule_notes = coordinates_inside_axis_rules(font, coordinates, axis_rules)
    else:
        sample_coordinates, axis_rule_notes = coordinates_outside_axis_rules(font, coordinates, avoid_axis_rules_list)
    source_copy = interpolated_source_layer_copy(
        source_glyph,
        sample_coordinates,
        axis_rules,
        associated_master_id,
        "__tmp_interpolate_%s" % source_glyph.name,
        reference_layer,
    )

    clear_proxy(target_layer.shapes)
    clear_proxy(target_layer.anchors)
    if hasattr(target_layer, "hints"):
        clear_proxy(target_layer.hints)

    for shape in source_copy.shapes:
        target_layer.shapes.append(shape.copy())
    for anchor in source_copy.anchors:
        target_layer.anchors.append(anchor.copy())
    if hasattr(source_copy, "hints") and hasattr(target_layer, "hints"):
        for hint in source_copy.hints:
            target_layer.hints.append(hint.copy())

    stem_count = copy_stems(source_copy, target_layer)
    target_layer.width = source_copy.width
    for attribute_name in ("leftMetricsKey", "rightMetricsKey", "widthMetricsKey"):
        copy_metric_attribute(source_copy, target_layer, attribute_name)

    return (
        shape_count(source_copy),
        anchor_count(source_copy),
        count_components(source_copy),
        count_helper_hints(source_copy),
        stem_count,
        source_label,
        sample_coordinates,
        axis_rule_notes,
    )


def source_sample_for_target_layer(
    font,
    target_layer,
    source_axis_id,
    target_axis_id,
    source_low_value,
    source_high_value,
    intermediate_coordinates_by_layer_id,
):
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
        return None, source_axis_value

    source_coordinates = master_coordinates(font, source_master)
    if source_coordinates is None:
        return None, source_axis_value

    return dict(
        coordinates=source_coordinates,
        axis_rules=None,
        associated_master_id=source_master.id,
        label=source_master.name,
    ), source_axis_value


def copy_source_samples_into_target(
    font,
    glyph,
    plain_source_glyph,
    rule_source_glyph,
    source_axis_tag,
    source_axis_id,
    target_axis_id,
    source_low_value,
    source_high_value,
    intermediate_coordinates_by_layer_id,
    source_samples_by_target_layer_id,
):
    copied = 0
    skipped = 0

    for layer in glyph.layers:
        sample = source_samples_by_target_layer_id.get(layer.layerId)
        source_axis_value = None
        if sample is None:
            if attribute_value(layer, "axisRules") is not None:
                continue
            sample, source_axis_value = source_sample_for_target_layer(
                font,
                layer,
                source_axis_id,
                target_axis_id,
                source_low_value,
                source_high_value,
                intermediate_coordinates_by_layer_id,
            )

        if sample is None:
            skipped += 1
            print_warning("%s: could not find source interpolation sample for %s=%s" % (
                layer.name or layer.layerId,
                source_axis_tag,
                source_axis_value,
            ))
            continue

        # Use the composite-aware source for both sides. Default/no-rule
        # samples are nudged outside source bracket rules below, so the source
        # can keep smart-component brace/bracket information intact.
        sample_source_glyph = rule_source_glyph
        reference_layer = sample.get("reference_layer")
        if sample.get("axis_rules") is None and "avoid_axis_rules" not in sample:
            sample["avoid_axis_rules"] = source_axis_rules_for_master(
                rule_source_glyph,
                sample.get("associated_master_id"),
            )
        if reference_layer is None and sample.get("associated_master_id"):
            try:
                reference_layer = sample_source_glyph.layers[sample.get("associated_master_id")]
            except Exception:
                reference_layer = None

        shape_total, anchor_total, remaining_components, remaining_helpers, stem_count, source_label, sample_coordinates, axis_rule_notes = copy_interpolated_layer_contents(
            font,
            sample_source_glyph,
            sample["coordinates"],
            sample.get("axis_rules"),
            sample.get("avoid_axis_rules"),
            sample.get("associated_master_id"),
            sample.get("label"),
            layer,
            reference_layer,
        )
        copied += 1
        axis_rule_note = ""
        if axis_rule_notes:
            axis_rule_note = "; axis-rule sample %s" % ", ".join(axis_rule_notes)
        print("%s: interpolated %s at %s from %s (%i shapes, %i anchors, %i stems, target width %s%s; remaining components %i, helpers %i)" % (
            layer.name or layer.layerId,
            sample_source_glyph.name,
            sample_coordinates,
            source_label,
            shape_total,
            anchor_total,
            stem_count,
            layer.width,
            axis_rule_note,
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
    fixed_target_axis_value,
    source_samples_by_target_layer_id,
):
    created = 0
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

        target_axis_value = float(fixed_target_axis_value)

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
            source_samples_by_target_layer_id[destination_layer.layerId] = dict(
                coordinates=source_coordinates,
                axis_rules=source_axis_rules,
                associated_master_id=getattr(source_layer, "associatedMasterId", master.id),
                label=source_layer.name or source_layer.layerId,
                reference_layer=source_layer,
            )
            print("%s: created rotated coordinate layer %s from source %s at %s" % (
                master.name,
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

    return created, 0, skipped


def rotate_glyph_designspace_from_source(
    font,
    source_glyph,
    destination_glyph,
    source_axis_tag,
    target_axis_tag,
    source_low_value,
    source_high_value,
    target_axis_value,
    rule_source_glyph=None,
):
    if rule_source_glyph is None:
        rule_source_glyph = source_glyph

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
    non_master_layers_removed = delete_non_master_layers(destination_glyph)
    created = 0
    refreshed = 0
    alternates_created = 0
    alternates_refreshed = 0
    skipped = 0
    layers_copied = 0
    copy_layers_skipped = 0
    intermediate_coordinates_by_layer_id = {}
    source_samples_by_target_layer_id = {}

    print("")
    print("[%s]" % destination_glyph.name)
    if non_master_layers_removed:
        print("%s: deleted %i non-master layer(s) before rebuilding" % (
            destination_glyph.name,
            non_master_layers_removed,
        ))

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

    coord_created, coord_refreshed, coord_skipped = create_rotated_source_coordinate_layers(
        font,
        rule_source_glyph,
        destination_glyph,
        source_axis_tag,
        target_axis_tag,
        source_axis_id,
        target_axis_id,
        source_axis_index,
        target_axis_index,
        target_axis_value,
        source_samples_by_target_layer_id,
    )
    created += coord_created
    refreshed += coord_refreshed
    skipped += coord_skipped

    for source_alternate_layer in source_alternate_layers(rule_source_glyph):
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
            low_source_alternate = source_alternate_layer_for_rules(rule_source_glyph, low_source_master.id, axis_rules)
        if high_source_master is not None:
            high_source_alternate = source_alternate_layer_for_rules(rule_source_glyph, high_source_master.id, axis_rules)

        if low_source_alternate is None or high_source_alternate is None:
            skipped += 1
            print_warning("%s: skipped alternate for %s, could not find matching low/high source alternates" % (
                destination_glyph.name,
                master.name,
            ))
            continue

        low_source_coordinates = master_coordinates(font, low_source_master)
        high_source_coordinates = master_coordinates(font, high_source_master)
        if low_source_coordinates is None or high_source_coordinates is None:
            skipped += 1
            print_warning("%s: skipped alternate for %s, could not read low/high source coordinates" % (
                destination_glyph.name,
                master.name,
            ))
            continue

        alternate_name = alternate_rules_name(master, target_axis_rules, font)
        # The remapped rule layer still lives under the low/source master; only
        # its companion coordinate layer at the target-axis value uses high.
        alternate_source_layer = low_source_alternate
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
        if remapped_source_rule:
            force_layer_rules_to_target_axis(
                alternate_layer,
                source_axis_index,
                target_axis_index,
                source_axis_id,
                target_axis_id,
            )
            alternate_layer.name = alternate_name
        source_samples_by_target_layer_id[alternate_layer.layerId] = dict(
            coordinates=low_source_coordinates,
            axis_rules=axis_rules,
            associated_master_id=low_source_master.id,
            label=alternate_source_layer.name or alternate_source_layer.layerId,
            reference_layer=alternate_source_layer,
        )
        print("%s: queued alternate layer %s to interpolate from %s" % (
            master.name,
            alternate_layer.name or alternate_layer.layerId,
            alternate_source_layer.name or alternate_source_layer.layerId,
        ))

        alternate_coordinates = dict(master_coords)
        alternate_coordinates[str(target_axis_id)] = float(target_axis_value)
        alternate_intermediate_name = "%s %s %s" % (alternate_name, target_axis_tag, target_axis_value)
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
        source_samples_by_target_layer_id[alternate_intermediate_layer.layerId] = dict(
            coordinates=high_source_coordinates,
            axis_rules=axis_rules,
            associated_master_id=high_source_master.id,
            label=high_source_alternate.name or high_source_alternate.layerId,
            reference_layer=high_source_alternate,
        )
        print("%s: queued alternate intermediate layer %s to interpolate from %s" % (
            master.name,
            alternate_intermediate_layer.name or alternate_intermediate_layer.layerId,
            high_source_alternate.name or high_source_alternate.layerId,
        ))

    copied, copy_skipped = copy_source_samples_into_target(
        font,
        destination_glyph,
        source_glyph,
        rule_source_glyph,
        source_axis_tag,
        source_axis_id,
        target_axis_id,
        source_low_value,
        source_high_value,
        intermediate_coordinates_by_layer_id,
        source_samples_by_target_layer_id,
    )
    layers_copied += copied
    copy_layers_skipped += copy_skipped

    report_outline_compatibility(destination_glyph)

    print("%s summary: deleted non-master %i, created %i, refreshed %i, alternate created %i, alternate refreshed %i, skipped %i" % (
        destination_glyph.name,
        non_master_layers_removed,
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
        stale_layers_removed=non_master_layers_removed,
        modified=True,
    )


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
    plain_source_glyph = None
    plain_component_glyphs = []
    prepared_source_glyph = None
    try:
        plain_source_glyph, plain_component_glyphs = prepared_plain_source_glyph(font, source_glyph)
        prepared_source_glyph, _ = prepared_composite_source_glyph(font, source_glyph)
        return rotate_glyph_designspace_from_source(
            font,
            plain_source_glyph,
            destination_glyph,
            source_axis_tag,
            target_axis_tag,
            source_low_value,
            source_high_value,
            target_axis_value,
            rule_source_glyph=prepared_source_glyph,
        )
    finally:
        if prepared_source_glyph is not None:
            remove_temp_glyph(font, prepared_source_glyph)
        if plain_source_glyph is not None:
            remove_temp_glyph(font, plain_source_glyph)
        for plain_component_glyph in plain_component_glyphs:
            remove_temp_glyph(font, plain_component_glyph)


def process_stats(
    created=0,
    refreshed=0,
    skipped=0,
    layers_copied=0,
    copy_layers_skipped=0,
    alternates_created=0,
    alternates_refreshed=0,
    stale_layers_removed=0,
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
        "stale_layers_removed": stale_layers_removed,
        "modified": int(bool(modified)),
    }
