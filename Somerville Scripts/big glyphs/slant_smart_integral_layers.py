#MenuTitle: Apply Slanter 14 degrees to selected glyph's Slant layers
# -*- coding: utf-8 -*-

"""Apply Slanter's geometric angle to the selected glyph's named Slant layers.

Run once after creating the INSL intermediate layers. Running again applies
another slant to the current outlines. The font is not saved automatically.
"""

import objc
from GlyphsApp import Glyphs, Message


GEOMETRIC_ANGLE = 14.0


def main():
    font = Glyphs.font
    if font is None:
        Message("No Font Open", "Open a font before running this script.")
        return

    selected_layers = list(font.selectedLayers or [])
    if not selected_layers:
        Message("No Glyph Selected", "Select one glyph before running this script.")
        return
    glyph = selected_layers[0].parent
    if any(layer.parent.id != glyph.id for layer in selected_layers):
        Message("Multiple Glyphs Selected", "Select only one glyph before running this script.")
        return

    layers = [layer for layer in glyph.layers if "Slant" in (layer.name or "")]
    if not layers:
        Message("No Slant Layers", "No layers with Slant in their name were found.")
        return

    try:
        slanter = objc.lookUpClass("Slanter").alloc().init()
    except objc.nosuchclass_error:
        Message("Slanter Not Available", "This script requires the Slanter filter.")
        return
    if not hasattr(slanter, "slantLayer_geometric_"):
        Message("Slanter Not Supported", "The geometric slant method is unavailable.")
        return

    Glyphs.clearLog()
    Glyphs.showMacroWindow()
    completed = 0
    font.disableUpdateInterface()
    glyph.beginUndo()
    try:
        for layer in layers:
            # Process the entire layer even if some nodes are selected.
            selection = list(layer.selection)
            layer.clearSelection()
            try:
                slanter.slantLayer_geometric_(layer, GEOMETRIC_ANGLE)
            finally:
                layer.selection = selection
            completed += 1
            print("SLANT %s: geometric angle %g degrees" % (layer.name, GEOMETRIC_ANGLE))
    finally:
        glyph.endUndo()
        font.enableUpdateInterface()

    Message(
        "Slanter",
        "Applied a %g degree geometric slant to %i layers in %s."
        % (GEOMETRIC_ANGLE, completed, glyph.name),
    )


main()
