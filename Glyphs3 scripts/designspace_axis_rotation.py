# -*- coding: utf-8 -*-

"""
Design-space axis rotation helpers for Glyphs 3.

This helper rebuilds a target glyph from a source glyph by sampling the source
at explicit design-space locations. The source axis is read from the source
glyph and written into the target axis in the destination glyph.
"""

import uuid
from GlyphsApp import GSLayer


DESIGNSPACE_AXIS_ROTATION_VERSION = "2026-06-22 23:01 CDT exact-max-rule-sampling"

INSIDE_MAX_RULE_OFFSET = 0.0
INSIDE_MIN_RULE_OFFSET = 0.01
OUTSIDE_MAX_RULE_OFFSET = 0.0
OUTSIDE_MIN_RULE_OFFSET = 0.1
VERBOSE_DIAGNOSTICS = False


def print_warning(message):
    print("WARNING: %s" % message)


def diagnostic(message):
    if VERBOSE_DIAGNOSTICS:
        print("DIAG: %s" % message)


def safe_call(value, default=None):
    if callable(value):
        try:
            return value()
        except Exception:
            return default
    return value


def axis_tag(axis):
    for attribute_name in ("tag", "axisTag"):
        value = safe_call(getattr(axis, attribute_name, None))
        if value:
            return str(value)
    return ""


def axis_id(axis):
    for attribute_name in ("axisId", "id"):
        value = safe_call(getattr(axis, attribute_name, None))
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


def layer_name(layer):
    return str(safe_call(getattr(layer, "name", ""), "") or "")


def layer_id(layer):
    value = safe_call(getattr(layer, "layerId", None))
    if value is None:
        return None
    return str(value)


def is_master_layer(layer):
    return bool(safe_call(getattr(layer, "isMasterLayer", False), False))


def bool_method_or_attribute(obj, name):
    return bool(safe_call(getattr(obj, name, False), False))


def master_for_id(font, master_id):
    for master in font.masters:
        if master.id == master_id:
            return master
    return None


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


def copied_value(value):
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return [copied_value(item) for item in value]
    if hasattr(value, "keys"):
        copied = {}
        try:
            keys = list(value.keys())
        except Exception:
            keys = []
        for key in keys:
            try:
                copied[key] = copied_value(value[key])
            except Exception:
                pass
        return copied
    try:
        return value.copy()
    except Exception:
        pass
    try:
        return list(value)
    except Exception:
        return value


def short_value(value, max_length=180):
    if value is None:
        return "None"
    try:
        value = copied_value(value)
    except Exception:
        pass
    try:
        text = repr(value)
    except Exception:
        text = "<%s>" % value.__class__.__name__
    if len(text) > max_length:
        return text[:max_length - 3] + "..."
    return text


def proxy_keys(proxy):
    if proxy is None:
        return []
    try:
        return [str(key) for key in proxy.keys()]
    except Exception:
        return []


def raw_attribute_sources(layer, key):
    sources = []
    sentinel = object()

    try:
        direct_value = safe_call(getattr(layer, key, sentinel), sentinel)
    except Exception as error:
        sources.append("direct:error:%s" % error)
    else:
        if direct_value is sentinel:
            sources.append("direct:missing")
        elif direct_value is None:
            sources.append("direct:None")
        else:
            sources.append("direct:%s" % short_value(direct_value))

    for proxy_name in ("attributes", "attr"):
        try:
            proxy = getattr(layer, proxy_name, None)
        except Exception as error:
            sources.append("%s:error:%s" % (proxy_name, error))
            continue
        keys = proxy_keys(proxy)
        if not keys:
            sources.append("%s:keys=[]" % proxy_name)
        else:
            sources.append("%s:keys=%s" % (proxy_name, ",".join(keys)))
        try:
            value = proxy[key]
        except Exception:
            sources.append("%s[%s]:missing" % (proxy_name, key))
        else:
            sources.append("%s[%s]:%s" % (proxy_name, key, short_value(value)))

    for method_name in ("attributeForKey_", "valueForKey_"):
        method = getattr(layer, method_name, None)
        if method is None:
            sources.append("%s:missing" % method_name)
            continue
        try:
            value = method(key)
        except Exception as error:
            sources.append("%s:%s:error:%s" % (method_name, key, error))
        else:
            sources.append("%s:%s:%s" % (method_name, key, short_value(value)))

    return " | ".join(sources)


def attribute_value(layer, key):
    sentinel = object()
    direct_value = safe_call(getattr(layer, key, sentinel), sentinel)
    if direct_value is not sentinel and direct_value is not None:
        return direct_value

    for proxy_name in ("attributes", "attr"):
        attributes = getattr(layer, proxy_name, None)
        if not attributes:
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
                try:
                    values.append(float(coordinates[current_axis_id]))
                except Exception:
                    return None
        return values

    values = []
    try:
        iterator = list(coordinates)
    except Exception:
        return None
    for value in iterator:
        try:
            values.append(float(value))
        except Exception:
            return None
    return values


def coordinates_dict(font, coordinates):
    if coordinates is None:
        return None
    if hasattr(coordinates, "keys"):
        result = {}
        for axis in font.axes:
            current_axis_id = axis_id(axis)
            if current_axis_id is None:
                return None
            try:
                result[str(current_axis_id)] = float(coordinates[str(current_axis_id)])
            except Exception:
                try:
                    result[str(current_axis_id)] = float(coordinates[current_axis_id])
                except Exception:
                    return None
        return result

    values = coordinate_values(font, coordinates)
    if values is None or len(values) != len(font.axes):
        return None
    result = {}
    for index, axis in enumerate(font.axes):
        current_axis_id = axis_id(axis)
        if current_axis_id is None:
            return None
        result[str(current_axis_id)] = float(values[index])
    return result


def coordinates_for_layer(font, layer):
    if is_master_layer(layer):
        master = master_for_id(font, layer_id(layer))
        if master is None:
            return None
        return master_coordinates(font, master)
    return coordinates_dict(font, attribute_value(layer, "coordinates"))


def coordinates_match_except_axes(font, first_coordinates, second_coordinates, ignored_axis_ids):
    first_coordinates = coordinates_dict(font, first_coordinates)
    second_coordinates = coordinates_dict(font, second_coordinates)
    if first_coordinates is None or second_coordinates is None:
        return False
    ignored_axis_ids = set(str(item) for item in ignored_axis_ids)
    for axis in font.axes:
        current_axis_id = axis_id(axis)
        if current_axis_id is None or str(current_axis_id) in ignored_axis_ids:
            continue
        if abs(first_coordinates[str(current_axis_id)] - second_coordinates[str(current_axis_id)]) > 0.001:
            return False
    return True


def coordinates_match(font, first_coordinates, second_coordinates):
    return coordinates_match_except_axes(font, first_coordinates, second_coordinates, [])


def master_for_coordinates(font, coordinates):
    for master in font.masters:
        master_coords = master_coordinates(font, master)
        if master_coords is not None and coordinates_match(font, master_coords, coordinates):
            return master
    return None


def corresponding_master_for_axis_value(font, coordinates, source_axis_id, target_axis_id, source_axis_value):
    coordinates = coordinates_dict(font, coordinates)
    if coordinates is None:
        return None
    wanted_coordinates = dict(coordinates)
    wanted_coordinates[str(source_axis_id)] = float(source_axis_value)
    for master in font.masters:
        master_coords = master_coordinates(font, master)
        if master_coords is None:
            continue
        if coordinates_match_except_axes(font, master_coords, wanted_coordinates, [target_axis_id]):
            return master
    return None


def call_layer_method(layer, method_name):
    method = getattr(layer, method_name, None)
    if method is None:
        return False
    try:
        method()
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


def glyph_layer_for_id(glyph, target_layer_id):
    if target_layer_id is None:
        return None
    try:
        layer = glyph.layers[target_layer_id]
    except Exception:
        layer = None
    if layer is not None:
        return layer
    for layer in glyph.layers:
        if layer_id(layer) == target_layer_id:
            return layer
    return None


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
        del glyph.layers[layer_index(glyph, layer)]
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
        if is_master_layer(layer):
            continue
        if remove_layer(glyph, layer):
            removed += 1
    return removed


def clear_proxy(proxy):
    try:
        proxy.clear()
        return
    except Exception:
        pass
    while len(proxy):
        try:
            proxy.remove(proxy[-1])
        except Exception:
            break


def copy_layer_attributes(source_layer, target_layer):
    copied_keys = set()
    for proxy_name in ("attributes", "attr"):
        attributes = getattr(source_layer, proxy_name, None)
        if not attributes:
            continue
        try:
            keys = list(attributes.keys())
        except Exception:
            keys = []
        for key in keys:
            if key in copied_keys:
                continue
            if set_layer_attribute(target_layer, key, attributes[key]):
                copied_keys.add(key)


def copy_metric_attribute(source_layer, target_layer, attribute_name):
    if not hasattr(source_layer, attribute_name) or not hasattr(target_layer, attribute_name):
        return
    try:
        setattr(target_layer, attribute_name, getattr(source_layer, attribute_name))
    except Exception:
        pass


def copy_stems(source_layer, target_layer):
    if not hasattr(source_layer, "stems") or not hasattr(target_layer, "stems"):
        return 0
    try:
        target_layer.stems = [stem.copy() for stem in source_layer.stems]
    except Exception:
        try:
            target_layer.stems = source_layer.stems.copy()
        except Exception:
            return 0
    try:
        return len(target_layer.stems)
    except Exception:
        return 0


def set_layer_axis_rules(layer, axis_rules):
    return set_layer_attribute(layer, "axisRules", axis_rules)


def has_coordinates_attribute(layer):
    return attribute_value(layer, "coordinates") is not None


def has_axis_rules_attribute(layer):
    return attribute_value(layer, "axisRules") is not None


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
        copied = {}
        try:
            keys = list(rule.keys())
        except Exception:
            keys = []
        for key in keys:
            try:
                copied[key] = rule[key]
            except Exception:
                pass
        return copied
    try:
        return dict(rule)
    except Exception:
        return {}


def axis_rules_key(axis_rules):
    if axis_rules is None:
        return None
    if hasattr(axis_rules, "keys"):
        rules = {}
        try:
            keys = list(axis_rules.keys())
        except Exception:
            keys = []
        for key in keys:
            rule = copied_axis_rule(axis_rules[key])
            rules[str(key)] = (rule.get("min"), rule.get("max"))
        return tuple((key, rules[key][0], rules[key][1]) for key in sorted(rules.keys()))

    key = []
    for rule in axis_rule_items(axis_rules):
        copied_rule = copied_axis_rule(rule)
        key.append((copied_rule.get("min"), copied_rule.get("max")))
    return tuple(key)


def axis_rules_match(first_axis_rules, second_axis_rules):
    return axis_rules_key(first_axis_rules) == axis_rules_key(second_axis_rules)


def axis_rule_has_limits(rule):
    if rule is None:
        return False
    copied_rule = copied_axis_rule(rule)
    return "min" in copied_rule or "max" in copied_rule


def axis_rule_limits(rule):
    copied_rule = copied_axis_rule(rule)
    minimum = copied_rule.get("min")
    maximum = copied_rule.get("max")
    try:
        minimum = float(minimum) if minimum is not None else None
    except Exception:
        minimum = None
    try:
        maximum = float(maximum) if maximum is not None else None
    except Exception:
        maximum = None
    return minimum, maximum


def coordinate_is_inside_axis_rule(value, rule):
    try:
        value = float(value)
    except Exception:
        return False
    minimum, maximum = axis_rule_limits(rule)
    if minimum is not None and value <= minimum:
        return False
    if maximum is not None and value >= maximum:
        return False
    return True


def format_number(value):
    try:
        number = float(value)
    except Exception:
        return str(value)
    if number.is_integer():
        return str(int(number))
    return str(number)


def axis_label(font, axis_key, fallback_index=None):
    axis_key = str(axis_key)
    for axis in font.axes:
        if axis_id(axis) == axis_key:
            return axis_tag(axis) or axis_key
    if fallback_index is not None:
        try:
            return axis_tag(font.axes[fallback_index]) or axis_key
        except Exception:
            pass
    return axis_key


def axis_rule_entries(font, axis_rules):
    if axis_rules is None:
        return []
    if hasattr(axis_rules, "keys"):
        entries = []
        try:
            keys = list(axis_rules.keys())
        except Exception:
            keys = []
        for key in keys:
            entries.append((str(key), axis_label(font, key), copied_axis_rule(axis_rules[key])))
        return entries

    entries = []
    for index, rule in enumerate(axis_rule_items(axis_rules)):
        try:
            current_axis_id = axis_id(font.axes[index])
        except Exception:
            current_axis_id = None
        if current_axis_id is not None:
            entries.append((str(current_axis_id), axis_label(font, current_axis_id, index), copied_axis_rule(rule)))
    return entries


def inside_value_for_rule(rule):
    minimum, maximum = axis_rule_limits(rule)
    if minimum is not None and maximum is not None:
        if minimum >= maximum:
            return None, None
        return (minimum + maximum) / 2.0, ">%s,<%s" % (format_number(minimum), format_number(maximum))
    if maximum is not None:
        return maximum - INSIDE_MAX_RULE_OFFSET, "<%s" % format_number(maximum)
    if minimum is not None:
        return minimum + INSIDE_MIN_RULE_OFFSET, ">%s" % format_number(minimum)
    return None, None


def outside_value_for_rule(value, rule):
    if not coordinate_is_inside_axis_rule(value, rule):
        return None, None
    minimum, maximum = axis_rule_limits(rule)
    if maximum is not None:
        return maximum + OUTSIDE_MAX_RULE_OFFSET, ">%s" % format_number(maximum)
    if minimum is not None:
        return minimum - OUTSIDE_MIN_RULE_OFFSET, "<%s" % format_number(minimum)
    return None, None


def coordinates_inside_axis_rules(font, coordinates, axis_rules):
    adjusted = coordinates_dict(font, coordinates)
    if adjusted is None:
        return coordinates, []
    notes = []
    for axis_key, label, rule in axis_rule_entries(font, axis_rules):
        sample_value, rule_label = inside_value_for_rule(rule)
        if sample_value is None:
            continue
        current_value = adjusted.get(str(axis_key))
        if current_value is not None and coordinate_is_inside_axis_rule(current_value, rule):
            notes.append("%s%s keep %s" % (label, rule_label, format_number(current_value)))
            continue
        adjusted[str(axis_key)] = sample_value
        notes.append("%s%s -> %s" % (label, rule_label, format_number(sample_value)))
    return adjusted, notes


def coordinates_outside_axis_rules(font, coordinates, axis_rules_list):
    adjusted = coordinates_dict(font, coordinates)
    if adjusted is None:
        return coordinates, []
    notes = []
    for axis_rules in axis_rules_list or []:
        for axis_key, label, rule in axis_rule_entries(font, axis_rules):
            current_value = adjusted.get(str(axis_key))
            if current_value is None:
                continue
            sample_value, rule_label = outside_value_for_rule(current_value, rule)
            if sample_value is None:
                continue
            adjusted[str(axis_key)] = sample_value
            notes.append("%s%s -> %s" % (label, rule_label, format_number(sample_value)))
    return adjusted, notes


def mutable_copy(value):
    if value is None:
        return None
    for method_name in ("mutableCopy", "copy"):
        method = getattr(value, method_name, None)
        if method is None:
            continue
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


def remap_axis_rules(axis_rules, source_axis_index, target_axis_index):
    rules = [copied_axis_rule(rule) for rule in axis_rule_items(axis_rules)]
    if (
        source_axis_index is None
        or target_axis_index is None
        or source_axis_index >= len(rules)
        or target_axis_index >= len(rules)
    ):
        return copied_value(axis_rules), False

    source_rule = copied_axis_rule(rules[source_axis_index])
    if not axis_rule_has_limits(source_rule):
        return copied_value(axis_rules), False

    target_rule = copied_axis_rule(rules[target_axis_index])
    for limit_name in ("min", "max"):
        if limit_name in source_rule:
            target_rule[limit_name] = source_rule[limit_name]
    rules[source_axis_index] = {}
    rules[target_axis_index] = target_rule
    return rules, True


def remap_axis_rules_by_axis_id(axis_rules, source_axis_id, target_axis_id):
    if not hasattr(axis_rules, "keys"):
        return copied_value(axis_rules), False

    rules = {}
    try:
        keys = list(axis_rules.keys())
    except Exception:
        keys = []
    for key in keys:
        rules[str(key)] = copied_axis_rule(axis_rules[key])

    source_rule = copied_axis_rule(rules.get(str(source_axis_id)))
    if not axis_rule_has_limits(source_rule):
        return copied_value(axis_rules), False

    target_rule = copied_axis_rule(rules.get(str(target_axis_id)))
    for limit_name in ("min", "max"):
        if limit_name in source_rule:
            target_rule[limit_name] = source_rule[limit_name]
    rules[str(source_axis_id)] = {}
    rules[str(target_axis_id)] = target_rule
    return rules, True


def remap_axis_rules_native(axis_rules, source_axis_index, target_axis_index, source_axis_id=None, target_axis_id=None):
    if axis_rules is None:
        return None, False

    if source_axis_id is not None and target_axis_id is not None:
        remapped, did_remap = remap_axis_rules_by_axis_id(axis_rules, source_axis_id, target_axis_id)
        if did_remap:
            return remapped, True

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
    source_values = copied_axis_rule(source_rule)
    for limit_name in ("min", "max"):
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
    remapped, did_remap = remap_axis_rules_native(
        attribute_value(layer, "axisRules"),
        source_axis_index,
        target_axis_index,
        source_axis_id,
        target_axis_id,
    )
    if did_remap:
        set_layer_axis_rules(layer, remapped)
    return did_remap, remapped


def is_brace_layer(layer):
    if bool_method_or_attribute(layer, "isBraceLayer"):
        return True
    return bool(bool_method_or_attribute(layer, "isSpecialLayer") and "{" in layer_name(layer) and "}" in layer_name(layer))


def is_bracket_layer(layer):
    if bool_method_or_attribute(layer, "isBracketLayer"):
        return True
    return bool(bool_method_or_attribute(layer, "isSpecialLayer") and "[" in layer_name(layer) and "]" in layer_name(layer))


def is_component_special_layer(layer):
    if is_master_layer(layer):
        return False
    return bool(is_brace_layer(layer) or is_bracket_layer(layer) or has_coordinates_attribute(layer) or has_axis_rules_attribute(layer))


def proxy_count(object_value, attribute_name):
    try:
        return len(getattr(object_value, attribute_name))
    except Exception:
        return 0


def glyph_is_smart(glyph):
    method = getattr(glyph, "isSmartGlyph", None)
    if method is not None:
        try:
            return bool(method())
        except Exception:
            pass
    return bool(safe_call(getattr(glyph, "isSmartGlyph", False), False))


def component_name_from_object(component, allow_name_fallback=True):
    for attribute_name in ("componentName", "glyphName", "ref"):
        value = safe_call(getattr(component, attribute_name, None))
        if value:
            return str(value)

    for method_name in ("valueForKey_", "attributeForKey_"):
        method = getattr(component, method_name, None)
        if method is None:
            continue
        keys = ["componentName", "glyphName", "ref"]
        if allow_name_fallback:
            keys.append("name")
        for key in keys:
            try:
                value = method(key)
            except Exception:
                value = None
            if value:
                return str(value)

    for glyph_attribute in ("component", "glyph"):
        glyph = safe_call(getattr(component, glyph_attribute, None))
        if glyph is None:
            continue
        value = safe_call(getattr(glyph, "name", None))
        if value:
            return str(value)

    if allow_name_fallback:
        value = safe_call(getattr(component, "name", None))
        if value:
            return str(value)
    return None


def glyph_for_name(font, glyph_name):
    try:
        glyph = font.glyphs[glyph_name]
    except Exception:
        glyph = None
    if glyph is not None:
        return glyph

    for glyph in font.glyphs:
        if getattr(glyph, "name", None) == glyph_name:
            return glyph
    return None


def iter_layer_components(layer):
    seen = set()
    try:
        component_values = list(getattr(layer, "components"))
    except Exception:
        component_values = []

    for value in component_values:
        if component_name_from_object(value, allow_name_fallback=True) is None:
            continue
        identity = id(value)
        if identity in seen:
            continue
        seen.add(identity)
        yield value

    try:
        shape_values = list(getattr(layer, "shapes"))
    except Exception:
        shape_values = []

    for value in shape_values:
        if component_name_from_object(value, allow_name_fallback=False) is None:
            continue
        identity = id(value)
        if identity in seen:
            continue
        seen.add(identity)
        yield value


def layer_component_names(layer):
    names = []
    for component in iter_layer_components(layer):
        component_name = component_name_from_object(component)
        if component_name:
            names.append(component_name)
    return names


def layer_diagnostic_summary(layer):
    axis_rules = attribute_value(layer, "axisRules")
    coordinates = attribute_value(layer, "coordinates")
    part_selection = attribute_value(layer, "partSelection")
    associated_master_id = getattr(layer, "associatedMasterId", None)
    return (
        "id=%s name=%r master=%s special=%s brace=%s bracket=%s "
        "assoc=%s width=%s shapes=%i components=%i anchors=%i hints=%i "
        "componentNames=%s axisRules=%s coordinates=%s partSelection=%s"
    ) % (
        layer_id(layer),
        layer_name(layer),
        is_master_layer(layer),
        bool_method_or_attribute(layer, "isSpecialLayer"),
        is_brace_layer(layer),
        is_bracket_layer(layer),
        associated_master_id,
        getattr(layer, "width", None),
        proxy_count(layer, "shapes"),
        proxy_count(layer, "components"),
        proxy_count(layer, "anchors"),
        proxy_count(layer, "hints"),
        layer_component_names(layer),
        short_value(axis_rules),
        short_value(coordinates),
        short_value(part_selection),
    )


def print_layer_diagnostics(layer, prefix):
    diagnostic("%s %s" % (prefix, layer_diagnostic_summary(layer)))
    diagnostic("%s axisRules sources: %s" % (prefix, raw_attribute_sources(layer, "axisRules")))
    diagnostic("%s coordinates sources: %s" % (prefix, raw_attribute_sources(layer, "coordinates")))
    diagnostic("%s partSelection sources: %s" % (prefix, raw_attribute_sources(layer, "partSelection")))


def glyph_component_names(glyph):
    names = []
    seen = set()
    for layer in glyph.layers:
        for component in iter_layer_components(layer):
            component_name = component_name_from_object(component)
            if component_name and component_name not in seen:
                seen.add(component_name)
                names.append(component_name)
    return names


def layer_has_same_name_and_master(glyph, source_layer):
    source_name = layer_name(source_layer)
    source_master_id = getattr(source_layer, "associatedMasterId", None)
    for layer in glyph.layers:
        if layer_name(layer) != source_name:
            continue
        if getattr(layer, "associatedMasterId", None) == source_master_id:
            return True
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

        for attribute_name, setter_name in (
            ("transform", "setTransform_"),
            ("position", "setPosition_"),
            ("scale", "setScale_"),
            ("rotation", "setRotation_"),
        ):
            value = safe_call(getattr(master_component, attribute_name, None))
            if value is None:
                continue
            try:
                value = value.copy()
            except Exception:
                pass
            setter = getattr(special_component, setter_name, None)
            if setter is not None:
                try:
                    setter(value)
                    continue
                except Exception:
                    pass
            try:
                setattr(special_component, attribute_name, value)
            except Exception:
                pass

        alignment = getattr(master_component, "alignment", None)
        method = getattr(special_component, "setAlignment_", None)
        if method is not None and alignment is not None:
            try:
                method(alignment)
            except Exception:
                pass

        method = getattr(special_component, "setIsAligned_", None)
        is_aligned = safe_call(getattr(master_component, "isAligned", None))
        if method is not None and is_aligned is not None:
            try:
                method(is_aligned)
            except Exception:
                pass


def add_component_special_layer_to_composite(composite_glyph, component_special_layer):
    if layer_has_same_name_and_master(composite_glyph, component_special_layer):
        diagnostic("component special layer already exists in %s: %s / associatedMasterId=%s" % (
            composite_glyph.name,
            layer_name(component_special_layer),
            getattr(component_special_layer, "associatedMasterId", None),
        ))
        return None

    associated_master_id = getattr(component_special_layer, "associatedMasterId", None)
    diagnostic("adding component special layer to %s from %s" % (
        composite_glyph.name,
        layer_name(component_special_layer) or layer_id(component_special_layer),
    ))
    print_layer_diagnostics(component_special_layer, "source component layer before add")

    new_layer = GSLayer()
    new_layer.name = layer_name(component_special_layer)
    set_associated_master_id(new_layer, associated_master_id)
    copy_layer_attributes(component_special_layer, new_layer)
    try:
        master_layer = composite_glyph.layers[associated_master_id]
    except Exception:
        master_layer = None
    if master_layer is not None:
        new_layer.width = master_layer.width
    else:
        new_layer.width = component_special_layer.width
    composite_glyph.layers.append(new_layer)
    print_layer_diagnostics(new_layer, "new composite layer after append/before reinterpolate")

    diagnostic("new composite layer reinterpolate=%s" % call_layer_method(new_layer, "reinterpolate"))
    diagnostic("new composite layer reinterpolateMetrics=%s" % call_layer_method(new_layer, "reinterpolateMetrics"))
    diagnostic("new composite layer syncMetrics=%s" % call_layer_method(new_layer, "syncMetrics"))
    print_layer_diagnostics(new_layer, "new composite layer after reinterpolate")

    if master_layer is not None:
        new_layer.width = master_layer.width
        print_layer_diagnostics(master_layer, "master layer used for alignment sync")
        sync_component_alignment_from_master(master_layer, new_layer)
        new_layer.width = master_layer.width
        print_layer_diagnostics(new_layer, "new composite layer after alignment sync")
    else:
        diagnostic("no master layer found for alignment sync: associatedMasterId=%s" % associated_master_id)
    return new_layer


def add_component_special_layers_to_composite_source(font, composite_glyph):
    added = 0
    added_names = []
    component_names_seen = set()
    missing_component_names = set()
    component_special_candidates = 0

    # Repeat a few times so components introduced by component layers can bring
    # in their own local brace/bracket designspaces too.
    for pass_index in range(5):
        pass_added = 0
        component_names = glyph_component_names(composite_glyph)
        diagnostic("%s component scan pass %i: %i component name(s): %s" % (
            composite_glyph.name,
            pass_index + 1,
            len(component_names),
            ", ".join(component_names),
        ))
        for component_name in component_names:
            component_names_seen.add(component_name)
            component_glyph = glyph_for_name(font, component_name)
            if component_glyph is None:
                missing_component_names.add(component_name)
                diagnostic("component glyph lookup failed: %s" % component_name)
                continue

            try:
                component_layers = list(component_glyph.layers)
            except Exception:
                component_layers = []
            diagnostic("component glyph %s: layers=%i smart=%s export=%s" % (
                component_name,
                len(component_layers),
                glyph_is_smart(component_glyph),
                getattr(component_glyph, "export", None),
            ))

            for layer_index_value, component_layer in enumerate(component_layers):
                is_candidate = is_component_special_layer(component_layer)
                diagnostic("component glyph %s layer %i candidate=%s" % (
                    component_name,
                    layer_index_value,
                    is_candidate,
                ))
                print_layer_diagnostics(component_layer, "component %s layer %i" % (
                    component_name,
                    layer_index_value,
                ))

                if not is_candidate:
                    continue
                component_special_candidates += 1
                new_layer = add_component_special_layer_to_composite(composite_glyph, component_layer)
                if new_layer is None:
                    diagnostic("candidate did not add new layer: component=%s sourceLayer=%s" % (
                        component_name,
                        layer_name(component_layer) or layer_id(component_layer),
                    ))
                    continue
                pass_added += 1
                added += 1
                added_names.append(layer_name(new_layer) or layer_id(new_layer))
                diagnostic("candidate added new layer: component=%s newLayer=%s" % (
                    component_name,
                    layer_name(new_layer) or layer_id(new_layer),
                ))
        if pass_added == 0:
            diagnostic("%s component scan pass %i added no layers; stopping" % (
                composite_glyph.name,
                pass_index + 1,
            ))
            break
        diagnostic("%s component scan pass %i added %i layer(s)" % (
            composite_glyph.name,
            pass_index + 1,
            pass_added,
        ))

    if added == 0:
        if component_names_seen:
            print("%s: scanned %i component glyph(s) and %i component special candidate(s) but added none: %s" % (
                composite_glyph.name,
                len(component_names_seen),
                component_special_candidates,
                ", ".join(sorted(component_names_seen)),
            ))
        else:
            print_warning("%s: component scan found no component names" % composite_glyph.name)
    if missing_component_names:
        print_warning("%s: could not find %i component glyph(s): %s" % (
            composite_glyph.name,
            len(missing_component_names),
            ", ".join(sorted(missing_component_names)),
        ))

    return added, added_names


def prepared_sampling_source_glyph(font, source_glyph):
    glyph_copy = source_glyph.copy()
    glyph_copy.name = "__tmp_math_bold_source_%s_%s" % (
        source_glyph.name,
        str(uuid.uuid4()).replace("-", ""),
    )
    try:
        glyph_copy.export = False
    except Exception:
        pass

    font.glyphs.append(glyph_copy)
    diagnostic("prepared sampling source copy appended: original=%s copy=%s" % (
        source_glyph.name,
        glyph_copy.name,
    ))
    diagnostic("original source component names: %s" % ", ".join(glyph_component_names(source_glyph)))
    diagnostic("sampling copy component names before component-special expansion: %s" % ", ".join(glyph_component_names(glyph_copy)))
    added, added_names = add_component_special_layers_to_composite_source(font, glyph_copy)
    if added:
        print("%s: prepared sampling source with %i component special layer(s): %s" % (
            source_glyph.name,
            added,
            ", ".join(added_names),
        ))
    else:
        print("%s: sampling source needed no component special layers" % source_glyph.name)
    decompose_sampling_source_layers(glyph_copy)
    diagnostic("%s final sampling source layer inventory: %i layer(s)" % (
        glyph_copy.name,
        len(list(glyph_copy.layers)),
    ))
    for layer_index_value, layer in enumerate(glyph_copy.layers):
        print_layer_diagnostics(layer, "sampling source final layer %i" % layer_index_value)
    return glyph_copy


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


def source_coordinate_layers(source_glyph):
    layers = []
    for layer in source_glyph.layers:
        if is_master_layer(layer):
            continue
        if has_coordinates_attribute(layer):
            layers.append(layer)
    return layers


def source_alternate_layers(source_glyph):
    layers = []
    for layer in source_glyph.layers:
        if is_master_layer(layer) or has_coordinates_attribute(layer):
            continue
        if has_axis_rules_attribute(layer):
            layers.append(layer)
    return layers


def source_alternate_layers_for_master(source_glyph, associated_master_id):
    return [
        layer for layer in source_alternate_layers(source_glyph)
        if getattr(layer, "associatedMasterId", None) == associated_master_id
    ]


def source_alternate_layer_for_rules(source_glyph, associated_master_id, axis_rules):
    for layer in source_alternate_layers_for_master(source_glyph, associated_master_id):
        if axis_rules_match(attribute_value(layer, "axisRules"), axis_rules):
            return layer
    return None


def source_axis_rules_for_master(source_glyph, associated_master_id):
    rules = []
    seen = set()
    for layer in source_alternate_layers(source_glyph):
        if getattr(layer, "associatedMasterId", None) != associated_master_id:
            continue
        axis_rules = attribute_value(layer, "axisRules")
        key = axis_rules_key(axis_rules)
        if key in seen:
            continue
        seen.add(key)
        rules.append(axis_rules)
    return rules


def special_layer_shell(layer_id_value, name, coordinates, axis_rules, associated_master_id, width):
    layer = GSLayer()
    layer.layerId = layer_id_value
    layer.name = name
    set_associated_master_id(layer, associated_master_id)
    if coordinates is not None:
        set_layer_attribute(layer, "coordinates", coordinates)
    if axis_rules is not None:
        set_layer_axis_rules(layer, axis_rules)
    layer.width = width
    return layer


def create_intermediate_layer(glyph, master_layer, master, coordinates, width, target_axis_tag, target_axis_value):
    new_layer = special_layer_shell(
        str(uuid.uuid4()).upper(),
        "%s %s %s" % (master.name, target_axis_tag, target_axis_value),
        coordinates,
        None,
        master.id,
        width,
    )
    glyph.layers.insert(layer_index(glyph, master_layer) + 1, new_layer)
    return new_layer


def alternate_rules_name(master, axis_rules, font):
    parts = []
    for axis_key, label, rule in axis_rule_entries(font, axis_rules):
        if not rule:
            continue
        if "max" in rule:
            parts.append("%s<%s" % (label, rule["max"]))
        if "min" in rule:
            parts.append("%s>%s" % (label, rule["min"]))
    if not parts:
        return "%s alternate" % master.name
    return "%s [%s]" % (master.name, ", ".join(parts))


def rotated_coordinate_layer_name(master, source_layer, target_axis_tag, target_axis_value, axis_rules, font):
    if axis_rules is not None:
        return "%s %s %s" % (
            alternate_rules_name(master, axis_rules, font),
            target_axis_tag,
            target_axis_value,
        )
    if layer_name(source_layer):
        return "%s %s %s" % (master.name, target_axis_tag, target_axis_value)
    return "%s %s %s" % (master.name, target_axis_tag, target_axis_value)


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
    if axis_rules is not None:
        set_layer_axis_rules(new_layer, axis_rules)
    return new_layer


def count_components(layer):
    try:
        return len(layer.components)
    except Exception:
        return 0


def count_helper_hints(layer):
    if not hasattr(layer, "hints"):
        return 0
    count = 0
    for hint in layer.hints:
        name = str(safe_call(getattr(hint, "name", ""), "") or "")
        hint_type = str(safe_call(getattr(hint, "type", ""), "") or "")
        if name.startswith(("_corner.", "_cap.", "_segment.", "_brush.", "_stem")) or hint_type in ("Corner", "Cap", "Segment", "Brush", "Stem"):
            count += 1
    return count


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


def decompose_one_pass(layer):
    changed = False
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

    for method_name in (
        "decomposeSmartOutlines",
        "decomposeCorners",
        "decomposeCornerComponents",
        "decomposeCornersAndCaps",
        "decomposeCornerComponentsAndCaps",
        "decomposeHints",
    ):
        if call_layer_method(layer, method_name):
            changed = True
    return changed


def decompose_layer_fully(layer):
    previous_state = None
    for _ in range(12):
        before = (count_components(layer), count_helper_hints(layer), shape_count(layer))
        changed = decompose_one_pass(layer)
        after = (count_components(layer), count_helper_hints(layer), shape_count(layer))
        if not changed or after == before or after == previous_state:
            break
        previous_state = before


def decompose_sampling_source_layers(glyph):
    changed_layers = 0
    layers_with_components = []
    try:
        layers = list(glyph.layers)
    except Exception:
        layers = []

    for layer_index_value, layer in enumerate(layers):
        before = (
            shape_count(layer),
            count_components(layer),
            anchor_count(layer),
            count_helper_hints(layer),
        )
        diagnostic("%s: pre-decompose source layer %i before: shapes=%i components=%i anchors=%i helpers=%i name=%s" % (
            glyph.name,
            layer_index_value,
            before[0],
            before[1],
            before[2],
            before[3],
            layer_name(layer) or layer_id(layer),
        ))
        decompose_layer_fully(layer)
        after = (
            shape_count(layer),
            count_components(layer),
            anchor_count(layer),
            count_helper_hints(layer),
        )
        diagnostic("%s: pre-decompose source layer %i after: shapes=%i components=%i anchors=%i helpers=%i name=%s" % (
            glyph.name,
            layer_index_value,
            after[0],
            after[1],
            after[2],
            after[3],
            layer_name(layer) or layer_id(layer),
        ))
        if after != before:
            changed_layers += 1
        if after[1]:
            layers_with_components.append(layer_name(layer) or layer_id(layer))

    print("%s: pre-decomposed sampling source (%i/%i layer(s) changed)" % (
        glyph.name,
        changed_layers,
        len(layers),
    ))
    if layers_with_components:
        print_warning("%s: %i sampling source layer(s) still have components after pre-decompose: %s" % (
            glyph.name,
            len(layers_with_components),
            ", ".join(layers_with_components),
        ))


def interpolated_decomposed_layer_copy(source_glyph, coordinates, axis_rules, associated_master_id):
    diagnostic("interpolation request: source=%s coordinates=%s axisRules=%s associatedMasterId=%s" % (
        source_glyph.name,
        short_value(coordinates),
        short_value(axis_rules),
        associated_master_id,
    ))
    interpolation_layer = special_layer_shell(
        str(uuid.uuid4()).upper(),
        "__tmp_interpolate_%s" % source_glyph.name,
        coordinates,
        axis_rules,
        associated_master_id,
        0,
    )
    print_layer_diagnostics(interpolation_layer, "temporary interpolation layer before append")
    source_glyph.layers.append(interpolation_layer)
    try:
        diagnostic("temporary interpolation reinterpolate=%s" % call_layer_method(interpolation_layer, "reinterpolate"))
        print_layer_diagnostics(interpolation_layer, "temporary interpolation layer after reinterpolate")
        diagnostic("temporary interpolation reinterpolateMetrics=%s" % call_layer_method(interpolation_layer, "reinterpolateMetrics"))
        diagnostic("temporary interpolation syncMetrics=%s" % call_layer_method(interpolation_layer, "syncMetrics"))
        print_layer_diagnostics(interpolation_layer, "temporary interpolation layer after metrics")
        decompose_layer_fully(interpolation_layer)
        print_layer_diagnostics(interpolation_layer, "temporary interpolation layer after decompose")
        return interpolation_layer.copy()
    finally:
        diagnostic("removing temporary interpolation layer %s from %s" % (
            layer_id(interpolation_layer),
            source_glyph.name,
        ))
        remove_layer(source_glyph, interpolation_layer)


def direct_decomposed_layer_copy(source_glyph, source_layer_id):
    source_layer = glyph_layer_for_id(source_glyph, source_layer_id)
    if source_layer is None:
        print_warning("%s: direct source layer %s was not found; falling back to interpolation" % (
            source_glyph.name,
            source_layer_id,
        ))
        return None

    diagnostic("direct source layer copy: source=%s layer=%s name=%s" % (
        source_glyph.name,
        source_layer_id,
        layer_name(source_layer) or layer_id(source_layer),
    ))
    source_copy = source_layer.copy()
    decompose_layer_fully(source_copy)
    return source_copy


def copy_sample_to_target(font, sampling_source_glyph, sample, target_layer):
    direct_source_layer_id = sample.get("direct_source_layer_id")
    if direct_source_layer_id:
        source_copy = direct_decomposed_layer_copy(sampling_source_glyph, direct_source_layer_id)
        sample_coordinates = sample.get("coordinates")
        axis_rule_notes = ["direct %s" % direct_source_layer_id]
    else:
        source_copy = None

    if source_copy is None:
        if sample.get("axis_rules") is not None:
            sample_coordinates, axis_rule_notes = coordinates_inside_axis_rules(
                font,
                sample.get("coordinates"),
                sample.get("axis_rules"),
            )
        else:
            sample_coordinates, axis_rule_notes = coordinates_outside_axis_rules(
                font,
                sample.get("coordinates"),
                sample.get("avoid_axis_rules"),
            )

        source_copy = interpolated_decomposed_layer_copy(
            sampling_source_glyph,
            sample_coordinates,
            sample.get("axis_rules"),
            sample.get("associated_master_id"),
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
    for metric_key in ("leftMetricsKey", "rightMetricsKey", "widthMetricsKey"):
        copy_metric_attribute(source_copy, target_layer, metric_key)

    return dict(
        shapes=shape_count(source_copy),
        anchors=anchor_count(source_copy),
        stems=stem_count,
        components=count_components(source_copy),
        helpers=count_helper_hints(source_copy),
        coordinates=sample_coordinates,
        notes=axis_rule_notes,
    )


def enqueue_sample(
    samples_by_layer_id,
    layer,
    coordinates,
    axis_rules,
    associated_master_id,
    label,
    avoid_axis_rules=None,
    direct_source_layer_id=None,
):
    samples_by_layer_id[layer_id(layer)] = dict(
        coordinates=coordinates,
        axis_rules=axis_rules,
        associated_master_id=associated_master_id,
        label=label,
        avoid_axis_rules=avoid_axis_rules or [],
        direct_source_layer_id=direct_source_layer_id,
    )


def enqueue_master_and_intermediate_samples(
    font,
    source_glyph,
    sampling_source_glyph,
    destination_glyph,
    source_axis_id,
    target_axis_id,
    source_low_value,
    source_high_value,
    target_axis_tag,
    target_axis_value,
    samples_by_layer_id,
):
    created = 0
    skipped = 0
    for master in font.masters:
        master_layer = destination_glyph.layers[master.id]
        if master_layer is None:
            skipped += 1
            print_warning("%s: skipped, no destination master layer" % master.name)
            continue

        target_master_coordinates = master_coordinates(font, master)
        if target_master_coordinates is None:
            skipped += 1
            print_warning("%s: skipped, could not read master coordinates" % master.name)
            continue

        low_master = corresponding_master_for_axis_value(
            font,
            target_master_coordinates,
            source_axis_id,
            target_axis_id,
            source_low_value,
        )
        if low_master is not None:
            low_coordinates = master_coordinates(font, low_master)
            enqueue_sample(
                samples_by_layer_id,
                master_layer,
                low_coordinates,
                None,
                low_master.id,
                low_master.name,
                source_axis_rules_for_master(sampling_source_glyph, low_master.id),
                direct_source_layer_id=low_master.id,
            )
        else:
            skipped += 1
            print_warning("%s: could not find source master for %s=%s" % (
                master.name,
                source_axis_id,
                source_low_value,
            ))

        intermediate_coordinates = dict(target_master_coordinates)
        intermediate_coordinates[str(target_axis_id)] = float(target_axis_value)
        intermediate_layer = create_intermediate_layer(
            destination_glyph,
            master_layer,
            master,
            intermediate_coordinates,
            master_layer.width,
            target_axis_tag,
            target_axis_value,
        )
        created += 1
        high_master = corresponding_master_for_axis_value(
            font,
            target_master_coordinates,
            source_axis_id,
            target_axis_id,
            source_high_value,
        )
        if high_master is not None:
            high_coordinates = master_coordinates(font, high_master)
            enqueue_sample(
                samples_by_layer_id,
                intermediate_layer,
                high_coordinates,
                None,
                high_master.id,
                high_master.name,
                source_axis_rules_for_master(sampling_source_glyph, high_master.id),
                direct_source_layer_id=high_master.id,
            )
        else:
            skipped += 1
            print_warning("%s: could not find source master for %s=%s" % (
                intermediate_layer.name,
                source_axis_id,
                source_high_value,
            ))
        print("%s: created intermediate layer at %s" % (master.name, intermediate_coordinates))
    return created, skipped


def enqueue_source_coordinate_layers(
    font,
    source_glyph,
    sampling_source_glyph,
    destination_glyph,
    source_axis_tag,
    target_axis_tag,
    source_axis_id,
    target_axis_id,
    source_axis_index,
    target_axis_index,
    target_axis_value,
    samples_by_layer_id,
):
    created = 0
    skipped = 0
    for source_layer in source_coordinate_layers(source_glyph):
        source_coordinates = coordinates_for_layer(font, source_layer)
        if source_coordinates is None:
            skipped += 1
            print_warning("%s: skipped source coordinate layer %s, could not read coordinates" % (
                destination_glyph.name,
                layer_name(source_layer) or layer_id(source_layer),
            ))
            continue

        source_axis_rules = attribute_value(source_layer, "axisRules")
        target_axis_rules, remapped = remap_axis_rules_native(
            source_axis_rules,
            source_axis_index,
            target_axis_index,
            source_axis_id,
            target_axis_id,
        )

        source_master_id = getattr(source_layer, "associatedMasterId", None)
        if source_master_id is None:
            source_master = master_for_coordinates(font, source_coordinates)
            source_master_id = source_master.id if source_master is not None else None

        matched = 0
        for master in font.masters:
            target_master_coordinates = master_coordinates(font, master)
            if target_master_coordinates is None:
                continue
            if not coordinates_match_except_axes(
                font,
                target_master_coordinates,
                source_coordinates,
                [source_axis_id, target_axis_id],
            ):
                continue

            master_layer = destination_glyph.layers[master.id]
            if master_layer is None:
                skipped += 1
                continue
            destination_coordinates = dict(target_master_coordinates)
            destination_coordinates[str(target_axis_id)] = float(target_axis_value)
            new_layer_name = rotated_coordinate_layer_name(
                master,
                source_layer,
                target_axis_tag,
                target_axis_value,
                target_axis_rules,
                font,
            )
            new_layer = create_special_layer_after(
                destination_glyph,
                master_layer,
                new_layer_name,
                master.id,
                destination_coordinates,
                target_axis_rules,
                source_layer.width,
            )
            if remapped:
                force_layer_rules_to_target_axis(new_layer, source_axis_index, target_axis_index, source_axis_id, target_axis_id)
                new_layer.name = new_layer_name
            enqueue_sample(
                samples_by_layer_id,
                new_layer,
                source_coordinates,
                source_axis_rules,
                source_master_id,
                layer_name(source_layer) or layer_id(source_layer),
                source_axis_rules_for_master(sampling_source_glyph, source_master_id),
            )
            created += 1
            matched += 1
            print("%s: created rotated coordinate layer %s from source %s at %s" % (
                master.name,
                new_layer_name,
                layer_name(source_layer) or layer_id(source_layer),
                destination_coordinates,
            ))

        if matched == 0:
            skipped += 1
            print_warning("%s: skipped source coordinate layer %s, no matching destination master location" % (
                destination_glyph.name,
                layer_name(source_layer) or layer_id(source_layer),
            ))
    return created, skipped


def enqueue_alternate_layers(
    font,
    alternate_source_glyph,
    destination_glyph,
    source_axis_tag,
    target_axis_tag,
    source_axis_id,
    target_axis_id,
    source_axis_index,
    target_axis_index,
    source_low_value,
    source_high_value,
    target_axis_value,
    samples_by_layer_id,
):
    created = 0
    skipped = 0
    for master in font.masters:
        target_master_coordinates = master_coordinates(font, master)
        if target_master_coordinates is None:
            skipped += 1
            continue

        low_master = corresponding_master_for_axis_value(
            font,
            target_master_coordinates,
            source_axis_id,
            target_axis_id,
            source_low_value,
        )
        high_master = corresponding_master_for_axis_value(
            font,
            target_master_coordinates,
            source_axis_id,
            target_axis_id,
            source_high_value,
        )
        if low_master is None or high_master is None:
            skipped += 1
            print_warning("%s: skipped alternates, could not find low/high source masters" % master.name)
            continue

        master_layer = destination_glyph.layers[master.id]
        if master_layer is None:
            skipped += 1
            continue

        low_coordinates = master_coordinates(font, low_master)
        high_coordinates = master_coordinates(font, high_master)
        if low_coordinates is None or high_coordinates is None:
            skipped += 1
            continue

        for low_alternate in source_alternate_layers_for_master(alternate_source_glyph, low_master.id):
            axis_rules = attribute_value(low_alternate, "axisRules")
            high_alternate = source_alternate_layer_for_rules(alternate_source_glyph, high_master.id, axis_rules)
            if high_alternate is None:
                skipped += 1
                print_warning("%s: skipped alternate for %s, missing matching high source layer for %s" % (
                    destination_glyph.name,
                    master.name,
                    layer_name(low_alternate) or layer_id(low_alternate),
                ))
                continue

            target_axis_rules, remapped = remap_axis_rules_native(
                axis_rules,
                source_axis_index,
                target_axis_index,
                source_axis_id,
                target_axis_id,
            )
            alternate_name = alternate_rules_name(master, target_axis_rules, font)
            alternate_layer = create_special_layer_after(
                destination_glyph,
                master_layer,
                alternate_name,
                master.id,
                None,
                target_axis_rules,
                low_alternate.width,
            )
            if remapped:
                force_layer_rules_to_target_axis(alternate_layer, source_axis_index, target_axis_index, source_axis_id, target_axis_id)
                alternate_layer.name = alternate_name
            enqueue_sample(
                samples_by_layer_id,
                alternate_layer,
                low_coordinates,
                axis_rules,
                low_master.id,
                layer_name(low_alternate) or layer_id(low_alternate),
                direct_source_layer_id=layer_id(low_alternate),
            )
            created += 1
            if remapped:
                print("%s: created alternate layer %s with %s rule remapped to %s" % (
                    master.name,
                    alternate_name,
                    source_axis_tag,
                    target_axis_tag,
                ))
            else:
                print("%s: created alternate layer %s" % (master.name, alternate_name))

            alternate_coordinates = dict(target_master_coordinates)
            alternate_coordinates[str(target_axis_id)] = float(target_axis_value)
            alternate_intermediate_name = "%s %s %s" % (alternate_name, target_axis_tag, target_axis_value)
            alternate_intermediate_layer = create_special_layer_after(
                destination_glyph,
                alternate_layer,
                alternate_intermediate_name,
                master.id,
                alternate_coordinates,
                target_axis_rules,
                high_alternate.width,
            )
            if remapped:
                force_layer_rules_to_target_axis(alternate_intermediate_layer, source_axis_index, target_axis_index, source_axis_id, target_axis_id)
                alternate_intermediate_layer.name = alternate_intermediate_name
            enqueue_sample(
                samples_by_layer_id,
                alternate_intermediate_layer,
                high_coordinates,
                axis_rules,
                high_master.id,
                layer_name(high_alternate) or layer_id(high_alternate),
                direct_source_layer_id=layer_id(high_alternate),
            )
            created += 1
            print("%s: created alternate intermediate layer %s at %s" % (
                master.name,
                alternate_intermediate_layer.name,
                alternate_coordinates,
            ))
    return created, skipped


def node_signature(node):
    node_type = str(safe_call(getattr(node, "type", ""), "") or "")
    smooth = bool(safe_call(getattr(node, "smooth", False), False))
    return "%ss" % node_type if smooth else node_type


def shape_signature(shape):
    try:
        nodes = list(shape.nodes)
    except Exception:
        nodes = None
    if nodes is not None:
        closed = safe_call(getattr(shape, "closed", None))
        if closed is None:
            closed = safe_call(getattr(shape, "isClosed", None))
        direction = safe_call(getattr(shape, "direction", ""))
        return ("path", bool(closed), str(direction), tuple(node_signature(node) for node in nodes))

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
        elif item[0] == "path":
            parts.append("p%i:%s:dir=%s:n=%i:%s" % (
                index,
                "closed" if item[1] else "open",
                item[2],
                len(item[3]),
                "/".join(item[3]),
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


def fill_queued_samples(font, destination_glyph, sampling_source_glyph, samples_by_layer_id):
    copied = 0
    skipped = 0
    for layer in destination_glyph.layers:
        sample = samples_by_layer_id.get(layer_id(layer))
        if sample is None:
            continue
        result = copy_sample_to_target(font, sampling_source_glyph, sample, layer)
        copied += 1
        axis_rule_note = ""
        if result["notes"]:
            axis_rule_note = "; axis-rule sample %s" % ", ".join(result["notes"])
        print("%s: sampled %s at %s from %s (%i shapes, %i anchors, %i stems, target width %s%s; remaining components %i, helpers %i)" % (
            layer_name(layer) or layer_id(layer),
            sampling_source_glyph.name,
            result["coordinates"],
            sample.get("label"),
            result["shapes"],
            result["anchors"],
            result["stems"],
            layer.width,
            axis_rule_note,
            result["components"],
            result["helpers"],
        ))
        if result["components"]:
            print_warning("%s: sampled layer still has %i component(s)" % (
                layer_name(layer) or layer_id(layer),
                result["components"],
            ))
    return copied, skipped


def rotate_glyph_designspace_from_source(
    font,
    source_glyph,
    sampling_source_glyph,
    destination_glyph,
    source_axis_tag,
    target_axis_tag,
    source_low_value,
    source_high_value,
    target_axis_value,
):
    source_axis_id = axis_id_for_tag(font, source_axis_tag)
    target_axis_id = axis_id_for_tag(font, target_axis_tag)
    if source_axis_id is None:
        print_warning("Could not find axis %s in the open font." % source_axis_tag)
        return process_stats(copy_layers_skipped=len(destination_glyph.layers))
    if target_axis_id is None:
        print_warning("Could not find axis %s in the open font." % target_axis_tag)
        return process_stats(copy_layers_skipped=len(destination_glyph.layers))

    source_axis_index = axis_index(font, source_axis_tag)
    target_axis_index = axis_index(font, target_axis_tag)
    samples_by_layer_id = {}
    created = 0
    skipped = 0

    print("")
    print("[%s]" % destination_glyph.name)
    removed = delete_non_master_layers(destination_glyph)
    if removed:
        print("%s: deleted %i non-master layer(s) before rebuilding" % (destination_glyph.name, removed))

    master_created, master_skipped = enqueue_master_and_intermediate_samples(
        font,
        source_glyph,
        sampling_source_glyph,
        destination_glyph,
        source_axis_id,
        target_axis_id,
        source_low_value,
        source_high_value,
        target_axis_tag,
        target_axis_value,
        samples_by_layer_id,
    )
    created += master_created
    skipped += master_skipped

    coord_created, coord_skipped = enqueue_source_coordinate_layers(
        font,
        source_glyph,
        sampling_source_glyph,
        destination_glyph,
        source_axis_tag,
        target_axis_tag,
        source_axis_id,
        target_axis_id,
        source_axis_index,
        target_axis_index,
        target_axis_value,
        samples_by_layer_id,
    )
    created += coord_created
    skipped += coord_skipped

    alternate_created, alternate_skipped = enqueue_alternate_layers(
        font,
        sampling_source_glyph,
        destination_glyph,
        source_axis_tag,
        target_axis_tag,
        source_axis_id,
        target_axis_id,
        source_axis_index,
        target_axis_index,
        source_low_value,
        source_high_value,
        target_axis_value,
        samples_by_layer_id,
    )
    skipped += alternate_skipped

    copied, copy_skipped = fill_queued_samples(
        font,
        destination_glyph,
        sampling_source_glyph,
        samples_by_layer_id,
    )
    report_outline_compatibility(destination_glyph)

    print("%s summary: deleted non-master %i, created %i, alternate created %i, skipped %i" % (
        destination_glyph.name,
        removed,
        created,
        alternate_created,
        skipped,
    ))

    return process_stats(
        created=created,
        refreshed=0,
        skipped=skipped,
        layers_copied=copied,
        copy_layers_skipped=copy_skipped,
        alternates_created=alternate_created,
        alternates_refreshed=0,
        stale_layers_removed=removed,
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
    sampling_source_glyph = None
    try:
        sampling_source_glyph = prepared_sampling_source_glyph(font, source_glyph)
        return rotate_glyph_designspace_from_source(
            font,
            source_glyph,
            sampling_source_glyph,
            destination_glyph,
            source_axis_tag,
            target_axis_tag,
            source_low_value,
            source_high_value,
            target_axis_value,
        )
    finally:
        if sampling_source_glyph is not None:
            remove_temp_glyph(font, sampling_source_glyph)


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
