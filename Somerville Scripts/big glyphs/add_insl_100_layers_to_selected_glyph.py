#MenuTitle: Add INSL=100 Layers to Selected Glyphs
# -*- coding: utf-8 -*-

"""Add Slant, and where applicable High Slant, layers to selected glyphs.

Integral components in target layers get their smart slant axis set to 100. Existing target
layers are reused, preserving their outlines and other component settings.
Smart height layers require Glyphs 4 source format. Save after running.
"""

import uuid
from copy import deepcopy

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


def selected_glyphs(font):
    glyphs = []
    seen = set()
    for layer in font.selectedLayers or []:
        glyph = layer.parent
        if glyph is not None and glyph.name not in seen:
            seen.add(glyph.name)
            glyphs.append(glyph)
    return glyphs


def set_component_slant(layer):
    updated = 0
    for component in layer.components:
        if "integral" not in (component.componentName or "").lower():
            continue
        # The component glyph's smart slant axis is distinct from font INSL.
        # Glyphs 4 exposes these axes on component.component.axes.
        smart_glyph = component.component
        slant_axes = [axis for axis in (smart_glyph.axes if smart_glyph else [])
                      if axis_name(axis).strip().lower().replace(" ", "")
                      in ("slant", "integralslant")]
        if len(slant_axes) != 1:
            raise RuntimeError("%s: expected one smart slant axis, found %i"
                               % (component.componentName, len(slant_axes)))
        slant_id = axis_identifier(slant_axes[0])
        if not slant_id:
            raise RuntimeError("%s: smart slant axis has no ID"
                               % component.componentName)
        current = component.smartComponentValues
        keys = current.keys() if current is not None else None
        values = {key: current[key] for key in (keys or [])}
        if values.get(slant_id) == TARGET_VALUE:
            continue
        component.smartComponentValues[slant_id] = TARGET_VALUE
        if component.smartComponentValues[slant_id] != TARGET_VALUE:
            raise RuntimeError("%s: smart slant value did not stick"
                               % component.componentName)
        updated += 1
    return updated


def layer_name(layer):
    # Glyphs 4's Python .name exposes nameUI, which can hide the stored name.
    return str(layer.pyobjc_instanceMethods.name() or "")


def set_coordinates(layer, coordinates):
    attributes = deepcopy(dict(layer.attributes or {}))
    attributes.pop("partSelection", None)
    attributes["coordinates"] = dict(coordinates)
    layer.attributes = attributes
    actual = layer_attribute(layer, "coordinates")
    if actual is None or any(
        key not in actual or abs(float(actual[key]) - value) > TOLERANCE
        for key, value in coordinates.items()
    ):
        raise RuntimeError("Coordinates did not stick on %s" % layer.name)


def find_high(glyph, font, master, height_id, insl_id):
    candidates = []
    base = master_coordinates(font, master)
    for layer in glyph.layers:
        if str(layer.layerId) == str(master.id):
            continue
        if associated_master_id(layer) != str(master.id):
            continue
        if "slant" in layer_name(layer).lower():
            continue
        coordinates = effective_coordinates(font, layer, master)
        if abs(coordinates.get(insl_id, 0) - base[insl_id]) > TOLERANCE:
            continue
        if (abs(coordinates.get(height_id, -1) - 100) <= TOLERANCE
                or layer_name(layer) == "%s High" % master.name):
            candidates.append(layer)
    if len(candidates) > 1:
        raise RuntimeError("%s / %s: multiple High source layers" % (glyph.name, master.name))
    return candidates[0] if candidates else None


def find_target(glyph, font, master, coordinates, height):
    name = "%s %s" % (master.name, "High Slant" if height == 100 else "Slant")
    aliases = {name}
    if height in (None, 0):
        aliases.add("%s INSL=100" % master.name)
    if height is not None:
        aliases.add("%s height=%g INSL=100" % (master.name, height))
    candidates = []
    for layer in glyph.layers:
        if str(layer.layerId) == str(master.id):
            continue
        if associated_master_id(layer) != str(master.id):
            continue
        if (layer_name(layer) in aliases
                or coordinates_match(effective_coordinates(font, layer, master), coordinates)):
            candidates.append(layer)
    if len(candidates) > 1:
        raise RuntimeError("%s / %s: multiple target layers; resolve duplicates first" % (glyph.name, name))
    return (candidates[0] if candidates else None), name


def main():
    font = Glyphs.font
    if font is None:
        Message("No Font Open", "Open a font before running this script.")
        return
    glyphs = selected_glyphs(font)
    if not glyphs:
        Message("No Glyph Selected", "Select one or more glyphs before running this script.")
        return
    insl_axis = find_axis(font)
    insl_id = axis_identifier(insl_axis) if insl_axis is not None else None
    if not insl_id:
        Message("INSL Axis Not Found", "The font needs an axis tagged INSL with a valid ID.")
        return

    Glyphs.clearLog()
    Glyphs.showMacroWindow()
    created = kept = components_updated = skipped = 0
    font.disableUpdateInterface()
    try:
        for glyph in glyphs:
            print("GLYPH %s" % glyph.name)
            height_axis = next((axis for axis in glyph.axes
                                if axis_name(axis).lower() == "height"), None)
            height_id = axis_identifier(height_axis) if height_axis is not None else None
            if height_axis is not None and not height_id:
                print("SKIPPED %s: height axis has no ID" % glyph.name)
                skipped += 1
                continue
            if height_id:
                # Format 3 loses global INSL coordinates on smart height layers.
                font.formatVersion = 4
            undo_started = False
            try:
                try:
                    glyph.beginUndo()
                    undo_started = True
                except Exception:
                    pass
                for master in font.masters:
                    source = glyph.layers[master.id]
                    if source is None:
                        print("SKIPPED %s / %s: no master layer" % (glyph.name, master.name))
                        skipped += 1
                        continue
                    high = find_high(glyph, font, master, height_id, insl_id) if height_id else None
                    if height_id and high is None:
                        print("SKIPPED %s / %s: no height=100 source layer" % (glyph.name, master.name))
                        skipped += 1
                        continue
                    if high is not None:
                        high_coordinates = master_coordinates(font, master)
                        high_coordinates[height_id] = 100.0
                        set_coordinates(high, high_coordinates)
                        high.name = "%s High" % master.name
                    for height in ((0.0, 100.0) if height_id else (None,)):
                        coordinates = master_coordinates(font, master)
                        coordinates[insl_id] = TARGET_VALUE
                        if height_id:
                            coordinates[height_id] = height
                        target, name = find_target(glyph, font, master, coordinates, height)
                        if target is None:
                            target = (high if height == 100 else source).copy()
                            target.layerId = str(uuid.uuid4()).upper()
                            target.associatedMasterId = master.id
                            glyph.layers.append(target)
                            created += 1
                        else:
                            kept += 1
                        set_coordinates(target, coordinates)
                        target.name = name
                        components_updated += set_component_slant(target)
                        print("SET %s / %s" % (glyph.name, name))
            finally:
                if undo_started:
                    glyph.endUndo()
    finally:
        font.enableUpdateInterface()
    Message(
        "INSL=100 Layers",
        "Created %i layer(s); reused %i; updated %i integral component(s); skipped %i. "
        "Save the font after running."
        % (created, kept, components_updated, skipped),
    )


main()
