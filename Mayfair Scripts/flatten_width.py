#MenuTitle: Flatten Width
# -*- coding: utf-8 -*-

"""Overwrite Width=113 layers with corresponding Width=95 layer contents.

For the currently selected glyph, master layers at Width=95 are matched to
master layers at Width=113. Coordinate-bearing intermediate layers at Width=95
are separately matched to their corresponding intermediate layers at
Width=113. Intermediate coordinates omitted from a layer's attributes are
inherited from its associated master before matching. All coordinates on axes
other than Width must agree. The target layer keeps its identity,
designspace coordinates, associated master, name, and color, but its shapes,
anchors, hints, guides, annotations, stems, advance width, and metrics keys are
replaced with copies from the source layer.

Missing or ambiguous matches are reported and skipped. Changes are grouped for
undo per glyph.
"""

from GlyphsApp import Glyphs, Message


SOURCE_WIDTH = 95.0
TARGET_WIDTH = 113.0
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
    for axis in font.axes:
        if axis_tag(axis).strip().lower() == "wdth":
            return axis
    for axis in font.axes:
        if axis_name(axis).strip().lower() == "width":
            return axis
    return None


def master_coordinates(font, master):
    result = {}
    for index, axis in enumerate(font.axes):
        axis_id = axis_identifier(axis)
        if axis_id is None:
            raise RuntimeError("A font axis has no identifier.")
        try:
            value = master.axisValueValueForId_(axis_id)
        except Exception:
            value = master.axesValues[index]
        result[axis_id] = float(value)
    return result


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


def format_number(value):
    try:
        number = float(value)
        return str(int(number)) if number.is_integer() else "%g" % number
    except Exception:
        return str(value)


def coordinate_summary(font, coordinates):
    parts = []
    for axis in font.axes:
        identifier = axis_identifier(axis)
        if identifier not in coordinates:
            continue
        label = axis_tag(axis).strip() or axis_name(axis).strip() or identifier
        parts.append("%s=%s" % (label, format_number(coordinates[identifier])))
    return ", ".join(parts) or "no coordinates"


def proxy_count(layer, attribute_name):
    try:
        return len(getattr(layer, attribute_name))
    except Exception:
        return 0


def contents_summary(layer):
    return (
        "shapes=%i, anchors=%i, hints=%i, guides=%i, annotations=%i, "
        "stems=%i, advance width=%s, metrics keys=(L=%r, R=%r, W=%r)"
        % (
            proxy_count(layer, "shapes"),
            proxy_count(layer, "anchors"),
            proxy_count(layer, "hints"),
            proxy_count(layer, "guides"),
            proxy_count(layer, "annotations"),
            proxy_count(layer, "stems"),
            format_number(layer.width),
            layer.leftMetricsKey,
            layer.rightMetricsKey,
            layer.widthMetricsKey,
        )
    )


def layer_records(font, glyph):
    """Return masters and intermediates with complete effective coordinates."""
    masters_by_id = {str(master.id): master for master in font.masters}
    records = []
    for layer in glyph.layers:
        if is_master_layer(layer):
            try:
                master = masters_by_id.get(str(layer.layerId))
            except Exception:
                master = None
            if master is None:
                try:
                    master = masters_by_id.get(str(layer.associatedMasterId))
                except Exception:
                    pass
            if master is None:
                continue
            records.append(
                {"layer": layer, "kind": "master", "coordinates": master_coordinates(font, master)}
            )
            continue
        raw_coordinates = layer_attribute(layer, "coordinates")
        if raw_coordinates is None:
            continue
        coordinates = coordinates_dict(font, raw_coordinates)
        if coordinates is None:
            continue
        master_id = associated_master_id(layer)
        associated_master = masters_by_id.get(master_id)
        if associated_master is not None:
            inherited_coordinates = master_coordinates(font, associated_master)
            inherited_coordinates.update(coordinates)
            coordinates = inherited_coordinates
        records.append(
            {"layer": layer, "kind": "intermediate", "coordinates": coordinates}
        )
    return records


def value_matches(value, wanted):
    return abs(float(value) - float(wanted)) <= TOLERANCE


def coordinates_match_except_width(first, second, width_axis_id):
    if set(first) != set(second):
        return False
    for axis_id in first:
        if axis_id == width_axis_id:
            continue
        if abs(first[axis_id] - second[axis_id]) > TOLERANCE:
            return False
    return True


def clear_proxy(proxy):
    try:
        proxy.clear()
        return
    except Exception:
        pass
    while len(proxy):
        try:
            proxy.remove(proxy[-1])
        except Exception:
            break


def copy_proxy(source_layer, target_layer, attribute_name):
    source_proxy = getattr(source_layer, attribute_name, None)
    target_proxy = getattr(target_layer, attribute_name, None)
    if source_proxy is None or target_proxy is None:
        return 0
    clear_proxy(target_proxy)
    copied = 0
    for item in source_proxy:
        try:
            target_proxy.append(item.copy())
            copied += 1
        except Exception as error:
            raise RuntimeError("Could not copy %s: %s" % (attribute_name, error))
    return copied


def copy_stems(source_layer, target_layer):
    if not hasattr(source_layer, "stems") or not hasattr(target_layer, "stems"):
        return 0
    try:
        target_layer.stems = [stem.copy() for stem in source_layer.stems]
        return len(source_layer.stems)
    except Exception:
        try:
            target_layer.stems = source_layer.stems.copy()
            return len(source_layer.stems)
        except Exception:
            return 0


def copy_layer_contents(source_layer, target_layer):
    """Replace target contents without replacing its designspace identity."""
    source_copy = source_layer.copy()
    counts = {}
    for attribute_name in ("shapes", "anchors", "hints", "guides", "annotations"):
        counts[attribute_name] = copy_proxy(source_copy, target_layer, attribute_name)
    counts["stems"] = copy_stems(source_copy, target_layer)
    try:
        target_layer.width = source_copy.width
    except Exception as error:
        raise RuntimeError("Could not copy layer width: %s" % error)
    for attribute_name in ("leftMetricsKey", "rightMetricsKey", "widthMetricsKey"):
        if not hasattr(source_copy, attribute_name) or not hasattr(target_layer, attribute_name):
            continue
        try:
            setattr(target_layer, attribute_name, getattr(source_copy, attribute_name))
        except Exception:
            pass
    return counts


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

    copied_master_layers = 0
    copied_intermediate_layers = 0
    missing_targets = []
    ambiguous_targets = []
    errors = []
    print("=" * 72)
    print("Flatten Width")
    print("=" * 72)
    print("Selected glyph: %s" % glyph.name)
    print(
        "Width axis: name=%r, tag=%r, identifier=%r"
        % (axis_name(width_axis), axis_tag(width_axis), width_axis_id)
    )
    print(
        "Operation: copy Width=%s contents to matching Width=%s layers."
        % (format_number(SOURCE_WIDTH), format_number(TARGET_WIDTH))
    )
    print("Coordinate comparison tolerance: %g" % TOLERANCE)
    print(
        "Layers match only when their kinds and every non-Width axis "
        "coordinate agree."
    )
    print(
        "Target layer identity, designspace coordinates, associated master, "
        "name, and color are preserved."
    )

    font.disableUpdateInterface()
    try:
        for glyph in (glyph,):
            try:
                records = layer_records(font, glyph)
            except Exception as error:
                errors.append("%s: reading layer coordinates: %s" % (glyph.name, error))
                continue
            sources = [
                record for record in records
                if width_axis_id in record["coordinates"]
                and value_matches(record["coordinates"][width_axis_id], SOURCE_WIDTH)
            ]
            targets = [
                record for record in records
                if width_axis_id in record["coordinates"]
                and value_matches(record["coordinates"][width_axis_id], TARGET_WIDTH)
            ]
            source_master_count = sum(item["kind"] == "master" for item in sources)
            source_intermediate_count = sum(
                item["kind"] == "intermediate" for item in sources
            )
            target_master_count = sum(item["kind"] == "master" for item in targets)
            target_intermediate_count = sum(
                item["kind"] == "intermediate" for item in targets
            )
            print("\nEligible master and intermediate layers: %i" % len(records))
            print(
                "Source layers at Width=%s: %i (%i master, %i intermediate)"
                % (
                    format_number(SOURCE_WIDTH),
                    len(sources),
                    source_master_count,
                    source_intermediate_count,
                )
            )
            for record in sources:
                print(
                    "  SOURCE [%s] %s | %s"
                    % (
                        record["kind"],
                        layer_label(record["layer"]),
                        coordinate_summary(font, record["coordinates"]),
                    )
                )
            print(
                "Target layers at Width=%s: %i (%i master, %i intermediate)"
                % (
                    format_number(TARGET_WIDTH),
                    len(targets),
                    target_master_count,
                    target_intermediate_count,
                )
            )
            for record in targets:
                print(
                    "  TARGET [%s] %s | %s"
                    % (
                        record["kind"],
                        layer_label(record["layer"]),
                        coordinate_summary(font, record["coordinates"]),
                    )
                )
            if not sources:
                print("No Width=%s source layers found; nothing changed." % format_number(SOURCE_WIDTH))
                continue

            undo_started = False
            try:
                glyph.beginUndo()
                undo_started = True
            except Exception:
                pass
            try:
                for source in sources:
                    print("\nConsidering source layer:")
                    print(
                        "  [%s] %s | %s"
                        % (
                            source["kind"],
                            layer_label(source["layer"]),
                            coordinate_summary(font, source["coordinates"]),
                        )
                    )
                    print("  Source contents: %s" % contents_summary(source["layer"]))
                    matches = [
                        target for target in targets
                        if target["kind"] == source["kind"]
                        and coordinates_match_except_width(
                            source["coordinates"], target["coordinates"], width_axis_id
                        )
                    ]
                    source_description = "%s / %s / %s" % (
                        glyph.name, source["kind"], layer_label(source["layer"])
                    )
                    if not matches:
                        missing_targets.append(source_description)
                        print("  Matching targets found: 0")
                        print("  SKIPPED: no target has matching non-Width coordinates.")
                        continue
                    if len(matches) > 1:
                        ambiguous_targets.append(
                            "%s -> %s"
                            % (
                                source_description,
                                ", ".join(layer_label(item["layer"]) for item in matches),
                            )
                        )
                        print("  Matching targets found: %i" % len(matches))
                        print("  SKIPPED: the target is ambiguous. Candidates:")
                        for item in matches:
                            print(
                                "    %s | %s"
                                % (
                                    layer_label(item["layer"]),
                                    coordinate_summary(font, item["coordinates"]),
                                )
                            )
                        continue
                    target = matches[0]
                    print("  Matching targets found: 1")
                    print(
                        "  Target: %s | %s"
                        % (
                            layer_label(target["layer"]),
                            coordinate_summary(font, target["coordinates"]),
                        )
                    )
                    print("  Target before copy: %s" % contents_summary(target["layer"]))
                    try:
                        counts = copy_layer_contents(source["layer"], target["layer"])
                        if source["kind"] == "master":
                            copied_master_layers += 1
                        else:
                            copied_intermediate_layers += 1
                        print(
                            "  COPIED %s -> %s | shapes=%i, anchors=%i, hints=%i, "
                            "guides=%i, annotations=%i, stems=%i"
                            % (
                                source_description,
                                layer_label(target["layer"]),
                                counts.get("shapes", 0),
                                counts.get("anchors", 0),
                                counts.get("hints", 0),
                                counts.get("guides", 0),
                                counts.get("annotations", 0),
                                counts.get("stems", 0),
                            )
                        )
                        print("  Target after copy:  %s" % contents_summary(target["layer"]))
                    except Exception as error:
                        errors.append("%s: %s" % (source_description, error))
                        print("  ERROR: %s" % error)
            finally:
                if undo_started:
                    try:
                        glyph.endUndo()
                    except Exception:
                        pass
    finally:
        font.enableUpdateInterface()

    print("\n" + "-" * 72)
    print("Summary")
    print("-" * 72)
    print("Copied master layers: %i" % copied_master_layers)
    print("Copied intermediate layers: %i" % copied_intermediate_layers)
    for item in missing_targets:
        print("MISSING TARGET: %s" % item)
    for item in ambiguous_targets:
        print("AMBIGUOUS TARGET: %s" % item)
    for item in errors:
        print("ERROR: %s" % item)

    warning_count = len(missing_targets) + len(ambiguous_targets) + len(errors)
    summary = "Copied %i master and %i intermediate layer(s)." % (
        copied_master_layers, copied_intermediate_layers
    )
    if warning_count:
        summary += " See the Macro window for %i warning(s)." % warning_count
    Message("Flatten Width Complete", summary)


main()
