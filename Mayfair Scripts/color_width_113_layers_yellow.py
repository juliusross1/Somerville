#MenuTitle: Color Width 113 Layers Yellow
# -*- coding: utf-8 -*-

"""Color master and intermediate layers associated with Width=113 yellow.

In the currently selected glyph, this script colors:

* master layers whose master's Width-axis coordinate is 113; and
* coordinate-bearing intermediate layers whose own Width coordinate is 113,
  or whose associated master has Width=113.

Other special layers are left unchanged. Glyphs' palette index 3 is yellow.
The Macro window reports every changed layer and a final summary.
"""

from GlyphsApp import Glyphs, Message


TARGET_WIDTH = 113.0
YELLOW_COLOR_INDEX = 3
TOLERANCE = 0.0001


def axis_identifier(axis):
    for attribute_name in ("id", "axisId"):
        try:
            value = getattr(axis, attribute_name)
            if callable(value):
                value = value()
            if value:
                return str(value)
        except Exception:
            pass
    return None


def axis_name(axis):
    try:
        return str(axis.name or "")
    except Exception:
        return ""


def axis_tag(axis):
    for attribute_name in ("axisTag", "tag"):
        try:
            value = getattr(axis, attribute_name)
            if callable(value):
                value = value()
            if value:
                return str(value)
        except Exception:
            pass
    return ""


def find_width_axis(font):
    """Find Width, preferring the registered wdth tag over its display name."""
    for axis in font.axes:
        if axis_tag(axis).strip().lower() == "wdth":
            return axis
    for axis in font.axes:
        if axis_name(axis).strip().lower() == "width":
            return axis
    return None


def master_axis_value(font, master, axis, axis_id):
    try:
        return float(master.axisValueValueForId_(axis_id))
    except Exception:
        axis_index = list(font.axes).index(axis)
        return float(master.axesValues[axis_index])


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


def coordinates_dict(font, value):
    if value is None:
        return None
    if hasattr(value, "keys"):
        result = {}
        for key in value.keys():
            result[str(key)] = float(value[key])
        return result
    values = list(value)
    if len(values) != len(font.axes):
        return None
    return {
        axis_identifier(axis): float(values[index])
        for index, axis in enumerate(font.axes)
    }


def is_master_layer(layer):
    try:
        return bool(layer.isMasterLayer)
    except Exception:
        return False


def associated_master_id(layer):
    try:
        value = layer.associatedMasterId
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


def is_target_value(value):
    return abs(float(value) - TARGET_WIDTH) <= TOLERANCE


def main():
    font = Glyphs.font
    if font is None:
        Message("No Font Open", "Open a font before running this script.")
        return
    try:
        selected_layers = list(font.selectedLayers or [])
        glyph = selected_layers[0].parent if selected_layers else None
    except Exception:
        glyph = None
    if glyph is None:
        Message(
            "No Glyph Selected",
            "Select a glyph in Font View or Edit View before running this script.",
        )
        return

    width_axis = find_width_axis(font)
    if width_axis is None:
        Message(
            "Width Axis Not Found",
            "The font needs an axis tagged wdth or named Width.",
        )
        return
    width_axis_id = axis_identifier(width_axis)
    if width_axis_id is None:
        Message("Invalid Width Axis", "The Width axis has no identifier.")
        return

    target_master_ids = set()
    target_master_names = []
    for master in font.masters:
        try:
            value = master_axis_value(font, master, width_axis, width_axis_id)
        except Exception as error:
            Message(
                "Could Not Read Master Width",
                "%s: %s" % (master.name, error),
            )
            return
        if is_target_value(value):
            target_master_ids.add(str(master.id))
            target_master_names.append(str(master.name))

    changed_master_layers = 0
    changed_intermediate_layers = 0
    already_yellow = 0
    print("Color Width 113 Layers Yellow")
    print("Glyph: %s" % glyph.name)
    print("Width axis: %s (%s)" % (axis_name(width_axis), axis_tag(width_axis)))
    print(
        "Masters at Width=113: %s"
        % (", ".join(target_master_names) if target_master_names else "none")
    )

    font.disableUpdateInterface()
    try:
        for glyph in (glyph,):
            glyph_undo_started = False
            try:
                glyph.beginUndo()
                glyph_undo_started = True
            except Exception:
                pass
            try:
                for layer in glyph.layers:
                    should_color = False
                    layer_kind = None
                    if is_master_layer(layer):
                        try:
                            master_id = str(layer.layerId)
                        except Exception:
                            master_id = associated_master_id(layer)
                        if master_id in target_master_ids:
                            should_color = True
                            layer_kind = "master"
                    else:
                        raw_coordinates = layer_attribute(layer, "coordinates")
                        if raw_coordinates is None:
                            continue
                        coordinates = coordinates_dict(font, raw_coordinates)
                        own_width_matches = (
                            coordinates is not None
                            and width_axis_id in coordinates
                            and is_target_value(coordinates[width_axis_id])
                        )
                        under_target_master = (
                            associated_master_id(layer) in target_master_ids
                        )
                        if own_width_matches or under_target_master:
                            should_color = True
                            layer_kind = "intermediate"

                    if not should_color:
                        continue
                    try:
                        current_color = layer.color
                    except Exception:
                        current_color = None
                    if current_color == YELLOW_COLOR_INDEX:
                        already_yellow += 1
                        continue
                    layer.color = YELLOW_COLOR_INDEX
                    if layer_kind == "master":
                        changed_master_layers += 1
                    else:
                        changed_intermediate_layers += 1
                    print(
                        "  %s | %s | %s -> yellow"
                        % (glyph.name, layer_kind, layer_label(layer))
                    )
            finally:
                if glyph_undo_started:
                    try:
                        glyph.endUndo()
                    except Exception:
                        pass
    finally:
        font.enableUpdateInterface()

    summary = (
        "Colored %i master layer(s) and %i intermediate layer(s) yellow. "
        "%i layer(s) were already yellow."
        % (changed_master_layers, changed_intermediate_layers, already_yellow)
    )
    print(summary)
    Message("Width 113 Layers Colored", summary)


main()
