#MenuTitle: Add INSL=100 Layers to Selected Glyph
# -*- coding: utf-8 -*-

"""Add one INSL=100 intermediate per master to the selected glyph.

Each new layer is copied directly from its master layer. Smart-component
height layers and height pole mappings are intentionally ignored.
"""

import uuid

from GlyphsApp import Glyphs, Message


AXIS_TAG = "INSL"
AXIS_NAME = "Integral Slant"
TARGET_VALUE = 100.0
TOLERANCE = 0.0001


def value_or_call(value):
    return value() if callable(value) else value


def axis_identifier(axis):
    for attribute_name in ("id", "axisId"):
        try:
            value = value_or_call(getattr(axis, attribute_name))
            if value:
                return str(value)
        except Exception:
            pass
    return None


def axis_tag(axis):
    for attribute_name in ("axisTag", "tag"):
        try:
            value = value_or_call(getattr(axis, attribute_name))
            if value:
                return str(value)
        except Exception:
            pass
    return ""


def axis_name(axis):
    try:
        return str(value_or_call(axis.name) or "")
    except Exception:
        return ""


def find_axis(font):
    for axis in font.axes:
        if axis_tag(axis).strip().upper() == AXIS_TAG:
            return axis
    wanted_name = AXIS_NAME.lower().replace(" ", "")
    for axis in font.axes:
        if axis_name(axis).strip().lower().replace(" ", "") == wanted_name:
            return axis
    return None


def layer_attribute(layer, key):
    try:
        value = layer.attributes[key]
        if value is not None:
            return value
    except Exception:
        pass
    try:
        return layer.attributeForKey_(key)
    except Exception:
        return None


def set_layer_attribute(layer, key, value):
    try:
        layer.attributes[key] = value
        return
    except Exception:
        pass
    try:
        layer.setAttribute_forKey_(value, key)
        return
    except Exception:
        pass
    raise RuntimeError("Could not set layer attribute %s." % key)


def associated_master_id(layer):
    try:
        value = value_or_call(layer.associatedMasterId)
        return str(value) if value else None
    except Exception:
        return None


def master_coordinates(font, master):
    coordinates = {}
    for index, axis in enumerate(font.axes):
        axis_id = axis_identifier(axis)
        if axis_id is None:
            raise RuntimeError("Axis %i has no identifier." % (index + 1))
        try:
            value = master.axisValueValueForId_(axis_id)
        except Exception:
            value = master.axesValues[index]
        coordinates[axis_id] = float(value)
    return coordinates


def effective_coordinates(font, layer, master):
    coordinates = master_coordinates(font, master)
    raw = layer_attribute(layer, "coordinates")
    if raw is None:
        return coordinates
    if hasattr(raw, "keys"):
        coordinates.update({str(key): float(raw[key]) for key in raw.keys()})
        return coordinates
    values = list(raw)
    if len(values) == len(font.axes):
        coordinates.update({
            axis_identifier(axis): float(values[index])
            for index, axis in enumerate(font.axes)
        })
    return coordinates


def coordinates_match(first, second):
    if set(first) != set(second):
        return False
    return all(abs(first[key] - second[key]) <= TOLERANCE for key in first)


def existing_target(glyph, font, master, coordinates):
    for layer in glyph.layers:
        if str(getattr(layer, "layerId", "")) == str(master.id):
            continue
        if associated_master_id(layer) != str(master.id):
            continue
        if coordinates_match(effective_coordinates(font, layer, master), coordinates):
            return layer
    return None


def selected_glyph(font):
    selected_layers = list(font.selectedLayers or [])
    if not selected_layers:
        return None
    return selected_layers[0].parent


def main():
    Glyphs.clearLog()
    Glyphs.showMacroWindow()

    font = Glyphs.font
    if font is None:
        Message("No Font Open", "Open a font before running this script.")
        return

    glyph = selected_glyph(font)
    if glyph is None:
        Message("No Glyph Selected", "Select a glyph before running this script.")
        return

    insl_axis = find_axis(font)
    if insl_axis is None:
        Message("INSL Axis Not Found", "The font needs an axis tagged INSL.")
        return
    insl_axis_id = axis_identifier(insl_axis)
    if insl_axis_id is None:
        Message("Invalid INSL Axis", "The INSL axis has no identifier.")
        return

    created = 0
    kept = 0
    undo_started = False
    font.disableUpdateInterface()
    try:
        try:
            glyph.beginUndo()
            undo_started = True
        except Exception:
            pass

        for master in font.masters:
            source = glyph.layers[master.id]
            if source is None:
                print("SKIPPED %s: no master layer" % master.name)
                continue

            coordinates = master_coordinates(font, master)
            coordinates[insl_axis_id] = TARGET_VALUE
            current = existing_target(glyph, font, master, coordinates)
            if current is not None:
                kept += 1
                print("KEPT %s: %s" % (master.name, current.name or current.layerId))
                continue

            new_layer = source.copy()
            new_layer.layerId = str(uuid.uuid4()).upper()
            new_layer.associatedMasterId = master.id
            new_layer.name = "%s INSL=100" % master.name
            set_layer_attribute(new_layer, "coordinates", coordinates)
            glyph.layers.append(new_layer)
            created += 1
            print("CREATED %s" % new_layer.name)
    finally:
        if undo_started:
            try:
                glyph.endUndo()
            except Exception:
                pass
        font.enableUpdateInterface()

    Message(
        "INSL=100 Layers",
        "Created %i layer(s) in %s; %i matching layer(s) already existed."
        % (created, glyph.name, kept),
    )


main()
