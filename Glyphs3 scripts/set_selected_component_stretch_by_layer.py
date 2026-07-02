#MenuTitle: Set Selected Component Stretch by Layer
# -*- coding: utf-8 -*-

import vanilla
from GlyphsApp import Glyphs


SCRIPT_VERSION = "2026-07-01 14:30 CDT initial"
H_STRETCH = "hStretch"
V_STRETCH = "vStretch"
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
    value = clean_number(value)
    return str(value)


def numeric_value(value):
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except Exception:
        return None


def selected_layer(font):
    selected_layers = list(font.selectedLayers or [])
    if not selected_layers:
        return None
    return selected_layers[0]


def layer_name(layer):
    return str(safe_call(getattr(layer, "name", ""), "") or "")


def layer_id(layer):
    value = safe_call(getattr(layer, "layerId", None))
    if value is None:
        return ""
    return str(value)


def layer_label(layer):
    return layer_name(layer) or layer_id(layer) or "<unnamed layer>"


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


def component_glyph(font, component):
    glyph = safe_call(getattr(component, "component", None))
    if glyph is not None and safe_call(getattr(glyph, "name", None)):
        return glyph

    glyph = safe_call(getattr(component, "glyph", None))
    if glyph is not None and safe_call(getattr(glyph, "name", None)):
        return glyph

    name = component_name(component)
    try:
        return font.glyphs[name]
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


def axis_attribute_text(axis, attribute_name):
    value = safe_call(getattr(axis, attribute_name, None))
    if value is None:
        return ""
    return str(value).lower()


def axis_matches_role(axis, role):
    name = axis_name(axis).strip().lower().replace(" ", "").replace("_", "")
    if role == H_STRETCH:
        if name in ("hstretch", "horizontalstretch", "widthstretch", "width"):
            return True
    if role == V_STRETCH:
        if name in ("vstretch", "verticalstretch", "heightstretch", "height"):
            return True

    for attribute_name in ("orientation", "direction", "axis", "type"):
        text = axis_attribute_text(axis, attribute_name)
        if not text:
            continue
        if role == H_STRETCH and ("horizontal" in text or text in ("h", "x", "0")):
            return True
        if role == V_STRETCH and ("vertical" in text or text in ("v", "y", "1")):
            return True

    return False


def smart_axes(glyph):
    if glyph is None:
        return []
    try:
        return list(glyph.smartComponentAxes or [])
    except Exception:
        return []


def stretch_axes_for_component(font, component):
    glyph = component_glyph(font, component)
    axes = smart_axes(glyph)
    h_axis = None
    v_axis = None

    for axis in axes:
        if h_axis is None and axis_matches_role(axis, H_STRETCH):
            h_axis = axis
        if v_axis is None and axis_matches_role(axis, V_STRETCH):
            v_axis = axis

    stretch_axes = [axis for axis in axes if axis_name(axis).strip().lower() == "stretch"]
    if h_axis is None and len(stretch_axes) >= 1:
        h_axis = stretch_axes[0]
    if v_axis is None and len(stretch_axes) >= 2:
        v_axis = stretch_axes[1]

    return h_axis, v_axis


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
    if axis_id is None:
        return False

    value = clean_number(value)
    if not hasattr(component, "smartComponentValues"):
        return False

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


class SelectedComponentStretchByLayer(object):

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
            print_warning("Select one component in the current layer, then run the script.")
            return

        selected_components = layer_components(self.layer)
        if self.component_index >= len(selected_components):
            Glyphs.showMacroWindow()
            print_warning("The selected component index is no longer valid.")
            return

        self.component_name = component_name(selected_components[self.component_index])
        self.rows = []
        self.records = []
        self.is_updating = False
        self.build_rows()

        if not self.rows:
            Glyphs.showMacroWindow()
            print_warning("%s has no layers with component index %i." % (
                self.glyph.name,
                self.component_index + 1,
            ))
            return

        window_width = 640
        window_height = min(560, max(220, 92 + len(self.rows) * 24))
        self.w = vanilla.FloatingWindow(
            (window_width, window_height),
            "Set Component Stretch by Layer",
        )
        self.w.info = vanilla.TextBox(
            (15, 14, -15, 34),
            "%s / component %i: %s" % (
                self.glyph.name,
                self.component_index + 1,
                self.component_name,
            ),
        )
        self.w.table = vanilla.List(
            (15, 54, -15, -38),
            self.rows,
            columnDescriptions=[
                dict(title="Layer", key="layer", width=250, editable=False),
                dict(title="Component", key="component", width=130, editable=False),
                dict(title="hStretch", key=H_STRETCH, width=80, editable=True),
                dict(title="vStretch", key=V_STRETCH, width=80, editable=True),
                dict(title="Status", key="status", editable=False),
            ],
            editCallback=self.edit_callback,
        )
        self.w.status = vanilla.TextBox((15, -28, -15, 18), "Ready")
        self.w.open()
        self.w.makeKey()

        Glyphs.showMacroWindow()
        print("Set Selected Component Stretch by Layer")
        print("Script version: %s" % SCRIPT_VERSION)
        print("Glyph: %s" % self.glyph.name)
        print("Selected component index: %i" % (self.component_index + 1))
        print("Selected component name: %s" % self.component_name)
        print("Rows: %i" % len(self.rows))

    def build_rows(self):
        for row_index, layer in enumerate(self.glyph.layers):
            components = layer_components(layer)
            if self.component_index >= len(components):
                self.records.append(dict(layer=layer, component=None, hAxis=None, vAxis=None))
                self.rows.append(dict(
                    rowIndex=row_index,
                    layer=layer_label(layer),
                    component="",
                    hStretch="",
                    vStretch="",
                    status="missing component",
                ))
                continue

            component = components[self.component_index]
            h_axis, v_axis = stretch_axes_for_component(self.font, component)
            h_value = component_axis_value(component, h_axis) if h_axis is not None else None
            v_value = component_axis_value(component, v_axis) if v_axis is not None else None
            status_parts = []
            if h_axis is None:
                status_parts.append("no h axis")
            if v_axis is None:
                status_parts.append("no v axis")

            self.records.append(dict(layer=layer, component=component, hAxis=h_axis, vAxis=v_axis))
            self.rows.append(dict(
                rowIndex=row_index,
                layer=layer_label(layer),
                component=component_name(component),
                hStretch=format_number(h_value),
                vStretch=format_number(v_value),
                status=", ".join(status_parts) or "ok",
            ))

    def set_status(self, text):
        try:
            self.w.status.set(text)
        except Exception:
            pass

    def edit_callback(self, sender):
        if self.is_updating:
            return

        try:
            rows = list(sender.get())
        except Exception:
            rows = list(sender)
        changed = 0
        skipped = 0

        self.font.disableUpdateInterface()
        if hasattr(self.glyph, "beginUndo"):
            self.glyph.beginUndo()
        try:
            for index, row in enumerate(rows):
                if index >= len(self.records):
                    continue

                record = self.records[index]
                component = record["component"]
                if component is None:
                    skipped += 1
                    continue

                h_value = numeric_value(row.get(H_STRETCH, ""))
                v_value = numeric_value(row.get(V_STRETCH, ""))

                if h_value is not None and record["hAxis"] is not None:
                    if set_component_axis_value(component, record["hAxis"], h_value):
                        changed += 1
                    else:
                        skipped += 1
                elif str(row.get(H_STRETCH, "")).strip():
                    skipped += 1

                if v_value is not None and record["vAxis"] is not None:
                    if set_component_axis_value(component, record["vAxis"], v_value):
                        changed += 1
                    else:
                        skipped += 1
                elif str(row.get(V_STRETCH, "")).strip():
                    skipped += 1
        finally:
            if hasattr(self.glyph, "endUndo"):
                self.glyph.endUndo()
            self.font.enableUpdateInterface()

        refresh_font(self.font)
        self.set_status("Updated %i value(s)%s." % (
            changed,
            "; skipped %i" % skipped if skipped else "",
        ))


SelectedComponentStretchByLayer()
