#MenuTitle: Add Missing Math Corner Anchors to Current Glyph
# -*- coding: utf-8 -*-

"""Add missing math.bl, math.tl, math.tr and math.br on every glyph layer.

Uses the first selected layer's parent as the current glyph. Includes master,
intermediate, alternate and backup layers in glyph.layers. Existing anchors
are never moved. Backgrounds are not separate entries in glyph.layers.

Left/right mean the sidebearing boundaries (x=0 and x=layer.width), not the
outline bounds or the numeric LSB/RSB distances. Bottom is the baseline (y=0);
top is the layer's associated master cap height, falling back to the selected
font master if a layer has no associated master.
"""

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


def main():
    font = Glyphs.font
    if font is None:
        Glyphs.showMacroWindow()
        print("Open a font first.")
        return
    if not font.selectedLayers:
        Glyphs.showMacroWindow()
        print("Select a glyph first.")
        return

    glyph = font.selectedLayers[0].parent
    if glyph is None:
        Glyphs.showMacroWindow()
        print("The selected layer has no parent glyph.")
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


if __name__ == "__main__":
    main()
