#MenuTitle: copy sidebearings from masters to other layers
# -*- coding: utf-8 -*-

"""Copy associated-master sidebearings to selected non-master glyph layers.

Glyphs 4 / Vanilla. The window stays attached to the glyph selected when it
opens. Includes intermediate, alternate and backup layers, not backgrounds.
Sets LSB first, then RSB: this moves the layer content and adjusts its advance
width, without scaling the outlines. Master layers are never edited.
"""

import traceback

import vanilla
from AppKit import NSTableColumnUserResizingMask, NSTableViewNoColumnAutoresizing
from GlyphsApp import Glyphs


class CopySidebearingsWindow(object):
    def __init__(self):
        self.font = Glyphs.font
        if self.font is None or not self.font.selectedLayers:
            Glyphs.showMacroWindow()
            print("Open a font and select a glyph first.")
            return
        self.glyph = self.font.selectedLayers[0].parent
        self.w = vanilla.FloatingWindow(
            (1140, 440), "copy sidebearings from masters to other layers",
            minSize=(760, 300),
        )
        self.w.info = vanilla.TextBox(
            (15, 12, -15, 40),
            "Glyph: %s. Select rows with Command-click or Shift-click. "
            "Each selected layer receives its own associated master's sidebearings."
            % self.glyph.name,
        )
        self.w.layers = vanilla.List(
            (15, 58, -15, -82), [],
            columnDescriptions=[
                dict(title="Layer", key="layer", width=380, editable=False),
                dict(title="LSB", key="lsb", width=70, editable=False),
                dict(title="RSB", key="rsb", width=70, editable=False),
                dict(title="Associated master", key="master", width=380, editable=False),
                dict(title="Master LSB", key="masterLSB", width=95, editable=False),
                dict(title="Master RSB", key="masterRSB", width=95, editable=False),
            ],
            allowsMultipleSelection=True,
            allowsSorting=False,
            selectionCallback=self.selection_changed,
        )
        # Keep user-chosen widths and allow horizontal scrolling when the
        # columns are wider than the window.
        table = self.w.layers.getNSTableView()
        table.setColumnAutoresizingStyle_(NSTableViewNoColumnAutoresizing)
        for column in table.tableColumns():
            column.setMinWidth_(50)
            column.setMaxWidth_(2000)
            column.setResizingMask_(NSTableColumnUserResizingMask)
        table.enclosingScrollView().setHasHorizontalScroller_(True)
        self.w.refresh = vanilla.Button((15, -68, 90, 24), "Refresh", callback=self.refresh)
        self.w.copyButton = vanilla.Button(
            (-235, -68, 220, 24), "Copy to selected layers", callback=self.copy_selected,
        )
        self.w.status = vanilla.TextBox((15, -32, -15, 20), "")
        self.refresh()
        self.w.open()

    def master_for_layer(self, layer):
        master_id = layer.associatedMasterId
        master = self.font.masters[master_id] if master_id else None
        source = self.glyph.layers[master_id] if master is not None else None
        if source is None or not source.isMasterLayer:
            return None, None
        return master, source

    def refresh(self, sender=None):
        previous = getattr(self, "records", [])
        selected_ids = {
            previous[i].layerId for i in self.w.layers.getSelection()
            if i < len(previous)
        }
        self.records = [layer for layer in self.glyph.layers if not layer.isMasterLayer]
        rows = []
        for layer in self.records:
            master, source = self.master_for_layer(layer)
            rows.append(dict(
                layer=layer.name or layer.layerId,
                lsb="%g" % layer.LSB, rsb="%g" % layer.RSB,
                master=master.name if master is not None else "Missing associated master",
                masterLSB="%g" % source.LSB if source is not None else "—",
                masterRSB="%g" % source.RSB if source is not None else "—",
            ))
        self.w.layers.set(rows)
        self.w.layers.setSelection([
            i for i, layer in enumerate(self.records) if layer.layerId in selected_ids
        ])
        self.selection_changed()

    def selection_changed(self, sender=None):
        count = len(self.w.layers.getSelection())
        self.w.copyButton.enable(count > 0)
        self.w.status.set("%i non-master layers; %i selected." % (len(self.records), count))

    def copy_selected(self, sender):
        updates = []
        for i in self.w.layers.getSelection():
            layer = self.records[i]
            if self.glyph.layers[layer.layerId] is None or layer.isMasterLayer:
                self.w.status.set("Layer list changed. Refresh and select the layers again.")
                return
            master, source = self.master_for_layer(layer)
            if source is None:
                self.w.status.set("No associated master for %s. Nothing copied." % layer.name)
                return
            updates.append((layer, source.LSB, source.RSB))
        if not updates:
            return

        error = None
        self.font.disableUpdateInterface()
        try:
            self.glyph.beginUndo()
            try:
                for layer, lsb, rsb in updates:
                    layer.LSB = lsb
                    layer.RSB = rsb
            finally:
                self.glyph.endUndo()
        except Exception:
            error = traceback.format_exc()
        finally:
            self.font.enableUpdateInterface()
        self.refresh()
        if error:
            Glyphs.showMacroWindow()
            print(error)
            self.w.status.set("Copy failed; see Macro Window. Undo to revert partial changes.")
        else:
            mismatched = [layer.name for layer, lsb, rsb in updates
                          if abs(layer.LSB - lsb) > .01 or abs(layer.RSB - rsb) > .01]
            if mismatched:
                Glyphs.showMacroWindow()
                print("Sidebearings did not stay at their targets: %s" % ", ".join(mismatched))
                self.w.status.set("Some values differ from their targets; see Macro Window.")
            else:
                self.w.status.set("Copied sidebearings to %i layers. Undo is available." % len(updates))


copy_sidebearings_window = CopySidebearingsWindow()
