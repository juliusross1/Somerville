#MenuTitle: Fill Missing Intermediate Coordinates
# -*- coding: utf-8 -*-

"""Fill missing designspace coordinates on the current glyph's intermediates.

The script acts only on the currently selected or edited glyph. It inspects
every intermediate layer, preserves all explicit coordinate values, and fills
each absent axis coordinate from the layer's associated master. Complete
coordinate dictionaries are then stored on layers that needed repair.

Master layers and bracket/axis-rule layers are not changed. The operation is
all-or-nothing: every intermediate layer and associated master is validated
before any edit occurs. Unreadable coordinates, unknown axis identifiers, or
a missing associated master raise an error and leave the glyph unchanged.
Actions and errors are printed in the Macro window, and changes are grouped
for undo.
"""

from GlyphsApp import Glyphs, Message


def value_or_call(value):
    return value() if callable(value) else value


def boolean_attribute(obj, attribute_name):
    try:
        return bool(value_or_call(getattr(obj, attribute_name)))
    except Exception:
        return False


def axis_identifier(axis):
    for attribute_name in ("id", "axisId"):
        try:
            value = value_or_call(getattr(axis, attribute_name))
            if value:
                return str(value)
        except Exception:
            pass
    return None


def axis_label(axis):
    for attribute_name in ("axisTag", "tag", "name"):
        try:
            value = value_or_call(getattr(axis, attribute_name))
            if value:
                return str(value)
        except Exception:
            pass
    return axis_identifier(axis) or "unknown axis"


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
        if value:
            return str(value)
    except Exception:
        pass
    return None


def layer_label(layer):
    try:
        return str(layer.name or layer.layerId)
    except Exception:
        return "unnamed layer"


def is_intermediate_layer(layer):
    """Identify coordinate/brace intermediates, excluding bracket layers."""
    if boolean_attribute(layer, "isMasterLayer"):
        return False
    if boolean_attribute(layer, "isBracketLayer"):
        return False
    if boolean_attribute(layer, "isIntermediateLayer"):
        return True
    if layer_attribute(layer, "axisRules") is not None:
        return False
    if layer_attribute(layer, "coordinates") is not None:
        return True
    return boolean_attribute(layer, "isBraceLayer")


def master_coordinates(font, master):
    result = {}
    for index, axis in enumerate(font.axes):
        axis_id = axis_identifier(axis)
        if axis_id is None:
            raise RuntimeError("Axis %i has no identifier." % (index + 1))
        try:
            value = master.axisValueValueForId_(axis_id)
        except Exception:
            try:
                value = master.axesValues[index]
            except Exception as error:
                raise RuntimeError(
                    "Could not read %s from master %s: %s"
                    % (axis_label(axis), master.name, error)
                )
        result[axis_id] = float(value)
    return result


def coordinates_dict(font, raw_coordinates):
    if raw_coordinates is None:
        return {}
    if hasattr(raw_coordinates, "keys"):
        result = {}
        for key in raw_coordinates.keys():
            try:
                result[str(key)] = float(raw_coordinates[key])
            except Exception as error:
                raise RuntimeError(
                    "Coordinate %s is not numeric: %s" % (key, error)
                )
        return result
    try:
        values = list(raw_coordinates)
    except Exception as error:
        raise RuntimeError("Coordinates are not a dictionary or sequence: %s" % error)
    if len(values) != len(font.axes):
        raise RuntimeError(
            "Coordinate sequence has %i values for %i axes; missing positional "
            "coordinates cannot be identified safely."
            % (len(values), len(font.axes))
        )
    return {
        axis_identifier(axis): float(values[index])
        for index, axis in enumerate(font.axes)
    }


def selected_glyph(font):
    try:
        layers = list(font.selectedLayers or [])
        return layers[0].parent if layers else None
    except Exception:
        return None


def coordinate_summary(font, coordinates):
    parts = []
    for axis in font.axes:
        axis_id = axis_identifier(axis)
        value = float(coordinates[axis_id])
        value_text = str(int(value)) if value.is_integer() else "%g" % value
        parts.append("%s=%s" % (axis_label(axis), value_text))
    return ", ".join(parts)


def main():
    font = Glyphs.font
    Glyphs.clearLog()
    Glyphs.showMacroWindow()
    print("=" * 78)
    print("Fill Missing Intermediate Coordinates")
    print("=" * 78)
    if font is None:
        print("ERROR: No font is open.")
        Message("No Font Open", "Open a font before running this script.")
        return
    glyph = selected_glyph(font)
    if glyph is None:
        print("ERROR: No current glyph is selected or edited.")
        Message(
            "No Glyph Selected",
            "Select a glyph in Font View or open a glyph in Edit View.",
        )
        return
    print("Glyph: %s" % glyph.name)

    masters_by_id = {str(master.id): master for master in font.masters}
    axis_ids = set()
    for axis in font.axes:
        axis_id = axis_identifier(axis)
        if axis_id is None:
            error = "A font axis has no identifier."
            print("ERROR: %s" % error)
            Message("No Changes Made", error)
            return
        axis_ids.add(axis_id)

    intermediates = [layer for layer in glyph.layers if is_intermediate_layer(layer)]
    print("Intermediate layers found: %i" % len(intermediates))
    repairs = []
    try:
        for layer in intermediates:
            label = layer_label(layer)
            master_id = associated_master_id(layer)
            if not master_id:
                raise RuntimeError("%s has no associated master ID." % label)
            master = masters_by_id.get(master_id)
            if master is None:
                raise RuntimeError(
                    "%s refers to missing associated master %s." % (label, master_id)
                )
            existing = coordinates_dict(font, layer_attribute(layer, "coordinates"))
            unknown_ids = sorted(set(existing) - axis_ids)
            if unknown_ids:
                raise RuntimeError(
                    "%s contains unknown axis coordinate(s): %s."
                    % (label, ", ".join(unknown_ids))
                )
            inherited = master_coordinates(font, master)
            missing_ids = [
                axis_identifier(axis)
                for axis in font.axes
                if axis_identifier(axis) not in existing
            ]
            completed = dict(inherited)
            completed.update(existing)
            if missing_ids:
                repairs.append((layer, master, completed, missing_ids))
                print(
                    "  NEEDS REPAIR: %s | associated master: %s | missing: %s"
                    % (
                        label,
                        master.name,
                        ", ".join(
                            axis_label(axis)
                            for axis in font.axes
                            if axis_identifier(axis) in missing_ids
                        ),
                    )
                )
            else:
                print("  COMPLETE: %s | %s" % (label, coordinate_summary(font, existing)))
    except Exception as error:
        print("\nERROR: %s" % error)
        print("No changes were made.")
        Message("No Changes Made", "%s See the Macro window." % error)
        return

    if not repairs:
        print("\nNo missing coordinates were found. No changes were needed.")
        Message(
            "Intermediate Coordinates Complete",
            "All %i intermediate layer(s) already have complete coordinates."
            % len(intermediates),
        )
        return

    undo_started = False
    font.disableUpdateInterface()
    try:
        try:
            glyph.beginUndo()
            undo_started = True
        except Exception:
            pass
        for layer, master, completed, missing_ids in repairs:
            set_layer_attribute(layer, "coordinates", completed)
            print(
                "  REPAIRED: %s | %s"
                % (layer_label(layer), coordinate_summary(font, completed))
            )
    finally:
        if undo_started:
            try:
                glyph.endUndo()
            except Exception:
                pass
        font.enableUpdateInterface()

    print("\nRepaired intermediate layers: %i" % len(repairs))
    Message(
        "Intermediate Coordinates Repaired",
        "Filled missing coordinates on %i intermediate layer(s) in %s."
        % (len(repairs), glyph.name),
    )


main()
