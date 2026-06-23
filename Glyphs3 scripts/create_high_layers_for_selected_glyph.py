#MenuTitle: Create High Layers for Selected Glyph
# -*- coding: utf-8 -*-

import uuid

from GlyphsApp import Glyphs


SCRIPT_VERSION = "2026-06-23 14:05 CDT create-high-layers"


def print_warning(message):
    print("WARNING: %s" % message)


def layer_index(glyph, target_layer):
    for index, layer in enumerate(glyph.layers):
        if layer is target_layer:
            return index
    return len(glyph.layers) - 1


def set_associated_master_id(layer, associated_master_id):
    method = getattr(layer, "setAssociatedMasterId_", None)
    if method is not None:
        try:
            method(associated_master_id)
            return
        except Exception:
            pass
    try:
        layer.associatedMasterId = associated_master_id
    except Exception:
        pass


def selected_glyph(font):
    selected_layers = list(font.selectedLayers or [])
    if not selected_layers:
        return None
    return selected_layers[0].parent


def create_high_layer(glyph, master):
    master_layer = glyph.layers[master.id]
    if master_layer is None:
        print_warning("%s: no layer for master %s" % (glyph.name, master.name))
        return None

    high_layer = master_layer.copy()
    high_layer.layerId = str(uuid.uuid4()).upper()
    set_associated_master_id(high_layer, master.id)
    high_layer.name = "%s High" % master.name
    glyph.layers.insert(layer_index(glyph, master_layer) + 1, high_layer)
    return high_layer


Glyphs.clearLog()
Glyphs.showMacroWindow()
print("Create High Layers for Selected Glyph")
print("Script version: %s" % SCRIPT_VERSION)
print("")

font = Glyphs.font
if font is None:
    print_warning("No font open.")
else:
    glyph = selected_glyph(font)
    if glyph is None:
        print_warning("No glyph selected.")
    else:
        print("Glyph: %s" % glyph.name)
        created_count = 0

        font.disableUpdateInterface()
        try:
            for master in font.masters:
                high_layer = create_high_layer(glyph, master)
                if high_layer is not None:
                    created_count += 1
                    print("Created layer: %s" % high_layer.name)
        finally:
            font.enableUpdateInterface()

        print("")
        print("Done. Created %i High layer(s)." % created_count)
