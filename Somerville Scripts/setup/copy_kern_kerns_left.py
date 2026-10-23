#MenuTitle: copy kern kerns left
# -*- coding: utf-8 -*-

"""Copy the right math corner-anchor slope to the left, on all glyph layers.

For Glyphs 3. Uses the first selected layer's parent as the current glyph.
Preserves right-anchor x coordinates, sets bottom y=65 and top y to the
associated master's x-height. Left sidebearing boundary means x=0, not
the outline's leftmost point or layer.LSB.

Since both anchor pairs have the same vertical span, equal signed horizontal
spans give equal angles: math.tl.x = math.tr.x - math.br.x; math.bl.x = 0.
Creates missing left anchors. Layers missing either right anchor are skipped
and reported, since they have no slope to copy. Includes master, intermediate,
alternate and backup layers, but not backgrounds.
"""

from GlyphsApp import Glyphs, GSAnchor


def x_height_for_layer(font, layer):
    master = getattr(layer, "master", None)
    if master is None:
        master_id = getattr(layer, "associatedMasterId", None)
        if master_id:
            master = font.masters[master_id]
    if master is None:
        master = font.selectedFontMaster
    if master is None:
        raise ValueError("Cannot determine a master for layer %s" % layer.name)
    return master.xHeight


def main():
    font = Glyphs.font
    if font is None or not font.selectedLayers:
        Glyphs.showMacroWindow()
        print("Open a font and select a glyph first.")
        return
    glyph = font.selectedLayers[0].parent
    if glyph is None:
        Glyphs.showMacroWindow()
        print("The selected layer has no parent glyph.")
        return

    updates = []
    skipped = []
    # Resolve coordinates before changing any layers.
    for layer in glyph.layers:
        bottom_right = layer.anchors["math.br"]
        top_right = layer.anchors["math.tr"]
        if bottom_right is None or top_right is None:
            skipped.append(layer.name)
            continue
        top_y = x_height_for_layer(font, layer)
        bottom_x = bottom_right.position.x
        top_x = top_right.position.x
        updates.append((layer, (
            ("math.br", (bottom_x, 65)),
            ("math.tr", (top_x, top_y)),
            ("math.bl", (0, 65)),
            ("math.tl", (top_x - bottom_x, top_y)),
        )))

    if updates:
        font.disableUpdateInterface()
        try:
            glyph.beginUndo()
            try:
                for layer, positions in updates:
                    for name, position in positions:
                        anchor = layer.anchors[name]
                        if anchor is None:
                            anchor = GSAnchor()
                            anchor.name = name
                            anchor.position = position
                            layer.anchors.append(anchor)
                        else:
                            anchor.position = position
            finally:
                glyph.endUndo()
        finally:
            font.enableUpdateInterface()

    print("%s: copied right corner slope to left on %i layers."
          % (glyph.name, len(updates)))
    if skipped:
        Glyphs.showMacroWindow()
        print("Skipped layers missing math.br or math.tr: %s" % ", ".join(skipped))


if __name__ == "__main__":
    main()
