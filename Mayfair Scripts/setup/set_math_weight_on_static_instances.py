#MenuTitle: Set Math Weight on Static Instances
# -*- coding: utf-8 -*-

"""
Set the Math Weight axis value on every complete static instance.

The script first asks for the amount to add to the `Weight` axis value and the
maximum allowed `Math Weight` value. With the default values, it calculates:

    Math Weight = min(900, Weight + 200)

It then writes that value in two places:

- the instance's live `Math Weight` axis value, so the instance actually uses
  the desired coordinate in Glyphs;
- the instance's `Axis Location` custom parameter, adding or updating the
  `Math Weight` entry there so exported static fonts keep the same location.

Instances without complete static axis values are skipped and reported in the
Macro panel. The script handles both list-style and dictionary-style
`axesValues`, and tries the modern and older Glyphs API spellings for setting
axis values.

Use this after adding the `Math Weight` axis and after creating or updating
static instances whose math-bold glyphs should be heavier than the text weight.
For example, with the defaults, a Weight value of 400 gets Math Weight 600,
while a Weight value of 800 or 900 is capped at Math Weight 900.
"""

import re

import vanilla
from GlyphsApp import Glyphs, GSCustomParameter


WEIGHT_AXIS_NAME = "Weight"
MATH_AXIS_NAME = "Math Weight"
AXIS_LOCATION_PARAMETER_NAME = "Axis Location"
DEFAULT_WEIGHT_OFFSET = 200
DEFAULT_MATH_WEIGHT_MAXIMUM = 900


def axis_index(font, axis_name):
    for index, axis in enumerate(font.axes):
        if axis.name == axis_name:
            return index
    raise ValueError("Could not find axis named %r" % axis_name)


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


def axis_id_for_name(font, axis_name):
    for axis in font.axes:
        if axis.name == axis_name:
            return axis_id(axis)
    raise ValueError("Could not find axis named %r" % axis_name)


def number_value(value):
    for attribute_name in ("value", "position", "pos", "floatValue"):
        attribute_value = getattr(value, attribute_name, None)
        if attribute_value is None:
            continue
        if callable(attribute_value):
            try:
                attribute_value = attribute_value()
            except Exception:
                continue
        if attribute_value is value:
            continue
        try:
            return number_value(attribute_value)
        except Exception:
            pass

    try:
        numeric_value = float(value)
    except Exception:
        match = re.search(r":\s*(-?\d+(?:\.\d+)?)\s*/", repr(value))
        if match:
            numeric_value = float(match.group(1))
        else:
            raise ValueError("Expected a numeric axis value, got %r" % value)

    if numeric_value.is_integer():
        return int(numeric_value)
    return numeric_value


def calculated_math_weight(weight, weight_offset, math_weight_maximum):
    return min(math_weight_maximum, number_value(weight) + weight_offset)


def axis_location_parameter(instance):
    for parameter in instance.customParameters:
        if parameter.name == AXIS_LOCATION_PARAMETER_NAME:
            return parameter
    return None


def mutable_axis_locations(value):
    if not value:
        return []
    return [dict(location) for location in value]


def set_axis_location(axis_locations, axis_name, location_value):
    for location in axis_locations:
        if location.get("Axis") == axis_name:
            location["Location"] = location_value
            return
    axis_locations.append({
        "Axis": axis_name,
        "Location": location_value,
    })


def raw_instance_axes_values(instance):
    axes_values = instance.axesValues
    if callable(axes_values):
        axes_values = axes_values()
    return axes_values


def dictionary_keys(value):
    try:
        return list(value.keys())
    except Exception:
        return None


def dictionary_copy(value):
    keys = dictionary_keys(value)
    if keys is None:
        return None
    return dict((key, value[key]) for key in keys)


def axis_value(axes_values, current_axis_index, current_axis_id):
    axes_dictionary = dictionary_copy(axes_values)
    if axes_dictionary is not None:
        if current_axis_id is None:
            return None
        return axes_dictionary.get(current_axis_id)

    try:
        axes_list = list(axes_values or [])
    except Exception:
        return None

    if len(axes_list) <= current_axis_index:
        return None
    return axes_list[current_axis_index]


def axes_values_with_axis_value(axes_values, current_axis_index, current_axis_id, value):
    axes_dictionary = dictionary_copy(axes_values)
    if axes_dictionary is not None:
        if current_axis_id is None:
            return axes_values
        axes_dictionary[current_axis_id] = value
        return axes_dictionary

    axes_list = list(axes_values or [])
    axes_list[current_axis_index] = value
    return axes_list


def set_wrapped_value(wrapped_value, value):
    for setter_name in ("setValue_", "setPosition_", "setPos_", "setFloatValue_"):
        setter = getattr(wrapped_value, setter_name, None)
        if callable(setter):
            try:
                setter(value)
                return True
            except Exception:
                pass

    for attribute_name in ("value", "position", "pos", "floatValue"):
        try:
            setattr(wrapped_value, attribute_name, value)
            return True
        except Exception:
            pass

    return False


def set_instance_axes_values(instance, axes_values):
    setter = getattr(instance, "setAxesValues_", None)
    if callable(setter):
        setter(axes_values)
    else:
        instance.axesValues = axes_values


def set_instance_axis_value(instance, axes_values, current_axis_index, current_axis_id, value):
    for setter_name in ("setAxisValueValue_forId_", "setAxisValue_forId_"):
        setter = getattr(instance, setter_name, None)
        if callable(setter):
            try:
                setter(value, current_axis_id)
                return True
            except Exception:
                pass

    axes_dictionary = dictionary_copy(axes_values)
    if axes_dictionary is not None and current_axis_id is not None:
        existing_value = axes_dictionary.get(current_axis_id)
        if existing_value is not None and set_wrapped_value(existing_value, value):
            return True

    updated_axes_values = axes_values_with_axis_value(
        axes_values,
        current_axis_index,
        current_axis_id,
        value,
    )
    set_instance_axes_values(instance, updated_axes_values)
    return True


def numeric_text_value(value, field_name):
    text = str(value).strip()
    if not text:
        raise ValueError("%s must not be empty." % field_name)
    try:
        numeric_value = float(text)
    except Exception:
        raise ValueError("%s must be a number." % field_name)
    if numeric_value.is_integer():
        return int(numeric_value)
    return numeric_value


def set_math_weight_on_static_instances(font, weight_offset, math_weight_maximum):
    weight_index = axis_index(font, WEIGHT_AXIS_NAME)
    math_index = axis_index(font, MATH_AXIS_NAME)
    weight_axis_id = axis_id_for_name(font, WEIGHT_AXIS_NAME)
    math_axis_id = axis_id_for_name(font, MATH_AXIS_NAME)

    Glyphs.clearLog()
    Glyphs.showMacroWindow()
    print("Set Math Weight on Static Instances")
    print("Math Weight = min(%s, Weight + %s)" % (math_weight_maximum, weight_offset))
    print("")

    font.disableUpdateInterface()

    updated_count = 0
    skipped_count = 0

    try:
        for instance in font.instances:
            axes_values = raw_instance_axes_values(instance)
            weight = axis_value(axes_values, weight_index, weight_axis_id)

            if weight is None:
                skipped_count += 1
                print("Skipping %s: no complete static axis values" % instance.name)
                continue

            math_weight = calculated_math_weight(weight, weight_offset, math_weight_maximum)
            set_instance_axis_value(
                instance,
                axes_values,
                math_index,
                math_axis_id,
                math_weight,
            )

            parameter = axis_location_parameter(instance)
            if parameter is None:
                parameter = GSCustomParameter(AXIS_LOCATION_PARAMETER_NAME, [])
                instance.customParameters.append(parameter)

            axis_locations = mutable_axis_locations(parameter.value)
            set_axis_location(axis_locations, MATH_AXIS_NAME, math_weight)
            parameter.value = axis_locations

            read_back_math_weight = axis_value(
                raw_instance_axes_values(instance),
                math_index,
                math_axis_id,
            )
            try:
                read_back_math_weight = number_value(read_back_math_weight)
            except Exception:
                pass

            updated_count += 1
            print("%s: Weight %s -> Math Weight %s; read back %s; Axis Location Math Weight %s" % (
                instance.name,
                weight,
                math_weight,
                read_back_math_weight,
                math_weight,
            ))

    finally:
        font.enableUpdateInterface()

    print("Done. Updated %s static instances; skipped %s other instances." % (
        updated_count,
        skipped_count,
    ))


class SetMathWeightWindow(object):
    def __init__(self):
        self.font = Glyphs.font
        if self.font is None:
            Glyphs.clearLog()
            Glyphs.showMacroWindow()
            print("No font open.")
            return

        self.w = vanilla.FloatingWindow((360, 148), "Set Math Weight on Static Instances")
        self.w.offsetLabel = vanilla.TextBox((15, 18, 145, 18), "Add to Weight")
        self.w.offsetValue = vanilla.EditText((170, 14, 80, 24), str(DEFAULT_WEIGHT_OFFSET))
        self.w.maximumLabel = vanilla.TextBox((15, 52, 145, 18), "Maximum Math Weight")
        self.w.maximumValue = vanilla.EditText((170, 48, 80, 24), str(DEFAULT_MATH_WEIGHT_MAXIMUM))
        self.w.status = vanilla.TextBox((15, 86, -15, 18), "Ready")
        self.w.applyButton = vanilla.Button((170, 110, -15, 24), "Set Math Weight", callback=self.apply_callback)
        self.w.open()
        self.w.makeKey()

    def set_status(self, text):
        try:
            self.w.status.set(text)
        except Exception:
            pass

    def apply_callback(self, sender):
        try:
            weight_offset = numeric_text_value(self.w.offsetValue.get(), "Add to Weight")
            math_weight_maximum = numeric_text_value(self.w.maximumValue.get(), "Maximum Math Weight")
        except ValueError as error:
            self.set_status(str(error))
            return

        set_math_weight_on_static_instances(self.font, weight_offset, math_weight_maximum)
        self.set_status("Done. See Macro panel.")


SetMathWeightWindow()
