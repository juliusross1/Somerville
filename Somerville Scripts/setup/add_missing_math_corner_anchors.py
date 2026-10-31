#MenuTitle: Add Missing Math Corner Anchors to Current Glyph
# -*- coding: utf-8 -*-

"""Choose which missing math corner anchors to add on every glyph layer.

Resolves the first selected layer's glyph name in the document font, including
when the displayed layer is an interpolated preview. Includes master,
intermediate, alternate and backup layers in glyph.layers. Existing anchors
are never moved. Backgrounds are not separate entries in glyph.layers.

Left/right mean the sidebearing boundaries (x=0 and x=layer.width), not the
outline bounds or the numeric LSB/RSB distances. Bottom is the baseline (y=0);
top is the layer's associated master cap height, falling back to the selected
font master if a layer has no associated master.
"""

import traceback

import vanilla
from GlyphsApp import Glyphs, GSAnchor


def cap_height_for_layer(font, layer):
    master = getattr(layer, "master", None)
    if master is None:
        master_id = getattr(layer, "associatedMasterId", None)
        if master_id:
            master = font.masters[master_id]
    if master is None:
        master = font.selectedFontMaster
    if master is None:
        raise ValueError("Cannot determine a master for layer %s" % layer.name)
    return master.capHeight


def add_missing_anchors(selected_names, selection=None):
    if selection is not None:
        font, glyph = selection()
    else:
        font = Glyphs.font
        glyph = None
        if font is not None and font.selectedLayers:
            displayed_glyph = font.selectedLayers[0].parent
            if displayed_glyph is not None:
                glyph = font.glyphForName_(displayed_glyph.name)
    if font is None:
        Glyphs.showMacroWindow()
        print("Open a font first.")
        return
    if glyph is None:
        Glyphs.showMacroWindow()
        print("Select a glyph with an editable source first.")
        return

    # Resolve positions before making any edits.
    additions = []
    kept = 0
    layer_count = 0
    for layer in glyph.layers:
        layer_count += 1
        cap_height = cap_height_for_layer(font, layer)
        positions = (
            ("math.bl", (0, 0)),
            ("math.tl", (0, cap_height)),
            ("math.tr", (layer.width, cap_height)),
            ("math.br", (layer.width, 0)),
        )
        for name, position in positions:
            if name not in selected_names:
                continue
            if layer.anchors[name] is not None:
                kept += 1
            else:
                additions.append((layer, name, position))

    if additions:
        font.disableUpdateInterface()
        try:
            glyph.beginUndo()
            try:
                for layer, name, position in additions:
                    anchor = GSAnchor()
                    anchor.name = name
                    anchor.position = position
                    layer.anchors.append(anchor)
            finally:
                glyph.endUndo()
        finally:
            font.enableUpdateInterface()

    print("%s: added %i math corner anchors across %i layers; kept %i existing."
          % (glyph.name, len(additions), layer_count, kept))
    return "%s: added %i; kept %i existing." % (glyph.name, len(additions), kept)


class MathCornerAnchorDialog:
    def __init__(self, on_added=None, selection=None):
        self.on_added = on_added
        self.selection = selection
        self.w = vanilla.FloatingWindow((390, 245), "Add Missing Math Corner Anchors")
        self.w.info = vanilla.TextBox(
            (15, 15, -15, 40),
            "Add checked corners on every layer of the current glyph. Existing anchors stay in place.",
        )
        self.checkboxes = {}
        for name, label, x, y in (
            ("math.tl", "Top left (math.tl)", 15, 65),
            ("math.tr", "Top right (math.tr)", 205, 65),
            ("math.bl", "Bottom left (math.bl)", 15, 100),
            ("math.br", "Bottom right (math.br)", 205, 100),
        ):
            checkbox = vanilla.CheckBox(
                (x, y, 175, 22), label, value=True, callback=self.selection_changed
            )
            setattr(self.w, name.replace(".", "_"), checkbox)
            self.checkboxes[name] = checkbox
        self.w.cancel = vanilla.Button(
            (15, 145, 100, 28), "Close", callback=self.close
        )
        self.w.add = vanilla.Button(
            (135, 145, -15, 28), "Add Missing Anchors", callback=self.add
        )
        self.w.status = vanilla.TextBox((15, 190, -15, 40), "")
        self.w.setDefaultButton(self.w.add)
        self.w.open()

    def selected_names(self):
        return {name for name, checkbox in self.checkboxes.items() if checkbox.get()}

    def selection_changed(self, sender):
        self.w.add.enable(bool(self.selected_names()))

    def close(self, sender):
        self.w.close()

    def add(self, sender):
        names = self.selected_names()
        if not names:
            return
        try:
            result = add_missing_anchors(names, selection=self.selection)
            self.w.status.set(result or "Select a glyph in an open font first.")
            if result is not None and self.on_added is not None:
                self.on_added(result)
        except Exception:
            Glyphs.showMacroWindow()
            traceback.print_exc()
            self.w.status.set("Could not add anchors. See the Macro window.")


if __name__ == "__main__":
    math_corner_anchor_dialog = MathCornerAnchorDialog()
