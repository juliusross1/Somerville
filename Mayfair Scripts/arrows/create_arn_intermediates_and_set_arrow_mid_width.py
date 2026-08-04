#MenuTitle: Adjust Arrow.mid components in a smart way
# -*- coding: utf-8 -*-

"""Recreate two Arrow Length intermediates and set component width values.

For the currently selected glyph, this script first removes every existing
intermediate layer, then creates layers at the two requested Arrow Length
values under every master. It sets the ``width`` smart-axis value on
supported Arrow.mid smart components according to the associated master's width class
on both master and intermediate layers, and reports every final value.
"""

import uuid
import os
import plistlib

import vanilla
from GlyphsApp import Glyphs, Message


SCRIPT_VERSION = "2026-08-04 arrow-and-double-arrow-smart-components"
PREFS_PREFIX = "com.mayfairmath.createARNIntermediates.v2"
SUPPORTED_COMPONENTS = (
    "_smart.Arrow.mid",
    "_smart.DoubleArrow.mid",
)
SHORT_SHORT_REFERENCE_GLYPHS = {
    "_smart.Arrow.mid": "Arrow.mid.ShortShort",
    "_smart.DoubleArrow.mid": "DoubleArrow.mid.ShortShort",
}
SMART_AXIS_NAME = "width"
ARLN_MAXIMUM_CONSTANT = "ARLNmaximum"
CONSTANTS_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "recipes", "recipe_constants.plist")
)


def clean_number(value):
    value = float(value)
    if value.is_integer():
        return int(value)
    return value


def format_number(value):
    return str(clean_number(value))


def axis_identifier(axis):
    for attribute_name in ("id", "axisId"):
        try:
            value = getattr(axis, attribute_name)
            if callable(value):
                value = value()
            if value:
                return str(value)
        except Exception:
            pass
    return None


def axis_name(axis):
    try:
        return str(axis.name or "")
    except Exception:
        return ""


def axis_tag(axis):
    try:
        return str(axis.axisTag or "")
    except Exception:
        try:
            return str(axis.tag or "")
        except Exception:
            return ""


def find_arrow_length_axis(font):
    """Find ARN/ARLN, preferring the registered tag over the display name."""
    axes = list(font.axes)
    for wanted_tag in ("ARLN", "ARN"):
        for axis in axes:
            if axis_tag(axis).strip().upper() == wanted_tag:
                return axis
    for axis in axes:
        normalized = axis_name(axis).strip().lower().replace(" ", "")
        if normalized in ("arrowlength", "arn", "arln"):
            return axis
    return None


def master_coordinates(font, master):
    coordinates = {}
    for axis in font.axes:
        current_axis_id = axis_identifier(axis)
        if current_axis_id is None:
            raise RuntimeError("A font axis has no identifier.")
        try:
            value = master.axisValueValueForId_(current_axis_id)
        except Exception:
            axis_index = list(font.axes).index(axis)
            value = master.axesValues[axis_index]
        coordinates[current_axis_id] = float(value)
    return coordinates


def layer_attribute(layer, key):
    for attribute_name in ("attributes", "attributeForKey_"):
        try:
            owner = getattr(layer, attribute_name)
            if callable(owner):
                value = owner(key)
            else:
                value = owner[key]
            if value is not None:
                return value
        except Exception:
            pass
    return None


def set_layer_attribute(layer, key, value):
    try:
        layer.attributes[key] = value
        return
    except Exception:
        pass
    try:
        layer.setAttribute_forKey_(value, key)
        return
    except Exception:
        pass
    raise RuntimeError("Could not set layer attribute %s." % key)


def coordinates_dict(font, value):
    if value is None:
        return None
    if hasattr(value, "keys"):
        result = {}
        for key in value.keys():
            result[str(key)] = float(value[key])
        return result
    values = list(value)
    if len(values) != len(font.axes):
        return None
    return {
        axis_identifier(axis): float(values[index])
        for index, axis in enumerate(font.axes)
    }


def associated_master_id(layer):
    try:
        value = layer.associatedMasterId
        if value:
            return str(value)
    except Exception:
        pass
    return None


def is_master_layer(layer):
    try:
        return bool(layer.isMasterLayer)
    except Exception:
        return False


def remove_layer(glyph, layer):
    layer_id = None
    try:
        layer_id = str(layer.layerId)
    except Exception:
        pass
    if layer_id:
        try:
            del glyph.layers[layer_id]
            return True
        except Exception:
            pass
    for method_name in ("remove_", "removeObject_", "removeObject"):
        try:
            getattr(glyph.layers, method_name)(layer)
            return True
        except Exception:
            pass
    return False


def remove_all_intermediate_layers(glyph):
    """Remove non-master layers that carry designspace coordinates."""
    removed = []
    for layer in reversed(list(glyph.layers)):
        if is_master_layer(layer):
            continue
        if layer_attribute(layer, "coordinates") is None:
            continue
        try:
            label = str(layer.name or layer.layerId)
        except Exception:
            label = "unnamed layer"
        if not remove_layer(glyph, layer):
            raise RuntimeError("Could not remove intermediate layer %s." % label)
        removed.append(label)
    removed.reverse()
    return removed


def coordinates_match(first, second, tolerance=0.0001):
    if first is None or second is None or set(first) != set(second):
        return False
    return all(abs(first[key] - second[key]) <= tolerance for key in first)


def existing_intermediate(glyph, font, master_id, coordinates):
    for layer in glyph.layers:
        if is_master_layer(layer):
            continue
        if associated_master_id(layer) != str(master_id):
            continue
        current = coordinates_dict(font, layer_attribute(layer, "coordinates"))
        if coordinates_match(current, coordinates):
            return layer
    return None


def master_layer_for_glyph(glyph, master):
    try:
        return glyph.layers[master.id]
    except Exception:
        pass
    for layer in glyph.layers:
        try:
            if is_master_layer(layer) and str(layer.layerId) == str(master.id):
                return layer
        except Exception:
            pass
    return None


def make_intermediate_layer(glyph, font, master, arn_axis, arn_value):
    coordinates = master_coordinates(font, master)
    coordinates[axis_identifier(arn_axis)] = float(arn_value)
    existing = existing_intermediate(glyph, font, master.id, coordinates)
    if existing is not None:
        return existing, False

    source_layer = master_layer_for_glyph(glyph, master)
    if source_layer is None:
        raise RuntimeError("%s has no layer for master %s." % (glyph.name, master.name))
    new_layer = source_layer.copy()
    new_layer.layerId = str(uuid.uuid4()).upper()
    new_layer.associatedMasterId = master.id
    new_layer.name = "%s ARN=%s" % (master.name, format_number(arn_value))
    set_layer_attribute(new_layer, "coordinates", coordinates)
    glyph.layers.append(new_layer)
    return new_layer, True


def component_name(component):
    for attribute_name in ("componentName", "name"):
        try:
            value = getattr(component, attribute_name)
            if value:
                return str(value)
        except Exception:
            pass
    try:
        return str(component.component.name)
    except Exception:
        return None


def components_in_layer(layer):
    result = []
    try:
        shapes = list(layer.shapes)
    except Exception:
        shapes = []
    for shape in shapes:
        if component_name(shape) in SUPPORTED_COMPONENTS:
            result.append(shape)
    return result


def recipe_constant(name):
    try:
        with open(CONSTANTS_PATH, "rb") as handle:
            constants_plist = plistlib.load(handle)
        constants = constants_plist.get("constants", {})
        if name not in constants:
            raise RuntimeError("Constant %s is not defined." % name)
        return float(constants[name])
    except Exception as error:
        raise RuntimeError(
            "Could not read %s from %s: %s"
            % (name, CONSTANTS_PATH, error)
        )


def component_smart_axis(component):
    """Return the referenced smart glyph's Glyphs 4 width axis."""
    try:
        axes = list(component.component.axes or [])
    except Exception:
        axes = []
    for axis in axes:
        if axis_name(axis).strip().lower() == SMART_AXIS_NAME:
            return axis
    return None


def smart_values_dict(component):
    try:
        return dict(component.smartComponentValues or {})
    except Exception:
        return {}


def read_component_smart_value(component):
    """Read only an explicitly stored smart value, never an inherited value."""
    axis = component_smart_axis(component)
    if axis is None:
        return None
    values = smart_values_dict(component)
    for key in (axis_identifier(axis), axis_name(axis)):
        if key in values:
            try:
                return float(values[key])
            except Exception:
                return values[key]
    return None


def set_component_smart_value(component, value):
    axis = component_smart_axis(component)
    if axis is None:
        raise RuntimeError(
            "%s has no smart axis named %s."
            % (component_name(component) or "Component", SMART_AXIS_NAME)
        )
    axis_key = axis_identifier(axis)
    if axis_key is None:
        raise RuntimeError("The %s smart axis has no identifier." % SMART_AXIS_NAME)
    value = float(value)
    # Glyphs 4 exposes smart axes through glyph.axes, but component instances
    # still store their explicit selections in smartComponentValues by axis ID.
    values = smart_values_dict(component)
    values[axis_key] = value
    try:
        component.smartComponentValues = values
    except Exception:
        try:
            component.smartComponentValues[axis_key] = value
        except Exception:
            raise RuntimeError("Could not store %s in smartComponentValues." % SMART_AXIS_NAME)

    actual = read_component_smart_value(component)
    try:
        matches = abs(float(actual) - value) < 0.0001
    except Exception:
        matches = False
    if not matches:
        raise RuntimeError(
            "Could not verify explicit %s %s: requested %s, "
            "smartComponentValues=%s."
            % (
                component_name(component),
                SMART_AXIS_NAME,
                format_number(value),
                smart_values_dict(component),
            )
        )
    return actual


def master_width_class(master):
    name = str(master.name or "").lower()
    if "semicondens" in name:  # accepts SemiCondensed and the common misspelling
        return "condensed"
    if "semiexpand" in name:
        return "expanded"
    return None


class ARNIntermediateWindow(object):
    def __init__(self):
        self.initial_glyph = self.selected_glyph()
        self.b_calculation = self.calculate_b_default(self.initial_glyph)
        calculated_b = self.b_calculation.get("r")
        b_fallback = format_number(calculated_b) if calculated_b is not None else "50"
        self.w = vanilla.FloatingWindow(
            (460, 380),
            "ARLN Intermediates and Smart Mid Width",
        )
        self.w.intro = vanilla.TextBox(
            (15, 14, -15, 36),
            "Set master component widths and optionally recreate two ARLN intermediate layers.",
        )
        self.w.adjustMasters = vanilla.CheckBox(
            (15, 56, -15, 20),
            "Adjust component widths on the actual master layers",
            value=self.boolean_preference("adjustMasters", True),
            callback=self.update_enabled_controls,
        )
        self.w.condensedMasterLabel = vanilla.TextBox(
            (28, 88, 120, 18), "SemiCondensed"
        )
        self.w.condensedMaster = vanilla.EditText(
            (150, 84, 85, 24), self.preference("MC", "0")
        )
        self.w.expandedMasterLabel = vanilla.TextBox(
            (250, 88, 110, 18), "SemiExpanded"
        )
        self.w.expandedMaster = vanilla.EditText(
            (365, 84, 80, 24), self.preference("ME", "0")
        )

        self.w.arnHeading = vanilla.TextBox((15, 126, -15, 18), "ARLN intermediate-layer values")
        self.w.createA = vanilla.CheckBox(
            (28, 154, 120, 20),
            "Create A layer",
            value=self.boolean_preference("createA", True),
            callback=self.update_enabled_controls,
        )
        self.w.a = vanilla.EditText((150, 151, 85, 24), self.preference("A", "0"))
        self.w.createB = vanilla.CheckBox(
            (250, 154, 112, 20),
            "Create B layer",
            value=self.boolean_preference("createB", True),
            callback=self.update_enabled_controls,
        )
        self.w.b = vanilla.EditText(
            (365, 151, 80, 24),
            self.preference("B", b_fallback, calculated_default=True),
        )

        self.w.axisHeading = vanilla.TextBox(
            (15, 193, -15, 18),
            "Smart mid-component axis value: width",
        )
        self.w.tableA = vanilla.TextBox((197, 220, 95, 18), "At ARLN = A")
        self.w.tableB = vanilla.TextBox((330, 220, 95, 18), "At ARLN = B")
        self.w.condensedLabel = vanilla.TextBox((28, 249, 155, 18), "SemiCondensed masters")
        self.w.c1 = vanilla.EditText((195, 245, 90, 24), self.preference("C1", "0"))
        self.w.d1 = vanilla.EditText((330, 245, 90, 24), self.preference("D1", "0"))
        self.w.expandedLabel = vanilla.TextBox((28, 283, 155, 18), "SemiExpanded masters")
        self.w.c2 = vanilla.EditText((195, 279, 90, 24), self.preference("C2", "0"))
        self.w.d2 = vanilla.EditText((330, 279, 90, 24), self.preference("D2", "0"))

        self.w.status = vanilla.TextBox((15, 337, 290, 18), "Ready")
        self.w.applyButton = vanilla.Button((315, 331, 130, 28), "Create / Update", callback=self.apply)
        self.update_enabled_controls()
        self.w.open()
        self.w.makeKey()

    def update_enabled_controls(self, sender=None):
        adjust_masters = bool(self.w.adjustMasters.get())
        create_a = bool(self.w.createA.get())
        create_b = bool(self.w.createB.get())
        for control in (self.w.condensedMaster, self.w.expandedMaster):
            control.enable(adjust_masters)
        for control in (self.w.a, self.w.tableA, self.w.c1, self.w.c2):
            control.enable(create_a)
        for control in (self.w.b, self.w.tableB, self.w.d1, self.w.d2):
            control.enable(create_b)

    def selected_glyph(self):
        try:
            layers = list(Glyphs.font.selectedLayers or [])
            return layers[0].parent if layers else None
        except Exception:
            return None

    def preference(self, key, fallback, calculated_default=False):
        if calculated_default:
            return fallback
        try:
            value = Glyphs.defaults["%s.%s" % (PREFS_PREFIX, key)]
            if value is not None:
                return str(value)
        except Exception:
            pass
        return fallback

    def calculate_b_default(self, glyph):
        result = {"c": None, "masters": [], "r": None, "warnings": []}
        print("Calculating the default B-layer ARLN value (r):")
        print("  Formula for each master: (b - a) * c / b")
        print("  Supported smart components: %s" % ", ".join(SUPPORTED_COMPONENTS))
        print("  a = supported component width in the selected glyph")
        print("  b = matching component width in its ShortShort reference glyph")
        if glyph is None or Glyphs.font is None:
            result["warnings"].append("No selected glyph was available for the B calculation.")
            print("  ERROR: %s" % result["warnings"][-1])
            return result
        try:
            result["c"] = recipe_constant(ARLN_MAXIMUM_CONSTANT)
            print(
                "  c = %s (constant %s)"
                % (format_number(result["c"]), ARLN_MAXIMUM_CONSTANT)
            )
        except Exception as error:
            result["warnings"].append(str(error))
            print("  ERROR: %s" % result["warnings"][-1])
            return result
        calculated_values = []
        for master in Glyphs.font.masters:
            print("  Master: %s" % master.name)
            try:
                source_layer = master_layer_for_glyph(glyph, master)
                source_components = components_in_layer(source_layer) if source_layer is not None else []
                if not source_components:
                    raise RuntimeError(
                        "selected glyph has none of: %s" % ", ".join(SUPPORTED_COMPONENTS)
                    )
                source_component = source_components[0]
                source_component_name = component_name(source_component)
                reference_glyph_name = SHORT_SHORT_REFERENCE_GLYPHS[source_component_name]
                try:
                    reference_glyph = Glyphs.font.glyphs[reference_glyph_name]
                except Exception:
                    reference_glyph = None
                if reference_glyph is None:
                    raise RuntimeError("missing reference glyph %s" % reference_glyph_name)
                reference_layer = master_layer_for_glyph(reference_glyph, master)
                reference_components = components_in_layer(reference_layer) if reference_layer is not None else []
                reference_components = [
                    component
                    for component in reference_components
                    if component_name(component) == source_component_name
                ]
                if not reference_components:
                    raise RuntimeError(
                        "%s has no %s component"
                        % (reference_glyph_name, source_component_name)
                    )
                a = read_component_smart_value(source_component)
                b = read_component_smart_value(reference_components[0])
                if a is None:
                    raise RuntimeError(
                        "selected glyph's %s has no explicit width value"
                        % source_component_name
                    )
                if b is None:
                    raise RuntimeError(
                        "%s component has no explicit width value" % reference_glyph_name
                    )
                a = float(a)
                b = float(b)
                if abs(b) < 0.0001:
                    raise RuntimeError("b is zero")
                calculated = (b - a) * result["c"] / b
                running_minimum = min(calculated_values + [calculated])
                result["masters"].append(
                    {
                        "name": master.name,
                        "a": a,
                        "b": b,
                        "value": calculated,
                        "runningMinimum": running_minimum,
                        "component": source_component_name,
                        "referenceGlyph": reference_glyph_name,
                    }
                )
                calculated_values.append(calculated)
                print("    component = %s" % source_component_name)
                print("    ShortShort reference glyph = %s" % reference_glyph_name)
                print("    a = %s" % format_number(a))
                print("    b = %s" % format_number(b))
                print("    b - a = %s" % format_number(b - a))
                print(
                    "    (%s - %s) * %s / %s = %s"
                    % tuple(
                        format_number(value)
                        for value in (b, a, result["c"], b, calculated)
                    )
                )
                print("    running minimum = %s" % format_number(running_minimum))
            except Exception as error:
                result["warnings"].append("%s: %s" % (master.name, error))
                print("    ERROR: %s" % error)
        if calculated_values:
            result["r"] = min(calculated_values)
            print("  Final r = minimum across all masters = %s" % format_number(result["r"]))
        else:
            print("  Final r could not be calculated: no master produced a value.")
        return result

    def boolean_preference(self, key, fallback):
        try:
            value = Glyphs.defaults["%s.%s" % (PREFS_PREFIX, key)]
            if value is not None:
                return bool(value)
        except Exception:
            pass
        return fallback

    def read_values(self):
        controls = {
            "A": self.w.a,
            "B": self.w.b,
            "C1": self.w.c1,
            "D1": self.w.d1,
            "C2": self.w.c2,
            "D2": self.w.d2,
            "MC": self.w.condensedMaster,
            "ME": self.w.expandedMaster,
        }
        values = {}
        for key, control in controls.items():
            try:
                values[key] = float(str(control.get()).strip())
            except Exception:
                raise ValueError("%s must be a number." % key)
        values["createA"] = bool(self.w.createA.get())
        values["createB"] = bool(self.w.createB.get())
        values["adjustMasters"] = bool(self.w.adjustMasters.get())
        if values["createA"] and values["createB"] and abs(values["A"] - values["B"]) < 0.0001:
            raise ValueError("A and B must be different Arrow Length values.")
        for key in controls:
            Glyphs.defaults["%s.%s" % (PREFS_PREFIX, key)] = format_number(values[key])
        for key in ("createA", "createB", "adjustMasters"):
            Glyphs.defaults["%s.%s" % (PREFS_PREFIX, key)] = values[key]
        return values

    def apply(self, sender):
        font = Glyphs.font
        if font is None:
            Message("No Font Open", "Open a font and select a glyph first.")
            return
        try:
            selected_layers = list(font.selectedLayers or [])
            glyph = selected_layers[0].parent if selected_layers else None
        except Exception:
            glyph = None
        if glyph is None:
            Message("No Glyph Selected", "Select a glyph in Font View or Edit View first.")
            return

        arn_axis = find_arrow_length_axis(font)
        if arn_axis is None:
            Message(
                "Arrow Length Axis Not Found",
                "The font needs an axis tagged ARLN/ARN or named Arrow Length.",
            )
            return
        try:
            values = self.read_values()
        except ValueError as error:
            Message("Invalid Input", str(error))
            return

        created = 0
        reused = 0
        changed_components = 0
        removed_layers = []
        skipped_masters = []
        errors = []
        details = []
        processed_layers = []
        final_readback = []
        font.disableUpdateInterface()
        try:
            try:
                glyph.beginUndo()
            except Exception:
                pass
            try:
                removed_layers = remove_all_intermediate_layers(glyph)
                details.append("Removed %i existing intermediate layer(s)." % len(removed_layers))
                for removed_layer in removed_layers:
                    details.append("  removed: %s" % removed_layer)
            except Exception as error:
                errors.append("Removing existing intermediate layers: %s" % error)

            for master in font.masters:
                width_class = master_width_class(master)
                if width_class is None:
                    skipped_masters.append(master.name)
                elif values["adjustMasters"]:
                    try:
                        master_layer = master_layer_for_glyph(glyph, master)
                        if master_layer is None:
                            raise RuntimeError("No glyph layer exists for this master.")
                        master_value = values["MC" if width_class == "condensed" else "ME"]
                        processed_layers.append(
                            (master.name, "MASTER", master_layer, float(master_value))
                        )
                        master_components = components_in_layer(master_layer)
                        if not master_components:
                            details.append(
                                "%s | actual master layer | no supported smart component found (%s)"
                                % (master.name, ", ".join(SUPPORTED_COMPONENTS))
                            )
                        for component_index, component in enumerate(master_components, 1):
                            actual = set_component_smart_value(component, master_value)
                            changed_components += 1
                            details.append(
                                "%s | actual master layer | %s component %i: requested width=%s; "
                                "explicit read-back=%s; smartComponentValues=%s"
                                % (
                                    master.name,
                                    component_name(component),
                                    component_index,
                                    format_number(master_value),
                                    format_number(actual),
                                    smart_values_dict(component),
                                )
                            )
                    except Exception as error:
                        errors.append("%s / actual master layer: %s" % (master.name, error))
                else:
                    details.append(
                        "%s | actual master layer | width adjustment disabled in UI"
                        % master.name
                    )
                for arn_key in ("A", "B"):
                    if not values["create%s" % arn_key]:
                        details.append(
                            "%s | ARLN %s layer disabled in UI"
                            % (master.name, arn_key)
                        )
                        continue
                    try:
                        layer, did_create = make_intermediate_layer(
                            glyph, font, master, arn_axis, values[arn_key]
                        )
                        created += int(did_create)
                        reused += int(not did_create)
                        details.append(
                            "%s | ARLN %s=%s | %s layer: %s"
                            % (
                                master.name,
                                arn_key,
                                format_number(values[arn_key]),
                                "created" if did_create else "reused",
                                layer.name or layer.layerId,
                            )
                        )
                        if width_class is None:
                            details.append("  component width skipped: master is neither SemiCondensed nor SemiExpanded")
                            continue
                        if width_class == "condensed":
                            smart_value = values["C1" if arn_key == "A" else "D1"]
                        else:
                            smart_value = values["C2" if arn_key == "A" else "D2"]
                        processed_layers.append(
                            (master.name, arn_key, layer, float(smart_value))
                        )
                        components = components_in_layer(layer)
                        if not components:
                            details.append(
                                "  no supported smart component found (%s)"
                                % ", ".join(SUPPORTED_COMPONENTS)
                            )
                        for component_index, component in enumerate(components, 1):
                            actual = set_component_smart_value(component, smart_value)
                            changed_components += 1
                            details.append(
                                "  %s component %i: requested width=%s; explicit read-back=%s; smartComponentValues=%s (%s, ARLN %s)"
                                % (
                                    component_name(component),
                                    component_index,
                                    format_number(smart_value),
                                    format_number(actual),
                                    smart_values_dict(component),
                                    "SemiCondensed" if width_class == "condensed" else "SemiExpanded",
                                    arn_key,
                                )
                            )
                    except Exception as error:
                        errors.append("%s / ARLN %s: %s" % (master.name, arn_key, error))

            # Read every value again only after all layer creation and smart
            # component changes have finished. This catches settings that did
            # not persist beyond their immediate setter call.
            for master_name, location_key, layer, expected in processed_layers:
                components = components_in_layer(layer)
                if not components:
                    final_readback.append(
                        "%s | %s | no supported smart component found (%s)"
                        % (master_name, location_key, ", ".join(SUPPORTED_COMPONENTS))
                    )
                    continue
                for component_index, component in enumerate(components, 1):
                    actual = read_component_smart_value(component)
                    final_readback.append(
                        "%s | %s | %s component %i | requested width=%s | explicit actual=%s | smartComponentValues=%s"
                        % (
                            master_name,
                            location_key,
                            component_name(component),
                            component_index,
                            format_number(expected),
                            format_number(actual) if actual is not None else "not set",
                            smart_values_dict(component),
                        )
                    )
                    try:
                        matches = abs(float(actual) - expected) < 0.0001
                    except Exception:
                        matches = False
                    if not matches:
                        errors.append(
                            "%s / %s / component %i: requested width %s, final read-back %s"
                            % (
                                master_name,
                                location_key,
                                component_index,
                                format_number(expected),
                                actual,
                            )
                        )
            try:
                glyph.endUndo()
            except Exception:
                pass
        finally:
            font.enableUpdateInterface()

        print("Create ARLN Intermediates and Set Smart Mid Width")
        print("Script version: %s" % SCRIPT_VERSION)
        print("Glyph: %s" % glyph.name)
        print("Arrow Length axis: %s (%s)" % (axis_name(arn_axis), axis_tag(arn_axis)))
        print("Calculated B-layer ARLN default r: %s" % (
            format_number(self.b_calculation["r"])
            if self.b_calculation.get("r") is not None
            else "unavailable"
        ))
        for warning in self.b_calculation.get("warnings", []):
            print("  WARNING: %s" % warning)
        print(
            "ARLN A=%s (create=%s); ARLN B=%s (create=%s)"
            % (
                format_number(values["A"]),
                "yes" if values["createA"] else "no",
                format_number(values["B"]),
                "yes" if values["createB"] else "no",
            )
        )
        print(
            "SemiCondensed component widths: C1=%s at ARLN A; D1=%s at ARLN B"
            % (format_number(values["C1"]), format_number(values["D1"]))
        )
        print(
            "SemiExpanded component widths: C2=%s at ARLN A; D2=%s at ARLN B"
            % (format_number(values["C2"]), format_number(values["D2"]))
        )
        print(
            "Actual master-layer component widths: adjust=%s; SemiCondensed=%s; SemiExpanded=%s"
            % (
                "yes" if values["adjustMasters"] else "no",
                format_number(values["MC"]),
                format_number(values["ME"]),
            )
        )
        print("Removed existing intermediate layers: %i" % len(removed_layers))
        print("Details:")
        for detail in details:
            print(detail)
        print("Final smart mid-component width read-back:")
        if final_readback:
            for result in final_readback:
                print(result)
        else:
            print("No classified intermediate layers were available to inspect.")
        print("Created layers: %i" % created)
        print("Reused layers: %i" % reused)
        print("Updated supported smart mid components: %i" % changed_components)
        if skipped_masters:
            print("Skipped component-width assignment for unclassified masters: %s" % ", ".join(skipped_masters))
        for error in errors:
            print("WARNING: %s" % error)

        if errors:
            self.w.status.set("Finished with %i warning(s)" % len(errors))
        else:
            self.w.status.set(
                "Removed %i; created %i; updated %i"
                % (len(removed_layers), created, changed_components)
            )


ARNIntermediateWindow()
