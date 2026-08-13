#MenuTitle: Add Arrow Intermediate Layers
# -*- coding: utf-8 -*-

"""Add selected Arrow Length/Arrow Head intermediates below every master.

Run this Glyphs 3 script with a glyph selected in Font View or open in Edit
View. Its window offers four kinds of intermediate layer: ARLN=0, ARHD=100,
ARLN=200 plus ARHD=200, and ARLN=0 plus ARHD=200. For every enabled kind and
every font master, the script copies that glyph's master layer and associates
the copy with the same master. Each new layer receives the master's complete
coordinate set with only the selected ARLN and/or ARHD coordinates overridden.

If the glyph already has an intermediate layer associated with that master at
the same complete coordinates, the existing layer is kept and reported. A
proposed intermediate whose complete coordinates equal its actual master's
coordinates is skipped, because such a layer can cause an export error. No
other glyphs or layers are changed. The operation is grouped for undo and a
detailed report is printed in the Macro window.
"""

import uuid

import vanilla
from GlyphsApp import Glyphs, Message


TOLERANCE = 0.0001
LAYER_KINDS = (
    ("addARLN0", "ARLN=0", {"ARLN": 0.0}),
    ("addARHD100", "ARHD=100", {"ARHD": 100.0}),
    ("addARLN200ARHD200", "ARLN=200, ARHD=200", {"ARLN": 200.0, "ARHD": 200.0}),
    ("addARLN0ARHD200", "ARLN=0, ARHD=200", {"ARLN": 0.0, "ARHD": 200.0}),
)


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


def find_axis(font, wanted_tag, wanted_name):
    for axis in font.axes:
        if axis_tag(axis).strip().upper() == wanted_tag:
            return axis
    for axis in font.axes:
        normalized_name = axis_name(axis).strip().lower().replace(" ", "")
        if normalized_name in (wanted_name.lower().replace(" ", ""), wanted_tag.lower()):
            return axis
    return None


def master_coordinates(font, master):
    """Return every designspace coordinate for a master, keyed by axis ID."""
    coordinates = {}
    for index, axis in enumerate(font.axes):
        axis_id = axis_identifier(axis)
        if axis_id is None:
            raise RuntimeError("A font axis has no identifier.")
        try:
            value = master.axisValueValueForId_(axis_id)
        except Exception:
            value = master.axesValues[index]
        coordinates[axis_id] = float(value)
    return coordinates


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


def coordinates_dict(font, value):
    if value is None:
        return None
    if hasattr(value, "keys"):
        return {str(key): float(value[key]) for key in value.keys()}
    values = list(value)
    if len(values) != len(font.axes):
        return None
    return {
        axis_identifier(axis): float(values[index])
        for index, axis in enumerate(font.axes)
    }


def associated_master_id(layer):
    try:
        value = layer.associatedMasterId
        return str(value) if value else None
    except Exception:
        return None


def is_master_layer(layer):
    try:
        return bool(layer.isMasterLayer)
    except Exception:
        return False


def coordinates_match(first, second):
    if first is None or second is None or set(first) != set(second):
        return False
    return all(abs(first[key] - second[key]) <= TOLERANCE for key in first)


def master_layer_for_glyph(glyph, master):
    try:
        return glyph.layers[master.id]
    except Exception:
        pass
    for layer in glyph.layers:
        try:
            if is_master_layer(layer) and str(layer.layerId) == str(master.id):
                return layer
        except Exception:
            pass
    return None


def existing_intermediate(glyph, font, master, wanted_coordinates):
    for layer in glyph.layers:
        if is_master_layer(layer):
            continue
        if associated_master_id(layer) != str(master.id):
            continue
        current_coordinates = coordinates_dict(
            font, layer_attribute(layer, "coordinates")
        )
        if current_coordinates is not None:
            effective_coordinates = master_coordinates(font, master)
            effective_coordinates.update(current_coordinates)
            current_coordinates = effective_coordinates
        if coordinates_match(current_coordinates, wanted_coordinates):
            return layer
    return None


def format_number(value):
    number = float(value)
    return str(int(number)) if number.is_integer() else "%g" % number


def coordinate_summary(font, coordinates):
    parts = []
    for axis in font.axes:
        axis_id = axis_identifier(axis)
        label = axis_tag(axis).strip() or axis_name(axis).strip() or axis_id
        parts.append("%s=%s" % (label, format_number(coordinates[axis_id])))
    return ", ".join(parts)


def selected_glyph(font):
    try:
        layers = list(font.selectedLayers or [])
        if layers:
            return layers[0].parent
    except Exception:
        pass
    return None


class AddArrowIntermediateLayersWindow(object):
    def __init__(self):
        self.w = vanilla.FloatingWindow(
            (370, 245),
            "Add Arrow Intermediate Layers",
            minSize=(370, 245),
            maxSize=(520, 245),
        )
        self.w.intro = vanilla.TextBox(
            (15, 14, -15, 34),
            "For the current glyph, add the selected intermediate layers "
            "below every master:",
        )
        y = 55
        for control_name, label, overrides in LAYER_KINDS:
            setattr(self.w, control_name, vanilla.CheckBox((18, y, -18, 20), label, value=False))
            y += 28
        self.w.status = vanilla.TextBox(
            (15, 174, -15, 18),
            "Existing layers and coordinates equal to a master are skipped.",
        )
        self.w.cancel = vanilla.Button((-190, -38, 80, 22), "Cancel", callback=self.cancel)
        self.w.run = vanilla.Button((-100, -38, 85, 22), "Add Layers", callback=self.run)
        self.w.setDefaultButton(self.w.run)
        self.w.open()
        self.w.makeKey()

    def cancel(self, sender):
        self.w.close()

    def selected_kinds(self):
        return [
            (label, overrides)
            for control_name, label, overrides in LAYER_KINDS
            if bool(getattr(self.w, control_name).get())
        ]

    def run(self, sender):
        font = Glyphs.font
        if font is None:
            Message("No Font Open", "Open a font before running this script.")
            return
        glyph = selected_glyph(font)
        if glyph is None:
            Message(
                "No Glyph Selected",
                "Select a glyph in Font View or open a glyph in Edit View first.",
            )
            return
        selected_kinds = self.selected_kinds()
        if not selected_kinds:
            Message("Nothing Selected", "Select at least one kind of intermediate layer.")
            return

        required_tags = set()
        for label, overrides in selected_kinds:
            required_tags.update(overrides)
        axes_by_tag = {}
        axis_names = {"ARLN": "Arrow Length", "ARHD": "Arrow Head"}
        for tag in required_tags:
            axis = find_axis(font, tag, axis_names[tag])
            if axis is None:
                Message(
                    "%s Axis Not Found" % tag,
                    "The font needs an axis tagged %s or named %s."
                    % (tag, axis_names[tag]),
                )
                return
            axis_id = axis_identifier(axis)
            if axis_id is None:
                Message("Invalid %s Axis" % tag, "The %s axis has no identifier." % tag)
                return
            axes_by_tag[tag] = axis_id

        print("=" * 72)
        print("Add Arrow Intermediate Layers")
        print("=" * 72)
        print("Selected glyph: %s" % glyph.name)
        print("Selected layer kinds: %s" % "; ".join(item[0] for item in selected_kinds))
        print("Masters to inspect: %i" % len(font.masters))

        created = 0
        existing = 0
        same_as_master = 0
        errors = []
        undo_started = False
        font.disableUpdateInterface()
        try:
            try:
                glyph.beginUndo()
                undo_started = True
            except Exception:
                pass

            for master in font.masters:
                source_layer = master_layer_for_glyph(glyph, master)
                for label, overrides in selected_kinds:
                    try:
                        print("\nMaster: %s | kind: %s" % (master.name, label))
                        if source_layer is None:
                            raise RuntimeError("The glyph has no layer for this master.")
                        actual_master_coordinates = master_coordinates(font, master)
                        coordinates = dict(actual_master_coordinates)
                        for tag, value in overrides.items():
                            coordinates[axes_by_tag[tag]] = float(value)
                        print("  Coordinates: %s" % coordinate_summary(font, coordinates))

                        if coordinates_match(coordinates, actual_master_coordinates):
                            same_as_master += 1
                            print(
                                "  SKIPPED: these coordinates are identical to "
                                "the actual master coordinates."
                            )
                            continue

                        current_layer = existing_intermediate(
                            glyph, font, master, coordinates
                        )
                        if current_layer is not None:
                            existing += 1
                            print(
                                "  KEPT existing layer: %s"
                                % (current_layer.name or current_layer.layerId)
                            )
                            continue

                        new_layer = source_layer.copy()
                        new_layer.layerId = str(uuid.uuid4()).upper()
                        new_layer.associatedMasterId = master.id
                        new_layer.name = "%s %s" % (master.name, label)
                        set_layer_attribute(new_layer, "coordinates", coordinates)
                        glyph.layers.append(new_layer)
                        created += 1
                        print("  CREATED: %s" % new_layer.name)
                    except Exception as error:
                        errors.append("%s / %s: %s" % (master.name, label, error))
                        print("  ERROR: %s" % error)
        finally:
            if undo_started:
                try:
                    glyph.endUndo()
                except Exception:
                    pass
            font.enableUpdateInterface()

        print("\n" + "-" * 72)
        print("Created: %i" % created)
        print("Already present: %i" % existing)
        print("Skipped because coordinates equal the master: %i" % same_as_master)
        print("Errors: %i" % len(errors))
        for error in errors:
            print("ERROR: %s" % error)

        self.w.status.set(
            "Created %i; existing %i; same as master %i; errors %i."
            % (created, existing, same_as_master, len(errors))
        )
        summary = (
            "Created %i intermediate layer(s); %i already existed; "
            "%i matched a master and were skipped."
            % (created, existing, same_as_master)
        )
        if errors:
            summary += " See the Macro window for %i error(s)." % len(errors)
        Message("Arrow Intermediate Layers", summary)


AddArrowIntermediateLayersWindow()
