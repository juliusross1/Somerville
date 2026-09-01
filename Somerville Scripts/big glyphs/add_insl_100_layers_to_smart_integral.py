#MenuTitle: Add INSL=100 Layers to _smart.integral
# -*- coding: utf-8 -*-

"""Add height=0/100, INSL=100 layers to _smart.integral."""

import uuid

from GlyphsApp import Glyphs, Message


GLYPH_NAME = "_smart.integral"
HEIGHT_VALUES = (0.0, 100.0)
INSL_VALUE = 100.0
TOLERANCE = 0.0001


def axis_id(axis):
    for key in ("id", "axisId"):
        try:
            value = getattr(axis, key)
            value = value() if callable(value) else value
            if value:
                return str(value)
        except Exception:
            pass
    return None


def get_coordinates(layer):
    try:
        value = layer.attributes["coordinates"]
    except Exception:
        value = None
    if value is None:
        try:
            value = layer.attributeForKey_("coordinates")
        except Exception:
            value = None
    if value is None or not hasattr(value, "keys"):
        return {}
    return {str(key): float(value[key]) for key in value.keys()}


def set_coordinates(layer, coordinates):
    try:
        layer.attributes["coordinates"] = coordinates
        return
    except Exception:
        pass
    layer.setAttribute_forKey_(coordinates, "coordinates")


def layer_id(layer):
    try:
        return str(layer.layerId)
    except Exception:
        return ""


def associated_master_id(layer):
    try:
        return str(layer.associatedMasterId)
    except Exception:
        return ""


def source_for_height(glyph, master, height_axis_id, height):
    if height == 0.0:
        return glyph.layers[master.id]
    for layer in glyph.layers:
        if layer_id(layer) == str(master.id):
            continue
        if associated_master_id(layer) != str(master.id):
            continue
        coordinates = get_coordinates(layer)
        try:
            if abs(float(coordinates[height_axis_id]) - height) <= TOLERANCE:
                return layer
        except Exception:
            continue
    return None


def matching_layer(glyph, master, height_axis_id, insl_axis_id, height):
    for layer in glyph.layers:
        if layer_id(layer) == str(master.id):
            continue
        if associated_master_id(layer) != str(master.id):
            continue
        coordinates = get_coordinates(layer)
        try:
            layer_height = float(coordinates[height_axis_id])
            layer_insl = float(coordinates[insl_axis_id])
        except Exception:
            continue
        if (
            abs(layer_height - height) <= TOLERANCE
            and abs(layer_insl - INSL_VALUE) <= TOLERANCE
        ):
            return layer
    return None


def main():
    font = Glyphs.font
    if font is None:
        Message("No Font Open", "Open Somerville before running this script.")
        return

    glyph = font.glyphs[GLYPH_NAME]
    if glyph is None:
        Message("Glyph Not Found", "%s is not in the open font." % GLYPH_NAME)
        return

    try:
        insl_axis = list(font.axes)[-1]
    except Exception:
        Message("INSL Axis Not Found", "The font has no axes.")
        return
    try:
        height_axis = list(glyph.axes)[0]
    except Exception:
        Message(
            "Height Axis Not Found",
            "%s has no glyph-local smart axis." % GLYPH_NAME,
        )
        return

    insl_axis_id = axis_id(insl_axis)
    height_axis_id = axis_id(height_axis)
    if not insl_axis_id or not height_axis_id:
        Message("Invalid Axis", "The INSL or height axis has no ID.")
        return

    created = 0
    skipped = 0
    Glyphs.clearLog()
    Glyphs.showMacroWindow()
    print("Add INSL=100 layers to %s" % GLYPH_NAME)

    font.disableUpdateInterface()
    try:
        for master in font.masters:
            for height in HEIGHT_VALUES:
                if matching_layer(
                    glyph, master, height_axis_id, insl_axis_id, height
                ):
                    skipped += 1
                    print("SKIP %s: height=%g, INSL=100" % (master.name, height))
                    continue

                source = source_for_height(
                    glyph, master, height_axis_id, height
                )
                if source is None:
                    print("ERROR %s: no height=%g source layer" % (master.name, height))
                    continue

                new_layer = source.copy()
                new_layer.layerId = str(uuid.uuid4()).upper()
                new_layer.associatedMasterId = master.id
                new_layer.name = "%s height=%g INSL=100" % (master.name, height)
                set_coordinates(
                    new_layer,
                    {
                        height_axis_id: height,
                        insl_axis_id: INSL_VALUE,
                    },
                )
                glyph.layers.append(new_layer)
                created += 1
                print("ADD  %s: height=%g, INSL=100" % (master.name, height))
    finally:
        font.enableUpdateInterface()

    Message(
        "INSL Layers",
        "Created %i layer(s); skipped %i existing layer(s)."
        % (created, skipped),
    )


main()
