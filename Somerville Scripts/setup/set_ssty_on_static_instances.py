#MenuTitle: Set SSTY on Static Instances
# -*- coding: utf-8 -*-

import re

from GlyphsApp import Glyphs, GSCustomParameter


SOURCE_AXIS_NAME = "Optical size"
SOURCE_AXIS_TAG = "opsz"
STYA_AXIS_TAG = "STYA"
STYB_AXIS_TAG = "STYB"
AXIS_LOCATION_PARAMETER_NAME = "Axis Location"
SCRIPT_VERSION = "2026-07-09 10:33 CDT json-ssty-design-map"

SSTY_DESIGN_MAP = [
    {"opsz_external": 5, "opsz_design": 5, "ssty1_external": 5, "ssty1_design": 5, "ssty2_external": 5, "ssty2_design": 5},
    {"opsz_external": 6, "opsz_design": 200, "ssty1_external": 5, "ssty1_design": 5, "ssty2_external": 5, "ssty2_design": 5},
    {"opsz_external": 7, "opsz_design": 325, "ssty1_external": 5.25, "ssty1_design": 53, "ssty2_external": 5, "ssty2_design": 5},
    {"opsz_external": 8, "opsz_design": 400, "ssty1_external": 6.0, "ssty1_design": 197, "ssty2_external": 5, "ssty2_design": 5},
    {"opsz_external": 12, "opsz_design": 550, "ssty1_external": 9.0, "ssty1_design": 450, "ssty2_external": 7.2, "ssty2_design": 342},
    {"opsz_external": 16, "opsz_design": 640, "ssty1_external": 12.0, "ssty1_design": 640, "ssty2_external": 9.6, "ssty2_design": 481},
    {"opsz_external": 21, "opsz_design": 700, "ssty1_external": 15.75, "ssty1_design": 696, "ssty2_external": 12.6, "ssty2_design": 649},
    {"opsz_external": 32, "opsz_design": 800, "ssty1_external": 24.0, "ssty1_design": 837, "ssty2_external": 19.2, "ssty2_design": 802},
    {"opsz_external": 41, "opsz_design": 860, "ssty1_external": 30.75, "ssty1_design": 890, "ssty2_external": 24.6, "ssty2_design": 842},
    {"opsz_external": 48, "opsz_design": 900, "ssty1_external": 36.0, "ssty1_design": 925, "ssty2_external": 28.8, "ssty2_design": 874},
    {"opsz_external": 72, "opsz_design": 980, "ssty1_external": 54.0, "ssty1_design": 1002, "ssty2_external": 43.2, "ssty2_design": 969},
    {"opsz_external": 96, "opsz_design": 1020, "ssty1_external": 72.0, "ssty1_design": 1009, "ssty2_external": 57.6, "ssty2_design": 1003},
    {"opsz_external": 1200, "opsz_design": 1200, "ssty1_external": 900.0, "ssty1_design": 1151, "ssty2_external": 720.0, "ssty2_design": 1122},
]


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


def axis_name(axis):
    value = safe_call(getattr(axis, "name", None))
    if value:
        return str(value)
    return ""


def axis_info(font, axis_name_value=None, axis_tag_value=None):
    for index, axis in enumerate(font.axes):
        current_name = axis_name(axis)
        current_tag = axis_tag(axis)
        if axis_name_value is not None and current_name == axis_name_value:
            return dict(index=index, id=axis_id(axis), name=current_name, tag=current_tag)
        if axis_tag_value is not None and current_tag == axis_tag_value:
            return dict(index=index, id=axis_id(axis), name=current_name, tag=current_tag)

    labels = []
    if axis_name_value is not None:
        labels.append("name %r" % axis_name_value)
    if axis_tag_value is not None:
        labels.append("tag %r" % axis_tag_value)
    raise ValueError("Could not find axis with %s" % " or ".join(labels))


def number_value(value):
    for attribute_name in ("value", "position", "pos", "floatValue"):
        attribute_value = getattr(value, attribute_name, None)
        if attribute_value is None:
            continue
        attribute_value = safe_call(attribute_value, attribute_value)
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


def cleaned_number(value):
    value = float(value)
    rounded_integer = round(value)
    if abs(value - rounded_integer) < 0.000001:
        return int(rounded_integer)
    return round(value, 6)


def matching_ssty_design_row(opz_value):
    opz_design = cleaned_number(number_value(opz_value))
    for row in SSTY_DESIGN_MAP:
        if cleaned_number(row["opsz_design"]) == opz_design:
            return row
    raise ValueError("no SSTY design-map row for %s=%s" % (SOURCE_AXIS_TAG, opz_design))


def ssty_values_for_opz(opz_value):
    row = matching_ssty_design_row(opz_value)
    return dict(
        opsz_design=cleaned_number(row["opsz_design"]),
        opsz_external=cleaned_number(row["opsz_external"]),
        stya=cleaned_number(row["ssty1_design"]),
        styb=cleaned_number(row["ssty2_design"]),
        stya_external=cleaned_number(row["ssty1_external"]),
        styb_external=cleaned_number(row["ssty2_external"]),
    )


def axis_location_parameter(instance):
    for parameter in instance.customParameters:
        if parameter.name == AXIS_LOCATION_PARAMETER_NAME:
            return parameter
    return None


def mutable_axis_locations(value):
    if not value:
        return []
    return [dict(location) for location in value]


def set_axis_location(axis_locations, axis_name_value, location_value):
    for location in axis_locations:
        if location.get("Axis") == axis_name_value:
            location["Location"] = location_value
            return
    axis_locations.append({
        "Axis": axis_name_value,
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
        return axes_dictionary.get(current_axis_id) or axes_dictionary.get(str(current_axis_id))

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
    while len(axes_list) <= current_axis_index:
        axes_list.append(0)
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
    if current_axis_id is not None:
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
        existing_value = axes_dictionary.get(current_axis_id) or axes_dictionary.get(str(current_axis_id))
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


def set_instance_axis_and_location(instance, axis, value):
    set_instance_axis_value(
        instance,
        raw_instance_axes_values(instance),
        axis["index"],
        axis["id"],
        value,
    )


def set_axis_locations(instance, values_by_axis_name):
    parameter = axis_location_parameter(instance)
    if parameter is None:
        parameter = GSCustomParameter(AXIS_LOCATION_PARAMETER_NAME, [])
        instance.customParameters.append(parameter)

    axis_locations = mutable_axis_locations(parameter.value)
    for axis_name_value, location_value in values_by_axis_name.items():
        set_axis_location(axis_locations, axis_name_value, location_value)
    parameter.value = axis_locations


font = Glyphs.font

Glyphs.clearLog()
Glyphs.showMacroWindow()
print("Set SSTY on Static Instances")
print("Script version: %s" % SCRIPT_VERSION)
print("SSTY design-map rows: %s" % len(SSTY_DESIGN_MAP))
print("")

if font is None:
    print("WARNING: No font open.")
else:
    source_axis = axis_info(font, SOURCE_AXIS_NAME, SOURCE_AXIS_TAG)
    stya_axis = axis_info(font, axis_tag_value=STYA_AXIS_TAG)
    styb_axis = axis_info(font, axis_tag_value=STYB_AXIS_TAG)

    font.disableUpdateInterface()

    updated_count = 0
    skipped_count = 0

    try:
        for instance in font.instances:
            axes_values = raw_instance_axes_values(instance)
            opz_value = axis_value(axes_values, source_axis["index"], source_axis["id"])

            if opz_value is None:
                skipped_count += 1
                print("Skipping %s: no complete static axis values" % instance.name)
                continue

            try:
                values = ssty_values_for_opz(opz_value)
            except Exception as error:
                skipped_count += 1
                print("Skipping %s: %s" % (instance.name, error))
                continue

            set_instance_axis_and_location(instance, stya_axis, values["stya"])
            set_instance_axis_and_location(instance, styb_axis, values["styb"])
            set_axis_locations(instance, {
                stya_axis["name"]: values["stya"],
                styb_axis["name"]: values["styb"],
            })

            read_back_stya = axis_value(
                raw_instance_axes_values(instance),
                stya_axis["index"],
                stya_axis["id"],
            )
            read_back_styb = axis_value(
                raw_instance_axes_values(instance),
                styb_axis["index"],
                styb_axis["id"],
            )
            try:
                read_back_stya = cleaned_number(number_value(read_back_stya))
            except Exception:
                pass
            try:
                read_back_styb = cleaned_number(number_value(read_back_styb))
            except Exception:
                pass

            updated_count += 1
            print("%s: %s design=%s external=%s; %s=%s (ssty1 external=%s, read back %s); %s=%s (ssty2 external=%s, read back %s)" % (
                instance.name,
                SOURCE_AXIS_TAG,
                values["opsz_design"],
                values["opsz_external"],
                stya_axis["name"],
                values["stya"],
                values["stya_external"],
                read_back_stya,
                styb_axis["name"],
                values["styb"],
                values["styb_external"],
                read_back_styb,
            ))

    finally:
        font.enableUpdateInterface()

    print("")
    print("Done. Updated %s static instances; skipped %s other instances." % (
        updated_count,
        skipped_count,
    ))
