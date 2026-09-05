#MenuTitle: Add INSL intermediate layers to _smart.integral
# -*- coding: utf-8 -*-

"""Add or repair Slant and High Slant layers alongside each master's High layer.

Uses Glyphs 4 source format: format 3 drops global INSL coordinates when saving
layers that also use a glyph-local height axis. Save the font after running.
"""

import uuid
from copy import deepcopy

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
    # Copies may retain legacy smart pole mappings. Use an independent attribute
    # dictionary, with explicit coordinates as the only position definition.
    attributes = deepcopy(dict(layer.attributes))
    attributes.pop("partSelection", None)
    attributes["coordinates"] = dict(coordinates)
    layer.attributes = attributes
    actual = get_coordinates(layer)
    if any(abs(actual.get(key, float("inf")) - value) > TOLERANCE
           for key, value in coordinates.items()):
        raise RuntimeError("Coordinates did not stick on %s" % layer.name)


def target_coordinates(font, master, height_axis_id, height, insl_axis_id, insl):
    coordinates = {
        axis_id(axis): float(master.axisValueValueForId_(axis_id(axis)))
        for axis in font.axes
    }
    coordinates[height_axis_id] = height
    coordinates[insl_axis_id] = insl
    return coordinates


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
        if "Slant" in (layer.name or ""):
            continue
        if layer.name == "%s High" % master.name:
            return layer
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

    insl_axis = next((axis for axis in font.axes if axis.axisTag == "INSL"), None)
    height_axis = next((axis for axis in glyph.axes
                        if axis.name.lower() == "height"), None)
    if insl_axis is None or height_axis is None:
        Message("Axis Not Found", "The font needs INSL and the glyph needs a local height axis.")
        return

    insl_axis_id = axis_id(insl_axis)
    height_axis_id = axis_id(height_axis)
    if not insl_axis_id or not height_axis_id:
        Message("Invalid Axis", "The INSL or height axis has no ID.")
        return

    # In format 3, the writer converts these layers to legacy smart poles and
    # discards their global coordinates. In-memory verification cannot catch
    # that loss; format 4 is needed to preserve both INSL and local height.
    font.formatVersion = 4

    created = 0
    skipped = 0
    renamed = 0
    Glyphs.clearLog()
    Glyphs.showMacroWindow()
    print("Add INSL=100 layers to %s" % GLYPH_NAME)

    font.disableUpdateInterface()
    try:
        for master in font.masters:
            high = source_for_height(glyph, master, height_axis_id, 100.0)
            if high is None:
                print("ERROR %s: no High source layer" % master.name)
                continue
            high.name = "%s High" % master.name
            set_coordinates(high, target_coordinates(
                font, master, height_axis_id, 100.0, insl_axis_id,
                float(master.axisValueValueForId_(insl_axis_id)),
            ))
            for height in HEIGHT_VALUES:
                name = "%s %s" % (
                    master.name, "Slant" if height == 0.0 else "High Slant"
                )
                coordinates = target_coordinates(
                    font, master, height_axis_id, height, insl_axis_id, INSL_VALUE
                )
                # Recognize layers from earlier versions even when their stored
                # coordinates are broken, preserving any already slanted outlines.
                named = [layer for layer in glyph.layers
                         if associated_master_id(layer) == str(master.id)
                         and layer.name in (name, "%s height=%g INSL=100" % (master.name, height))]
                if len(named) > 1:
                    raise RuntimeError("Multiple layers named %s; resolve duplicates first." % name)
                existing = named[0] if named else matching_layer(
                    glyph, master, height_axis_id, insl_axis_id, height
                )
                if existing is not None:
                    set_coordinates(existing, coordinates)
                    if existing.name != name:
                        existing.name = name
                        renamed += 1
                        print("RENAME %s" % name)
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
                new_layer.name = name
                # Attach first so Glyphs can resolve global and glyph-local axes.
                glyph.layers.append(new_layer)
                set_coordinates(new_layer, coordinates)
                created += 1
                print("ADD  %s: height=%g, INSL=100" % (master.name, height))
    finally:
        font.enableUpdateInterface()

    Message(
        "INSL Layers",
        "Created %i layer(s); updated %i existing layer(s), renamed %i. "
        "Save the font in Glyphs 4 format to preserve INSL coordinates."
        % (created, skipped, renamed),
    )


main()
