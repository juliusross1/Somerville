#MenuTitle: Set default corner kern postions for italic capitals
# -*- coding: utf-8 -*-

"""Set math corner anchors on every layer of the current glyph.

Bottom anchors use y=65; top anchors use the associated master's x-height.
Both pairs lean 15.6 degrees clockwise from upward vertical. Preserve the
x positions of math.bl and math.tr and calculate math.tl and math.br from
them. Missing math.bl/math.tr default to x=0/layer.width respectively.

Includes master, intermediate, alternate and backup layers in glyph.layers,
but not backgrounds. Uses the first selected layer's parent glyph. Does not
change outlines or other anchors. All changes form one glyph undo operation.
"""

import math

from GlyphsApp import Glyphs, GSAnchor


BOTTOM_Y = 65
ANGLE_DEGREES = 15.6


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

    # Resolve every layer before editing so missing metrics cannot leave a
    # partially updated glyph.
    updates = []
    for layer in glyph.layers:
        top_y = x_height_for_layer(font, layer)
        dx = (top_y - BOTTOM_Y) * math.tan(math.radians(ANGLE_DEGREES))
        bottom_left = layer.anchors["math.bl"]
        top_right = layer.anchors["math.tr"]
        left_x = bottom_left.position.x if bottom_left is not None else 0
        right_x = top_right.position.x if top_right is not None else layer.width
        updates.append((layer, (
            ("math.bl", (left_x, BOTTOM_Y)),
            ("math.tl", (left_x + dx, top_y)),
            ("math.tr", (right_x, top_y)),
            ("math.br", (right_x - dx, BOTTOM_Y)),
        )))

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

    print("%s: set corner kern anchors on %i layers at %.1f degrees; bottom y=%g."
          % (glyph.name, len(updates), ANGLE_DEGREES, BOTTOM_Y))


if __name__ == "__main__":
    main()
