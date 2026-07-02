#MenuTitle: Set Selected Component Axis Low/High
# -*- coding: utf-8 -*-

import vanilla
from GlyphsApp import Glyphs


SCRIPT_VERSION = "2026-07-02 10:20 CDT initial"
DEFAULT_AXIS_NAME = "height"
AXIS_TOLERANCE = 0.000001


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
    try:
        number = float(value)
    except Exception:
        return value
    if abs(number - round(number)) <= AXIS_TOLERANCE:
        return int(round(number))
    return number


def format_number(value):
    if value is None:
        return ""
    return str(clean_number(value))


def numeric_value(value):
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except Exception:
        return None


def selected_layer(font):
    try:
        selected_layers = list(font.selectedLayers or [])
    except Exception:
        selected_layers = []
    return selected_layers[0] if selected_layers else None


def layer_name(layer):
    return str(safe_call(getattr(layer, "name", None), "") or "")


def layer_label(layer):
    return layer_name(layer) or str(safe_call(getattr(layer, "layerId", None), "") or "<unnamed layer>")


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

    for attribute_name in ("component", "glyph"):
        glyph = safe_call(getattr(component, attribute_name, None))
        if glyph is not None:
            value = safe_call(getattr(glyph, "name", None))
            if value:
                return str(value)
    return "<unnamed component>"


def component_glyph(font, component):
    for attribute_name in ("component", "glyph"):
        glyph = safe_call(getattr(component, attribute_name, None))
        if glyph is not None and safe_call(getattr(glyph, "name", None)):
            return glyph

    try:
        return font.glyphs[component_name(component)]
    except Exception:
        return None


def selected_component_index(layer):
    components = layer_components(layer)
    try:
        selection = list(layer.selection or [])
    except Exception:
        selection = []

    for selected in selection:
        for index, component in enumerate(components):
            if selected is component or selected == component:
                return index

    for index, component in enumerate(components):
        if bool(safe_call(getattr(component, "selected", False), False)):
            return index
    return None


def axis_identifier(axis):
    for attribute_name in ("id", "axisId"):
        value = safe_call(getattr(axis, attribute_name, None))
        if value:
            return str(value)
    return None


def axis_name(axis):
    return str(safe_call(getattr(axis, "name", None), "") or "")


def smart_axes(glyph):
    if glyph is None:
        return []
    try:
        return list(glyph.smartComponentAxes or [])
    except Exception:
        return []


def smart_axis_for_name(glyph, wanted_name):
    wanted = str(wanted_name).strip().lower()
    for axis in smart_axes(glyph):
        if axis_name(axis).strip().lower() == wanted:
            return axis
    return None


def axis_default_value(axis):
    if axis is None:
        return None
    for attribute_name in ("bottomValue", "topValue"):
        value = numeric_value(safe_call(getattr(axis, attribute_name, None)))
        if value is not None:
            return value
    return None


def component_axis_value(component, axis):
    axis_id = axis_identifier(axis)
    name = axis_name(axis)
    try:
        values = dict(component.smartComponentValues or {})
    except Exception:
        values = {}
    for key in (axis_id, name):
        if key in values:
            value = numeric_value(values[key])
            if value is not None:
                return value
    return axis_default_value(axis)


def set_component_axis_value(component, axis, value):
    axis_id = axis_identifier(axis)
    if axis_id is None or not hasattr(component, "smartComponentValues"):
        return False

    value = clean_number(value)
    try:
        component.smartComponentValues[axis_id] = value
        return True
    except Exception:
        pass

    try:
        values = dict(component.smartComponentValues or {})
        values[axis_id] = value
        component.smartComponentValues = values
        return True
    except Exception:
        return False


def is_master_layer(layer, font):
    layer_id = safe_call(getattr(layer, "layerId", None))
    try:
        masters = list(font.masters)
    except Exception:
        masters = []
    for master in masters:
        master_id = safe_call(getattr(master, "id", None))
        if layer_id == master_id:
            return True
    return False


def is_high_layer(layer):
    return "high" in layer_name(layer).lower()


def refresh_font(font):
    for method_name in ("updateFeatures", "refresh", "updateGlyphInfo"):
        method = getattr(font, method_name, None)
        if method is not None:
            try:
                method()
                return
            except Exception:
                pass
    try:
        Glyphs.redraw()
    except Exception:
        pass


class SelectedComponentAxisLowHigh(object):

    def __init__(self):
        self.font = Glyphs.font
        if self.font is None:
            Glyphs.showMacroWindow()
            print_warning("No font open.")
            return

        self.layer = selected_layer(self.font)
        if self.layer is None:
            Glyphs.showMacroWindow()
            print_warning("No layer selected.")
            return

        self.glyph = self.layer.parent
        self.component_index = selected_component_index(self.layer)
        if self.component_index is None:
            Glyphs.showMacroWindow()
            print_warning("Select one smart component in the current layer, then run the script.")
            return

        components = layer_components(self.layer)
        if self.component_index >= len(components):
            Glyphs.showMacroWindow()
            print_warning("The selected component index is no longer valid.")
            return

        self.component = components[self.component_index]
        self.component_name = component_name(self.component)
        self.component_glyph = component_glyph(self.font, self.component)
        self.axis_names = [axis_name(axis) for axis in smart_axes(self.component_glyph) if axis_name(axis)]
        if not self.axis_names:
            Glyphs.showMacroWindow()
            print_warning("%s is not a smart component or has no smart axes." % self.component_name)
            return

        try:
            axis_index = self.axis_names.index(DEFAULT_AXIS_NAME)
        except ValueError:
            axis_index = 0

        axis = smart_axis_for_name(self.component_glyph, self.axis_names[axis_index])
        current_value = component_axis_value(self.component, axis)

        self.w = vanilla.FloatingWindow((430, 188), "Set Component Axis Low/High")
        self.w.info = vanilla.TextBox(
            (15, 14, -15, 34),
            "%s / component %i: %s" % (
                self.glyph.name,
                self.component_index + 1,
                self.component_name,
            ),
        )
        self.w.axisLabel = vanilla.TextBox((15, 58, 72, 18), "Axis")
        self.w.axis = vanilla.PopUpButton((90, 54, 150, 24), self.axis_names, callback=self.axis_changed)
        self.w.axis.set(axis_index)
        self.w.lowLabel = vanilla.TextBox((15, 90, 72, 18), "Masters")
        self.w.lowValue = vanilla.EditText((90, 86, 90, 24), format_number(current_value if current_value is not None else 0))
        self.w.highLabel = vanilla.TextBox((205, 90, 82, 18), "High layers")
        self.w.highValue = vanilla.EditText((292, 86, 90, 24), "100")
        self.w.applyButton = vanilla.Button((292, 124, 90, 24), "Apply", callback=self.apply_callback)
        self.w.status = vanilla.TextBox((15, -30, -15, 18), "Ready")
        self.w.open()
        self.w.makeKey()

    def current_axis(self):
        try:
            axis_name_value = self.axis_names[int(self.w.axis.get())]
        except Exception:
            axis_name_value = DEFAULT_AXIS_NAME
        return smart_axis_for_name(self.component_glyph, axis_name_value)

    def axis_changed(self, sender):
        axis = self.current_axis()
        value = component_axis_value(self.component, axis)
        try:
            self.w.lowValue.set(format_number(value if value is not None else 0))
        except Exception:
            pass

    def set_status(self, text):
        try:
            self.w.status.set(text)
        except Exception:
            pass

    def apply_callback(self, sender):
        axis = self.current_axis()
        if axis is None:
            self.set_status("No matching smart axis.")
            return

        low_value = numeric_value(self.w.lowValue.get())
        high_value = numeric_value(self.w.highValue.get())
        if low_value is None or high_value is None:
            self.set_status("Enter numeric values for both fields.")
            return

        changed = 0
        skipped = 0
        high_layers = 0
        master_layers = 0

        self.font.disableUpdateInterface()
        if hasattr(self.glyph, "beginUndo"):
            self.glyph.beginUndo()
        try:
            for layer in self.glyph.layers:
                components = layer_components(layer)
                if self.component_index >= len(components):
                    skipped += 1
                    continue

                if is_high_layer(layer):
                    value = high_value
                    high_layers += 1
                elif is_master_layer(layer, self.font):
                    value = low_value
                    master_layers += 1
                else:
                    continue

                if set_component_axis_value(components[self.component_index], axis, value):
                    changed += 1
                else:
                    skipped += 1
        finally:
            if hasattr(self.glyph, "endUndo"):
                self.glyph.endUndo()
            self.font.enableUpdateInterface()

        refresh_font(self.font)
        self.set_status("Updated %i component%s (%i master, %i High)%s." % (
            changed,
            "" if changed == 1 else "s",
            master_layers,
            high_layers,
            "; skipped %i" % skipped if skipped else "",
        ))


SelectedComponentAxisLowHigh()
