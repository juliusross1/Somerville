#MenuTitle: Set Selected Component Scale and Height by Layer
# -*- coding: utf-8 -*-

"""
Edit the selected component's scale and height-axis value across every layer of
the current glyph.

Use this on a glyph that has the same component in the same component position
across its layers. Select that component in the current layer, run the script,
then edit the table rows for each layer:

- xScale: the component's horizontal scale.
- yScale: the component's vertical scale.
- height: the selected smart component's "height" axis value.

The script identifies the selected component by its component index in the
current layer. It then lists the component at that same index on every layer of
the glyph. Editing a row updates that layer immediately. Rows are marked when
the component is missing.

The "Fix yScale to xScale" checkbox is useful when the component should remain
proportionally scaled: changing xScale will keep yScale matched.
"""

import uuid
import vanilla
from AppKit import NSMakePoint
from Foundation import NSObject
from GlyphsApp import Glyphs


SCRIPT_VERSION = "2026-07-02 11:49 CDT unique-table-click-target"
HEIGHT_AXIS_NAME = "height"
AXIS_TOLERANCE = 0.000001
EDITABLE_COLUMNS = (1, 2, 3)


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


def layer_id(layer):
    value = safe_call(getattr(layer, "layerId", None))
    return str(value) if value is not None else ""


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


def scale_pair(component):
    scale = safe_call(getattr(component, "scale", None))
    if scale is not None:
        for x_name, y_name in (("x", "y"), ("width", "height")):
            try:
                return float(getattr(scale, x_name)), float(getattr(scale, y_name))
            except Exception:
                pass
        try:
            values = list(scale)
            if len(values) >= 2:
                return float(values[0]), float(values[1])
        except Exception:
            pass

    transform = safe_call(getattr(component, "transform", None))
    if transform is not None:
        try:
            return float(transform.m11), float(transform.m22)
        except Exception:
            pass
        try:
            values = list(transform)
            if len(values) >= 4:
                return float(values[0]), float(values[3])
        except Exception:
            pass
    return 1.0, 1.0


def set_component_scale(component, x_scale, y_scale):
    x_scale = clean_number(x_scale)
    y_scale = clean_number(y_scale)
    setter = getattr(component, "setScale_", None)
    for value in ((x_scale, y_scale), NSMakePoint(float(x_scale), float(y_scale))):
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


def select_layer_in_glyphs(font, layer):
    glyph = safe_call(getattr(layer, "parent", None))
    try:
        font.selectedLayers = [layer]
    except Exception:
        pass
    try:
        tab = font.currentTab
    except Exception:
        tab = None
    if tab is None and glyph is not None:
        try:
            tab = font.newTab(glyph.name)
        except Exception:
            tab = None
    if tab is not None:
        for method_name in ("setLayers_",):
            method = getattr(tab, method_name, None)
            if method is not None:
                try:
                    method([layer])
                    break
                except Exception:
                    pass
        try:
            tab.layers = [layer]
        except Exception:
            pass
        for attribute_name in ("selectedLayer", "activeLayer"):
            try:
                setattr(tab, attribute_name, layer)
            except Exception:
                pass
        for method_name in ("setSelectedLayer_", "setActiveLayer_"):
            method = getattr(tab, method_name, None)
            if method is not None:
                try:
                    method(layer)
                except Exception:
                    pass
        for value in (NSMakePoint(0, 0), 0):
            try:
                tab.selectedLayerOrigin = value
                break
            except Exception:
                pass
            method = getattr(tab, "setSelectedLayerOrigin_", None)
            if method is not None:
                try:
                    method(value)
                    break
                except Exception:
                    pass
        try:
            graphic_view = tab.graphicView()
        except Exception:
            graphic_view = None
        if graphic_view is not None:
            for method_name in ("setActiveLayer_", "setSelectedLayer_"):
                method = getattr(graphic_view, method_name, None)
                if method is not None:
                    try:
                        method(layer)
                    except Exception:
                        pass
    try:
        Glyphs.redraw()
    except Exception:
        pass


def vanilla_list_table_view(list_control):
    method = getattr(list_control, "getNSTableView", None)
    if method is not None:
        try:
            table_view = method()
            if table_view is not None:
                return table_view
        except Exception:
            pass

    for attribute_name in ("_nsObject", "_nsScrollView"):
        table_view = getattr(list_control, attribute_name, None)
        if table_view is None:
            continue
        if hasattr(table_view, "clickedRow"):
            return table_view
        document_view = getattr(table_view, "documentView", None)
        if document_view is not None:
            try:
                document_view = document_view()
            except Exception:
                pass
            if document_view is not None and hasattr(document_view, "clickedRow"):
                return document_view
    return None


def make_table_click_target(owner):
    class_name = "ScaleHeightTableClickTarget_%s" % uuid.uuid4().hex

    def initWithOwner_(self, owner):
        self = self.init()
        if self is None:
            return None
        self.owner = owner
        return self

    def tableClicked_(self, sender):
        try:
            self.owner.table_clicked(sender)
        except Exception:
            pass

    target_class = type(class_name, (NSObject,), {
        "__module__": __name__,
        "initWithOwner_": initWithOwner_,
        "tableClicked_": tableClicked_,
    })
    return target_class.alloc().initWithOwner_(owner)


class SelectedComponentScaleHeightByLayer(object):

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

        selected_components = layer_components(self.layer)
        if self.component_index >= len(selected_components):
            Glyphs.showMacroWindow()
            print_warning("The selected component index is no longer valid.")
            return

        selected_component = selected_components[self.component_index]
        self.component_name = component_name(selected_component)
        self.component_glyph = component_glyph(self.font, selected_component)
        self.height_axis = smart_axis_for_name(self.component_glyph, HEIGHT_AXIS_NAME)
        if self.height_axis is None:
            Glyphs.showMacroWindow()
            print_warning("%s has no smart axis named %s." % (self.component_name, HEIGHT_AXIS_NAME))
            return

        self.rows = []
        self.records = []
        self.is_updating = False
        self.table_click_target = None
        self.build_rows()
        if not self.rows:
            Glyphs.showMacroWindow()
            print_warning("%s has no layers with component index %i." % (
                self.glyph.name,
                self.component_index + 1,
            ))
            return

        window_width = 660
        window_height = min(620, max(240, 122 + len(self.rows) * 24))
        self.w = vanilla.FloatingWindow(
            (window_width, window_height),
            "Set Component Scale and Height by Layer",
        )
        self.w.info = vanilla.TextBox(
            (15, 14, -15, 34),
            "%s / component %i: %s" % (
                self.glyph.name,
                self.component_index + 1,
                self.component_name,
            ),
        )
        self.w.lockScale = vanilla.CheckBox(
            (15, 52, 210, 20),
            "Fix yScale to xScale",
            value=False,
            callback=self.lock_scale_changed,
        )
        self.w.table = vanilla.List(
            (15, 80, -15, -38),
            self.rows,
            columnDescriptions=[
                dict(title="Layer", key="layer", width=260, editable=False),
                dict(title="xScale", key="xScale", width=85, editable=True),
                dict(title="yScale", key="yScale", width=85, editable=True),
                dict(title="height", key="height", width=85, editable=True),
                dict(title="Status", key="status", editable=False),
            ],
            editCallback=self.edit_callback,
            selectionCallback=self.selection_callback,
        )
        self.w.status = vanilla.TextBox((15, -28, -15, 18), "Ready")
        self.configure_single_click_editing()
        self.w.open()
        self.w.makeKey()

        print("Set Selected Component Scale and Height by Layer")
        print("Script version: %s" % SCRIPT_VERSION)
        print("Glyph: %s" % self.glyph.name)
        print("Selected component index: %i" % (self.component_index + 1))
        print("Selected component name: %s" % self.component_name)
        print("Rows: %i" % len(self.rows))

    def build_rows(self):
        for row_index, layer in enumerate(self.glyph.layers):
            components = layer_components(layer)
            if self.component_index >= len(components):
                self.records.append(dict(layer=layer, component=None))
                self.rows.append(dict(
                    rowIndex=row_index,
                    layer=layer_label(layer),
                    xScale="",
                    yScale="",
                    height="",
                    status="missing component",
                ))
                continue

            component = components[self.component_index]
            x_scale, y_scale = scale_pair(component)
            height_value = component_axis_value(component, self.height_axis)
            self.records.append(dict(layer=layer, component=component))
            self.rows.append(dict(
                rowIndex=row_index,
                layer=layer_label(layer),
                xScale=format_number(x_scale),
                yScale=format_number(y_scale),
                height=format_number(height_value),
                status="ok",
            ))

    def set_status(self, text):
        try:
            self.w.status.set(text)
        except Exception:
            pass

    def selected_row_indexes(self, sender):
        try:
            return list(sender.getSelection())
        except Exception:
            pass
        table_view = vanilla_list_table_view(sender)
        if table_view is not None:
            try:
                indexes = table_view.selectedRowIndexes()
                if hasattr(indexes, "firstIndex"):
                    row = indexes.firstIndex()
                    rows = []
                    while row != 9223372036854775807:
                        rows.append(int(row))
                        row = indexes.indexGreaterThanIndex_(row)
                    return rows
                return list(indexes)
            except Exception:
                pass
            try:
                row = int(table_view.selectedRow())
                return [row] if row >= 0 else []
            except Exception:
                pass
        return []

    def configure_single_click_editing(self):
        table_view = vanilla_list_table_view(self.w.table)
        if table_view is None:
            return
        self.table_click_target = make_table_click_target(self)
        try:
            table_view.setTarget_(self.table_click_target)
            table_view.setAction_("tableClicked:")
        except Exception:
            pass

    def selection_callback(self, sender):
        if self.is_updating:
            return
        selected_rows = self.selected_row_indexes(sender)
        if not selected_rows:
            return
        row_index = int(selected_rows[0])
        if row_index < 0 or row_index >= len(self.records):
            return

        layer = self.records[row_index]["layer"]
        select_layer_in_glyphs(self.font, layer)
        self.set_status("Selected layer: %s" % layer_label(layer))
        self.start_editing_clicked_cell(sender, row_index)

    def table_clicked(self, table_view):
        if self.is_updating:
            return
        try:
            row = int(table_view.clickedRow())
        except Exception:
            row = -1
        if row < 0:
            try:
                row = int(table_view.selectedRow())
            except Exception:
                row = -1
        if row < 0 or row >= len(self.records):
            return

        select_layer_in_glyphs(self.font, self.records[row]["layer"])
        self.set_status("Selected layer: %s" % layer_label(self.records[row]["layer"]))
        self.start_editing_clicked_cell(self.w.table, row)

    def start_editing_clicked_cell(self, sender, fallback_row):
        table_view = vanilla_list_table_view(sender)
        if table_view is None:
            return
        try:
            row = int(table_view.clickedRow())
        except Exception:
            row = fallback_row
        if row < 0:
            row = fallback_row

        try:
            column = int(table_view.clickedColumn())
        except Exception:
            column = -1
        if column not in EDITABLE_COLUMNS:
            return

        try:
            table_view.editColumn_row_withEvent_select_(column, row, None, True)
        except Exception:
            pass

    def table_rows(self):
        try:
            return list(self.w.table.get())
        except Exception:
            try:
                return list(self.w.table)
            except Exception:
                return []

    def sync_locked_scale_rows(self, rows):
        changed = False
        for row in rows:
            x_text = str(row.get("xScale", "")).strip()
            if x_text and row.get("yScale", "") != x_text:
                row["yScale"] = x_text
                changed = True
        if changed:
            self.is_updating = True
            try:
                self.w.table.set(rows)
            finally:
                self.is_updating = False
        return rows

    def lock_scale_changed(self, sender):
        if not bool(sender.get()):
            return
        rows = self.sync_locked_scale_rows(self.table_rows())
        self.apply_rows(rows)

    def edit_callback(self, sender):
        if self.is_updating:
            return
        try:
            rows = list(sender.get())
        except Exception:
            rows = list(sender)
        if bool(self.w.lockScale.get()):
            rows = self.sync_locked_scale_rows(rows)
        self.apply_rows(rows)

    def apply_rows(self, rows):
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

                x_value = numeric_value(row.get("xScale", ""))
                y_value = numeric_value(row.get("yScale", ""))
                height_value = numeric_value(row.get("height", ""))

                row_changed = False
                if x_value is not None and y_value is not None:
                    if set_component_scale(component, x_value, y_value):
                        changed += 1
                        row_changed = True
                    else:
                        skipped += 1
                elif str(row.get("xScale", "")).strip() or str(row.get("yScale", "")).strip():
                    skipped += 1

                if height_value is not None:
                    if set_component_axis_value(component, self.height_axis, height_value):
                        changed += 1
                        row_changed = True
                    else:
                        skipped += 1
                elif str(row.get("height", "")).strip():
                    skipped += 1

                if row_changed:
                    row["status"] = "updated"
        finally:
            if hasattr(self.glyph, "endUndo"):
                self.glyph.endUndo()
            self.font.enableUpdateInterface()

        refresh_font(self.font)
        self.set_status("Updated %i value%s%s." % (
            changed,
            "" if changed == 1 else "s",
            "; skipped %i" % skipped if skipped else "",
        ))


SelectedComponentScaleHeightByLayer()
