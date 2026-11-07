#MenuTitle: Move Smart Circle Design from Width 95 to 100
# -*- coding: utf-8 -*-

"""Recalculate _smart.circle's Width=95 layers, keeping Width=113 fixed.

Run in Glyphs with the intended font open. Only _smart.circle is affected;
the script does not save the font. The original Width=95 result is moved to
Width=100 at every smart height, weight, and optical size. Node X/Y, anchors,
and advance widths are recalculated without rounding:

    new95 = (18 * old95 - 5 * old113) / 13

Each pair must agree on EVERY other font axis. Height is the glyph's one
local smart axis, not a font axis. Missing counterparts are sampled from the
ORIGINAL combined font-axis/smart-height interpolation, using Glyphs' native
VarLibModel. This accounts for sparse intermediates affecting other masters.
Missing Width=95 height layers are added where necessary.
For the original Somerville source this updates nine layers and adds one:
Agate Black SemiCondensed at smart height 30. Width=113 is never written.

Requires Glyphs' native VarLibModel class. Reads legacy pole mappings and
one-element smart coordinates as well as Glyphs 4 coordinate dictionaries.
Unrecognized or ambiguous setups,
incompatible paths, components, and unsupported font-width locations abort
before edits. All interpolation and layer creation are prepared and checked
first. Read-back verification follows the edits; failure restores the old
layers and removes new layers. The operation is one glyph undo group. Layer
copies are positioned through the unrounded native API, then installed by ID;
the font grid is not changed. Existing layer IDs and metadata are retained.

A persistent userData marker prevents accidentally applying this twice.
Undo removes that marker too. A full original glyph copy is retained for the
current session via glyph.tempDataForKey_(BACKUP_KEY). It is not saved to disk.
For a read-only report from the Macro window:

    report = recenter(Glyphs.font, dry_run=True)
"""

from datetime import datetime
from itertools import product
import math
import uuid


GLYPH_NAME = "_smart.circle"
OLD_WIDTH = 95.0
NEW_WIDTH = 100.0
FIXED_WIDTH = 113.0
EPSILON = 1e-8
MARKER_KEY = "com.somerville.smartCircleWidth95To100.v1"
BACKUP_KEY = MARKER_KEY + ".originalGlyph"


def value(obj, name, default=None):
    result = getattr(obj, name, default)
    return result() if callable(result) else result


def identifier(axis):
    result = value(axis, "axisId") or value(axis, "id")
    if not result:
        raise ValueError("An axis has no identifier.")
    return str(result)


def attribute(layer, name):
    try:
        return layer.attributes[name]
    except KeyError:
        return None


def close(first, second):
    return abs(first - second) <= EPSILON


def master_coordinates(master, axes):
    coordinates = []
    for index, axis in enumerate(axes):
        try:
            number = master.axisValueValueForId_(identifier(axis))
        except AttributeError:
            number = master.axes[index]
        coordinates.append(float(number))
    return coordinates


def smart_axis(glyph):
    modern = hasattr(glyph, "axes")
    axes = list(glyph.axes if modern else glyph.smartComponentAxes)
    if len(axes) != 1 or str(axes[0].name).lower() != "height":
        raise ValueError("Expected exactly one glyph-local smart axis named height.")
    axis = axes[0]
    if modern:
        if not close(float(value(axis, "defaultValue")), 0.0):
            raise ValueError("The height axis default must be 0.")
    elif not (close(float(axis.bottomValue), 0.0)
              and close(float(axis.topValue), 100.0)):
        raise ValueError("Expected smart height endpoints 0 and 100.")
    return axis, modern


def pole_height(layer, axis):
    """Use relevant pole keys only; conflicting name/ID mappings are unsafe."""
    mappings = [attribute(layer, "partSelection")]
    try:
        mappings.append(layer.smartComponentPoleMapping)
    except (AttributeError, NotImplementedError):
        pass
    poles = set()
    for mapping in mappings:
        if mapping is None:
            continue
        for key in (identifier(axis), str(axis.name)):
            try:
                result = mapping[key]
            except KeyError:
                continue
            if result is not None:
                poles.add(int(result))
    if not poles:
        return None
    if len(poles) != 1 or not poles.issubset({1, 2}):
        raise ValueError("Conflicting height poles on layer %r." % layer.name)
    return 0.0 if poles == {1} else 100.0


def geometry(layer):
    if len(layer.components) or len(layer.shapes) != len(layer.paths):
        raise ValueError("Only outline paths are supported: %r." % layer.name)
    paths = list(layer.paths)
    if not paths:
        raise ValueError("Empty outline: %r." % layer.name)
    topology = tuple(
        (bool(path.closed), tuple((node.type, bool(node.smooth)) for node in path.nodes))
        for path in paths
    )
    anchors = list(layer.anchors)
    if any(int(value(item, "orientation", 0)) != 0
           for item in anchors + [node for path in paths for node in path.nodes]):
        raise ValueError("Non-default node/anchor orientation on %r." % layer.name)
    names = [str(anchor.name) for anchor in anchors]
    if len(set(names)) != len(names):
        raise ValueError("Duplicate anchor names on %r." % layer.name)
    points = tuple(
        (float(node.position.x), float(node.position.y))
        for path in paths for node in path.nodes
    )
    anchor_points = {
        str(anchor.name): (float(anchor.position.x), float(anchor.position.y))
        for anchor in anchors
    }
    result = {"topology": topology, "points": points,
              "anchors": anchor_points, "width": float(layer.width)}
    if not all(math.isfinite(number) for number in numbers(result)):
        raise ValueError("Non-finite geometry on %r." % layer.name)
    return result


def numbers(data):
    for point in data["points"]:
        yield from point
    for name in sorted(data["anchors"]):
        yield from data["anchors"][name]
    yield data["width"]


def blend(first, second, factor):
    if (first["topology"] != second["topology"]
            or set(first["anchors"]) != set(second["anchors"])):
        raise ValueError("Corresponding layers have incompatible paths or anchors.")

    def scalar(a, b):
        return a + factor * (b - a)

    def point(a, b):
        return (scalar(a[0], b[0]), scalar(a[1], b[1]))

    return {
        "topology": first["topology"],
        "points": tuple(point(a, b) for a, b in zip(first["points"], second["points"])),
        "anchors": {name: point(first["anchors"][name], second["anchors"][name])
                    for name in first["anchors"]},
        "width": scalar(first["width"], second["width"]),
    }


def assert_geometry(actual, expected, label):
    if (actual["topology"] != expected["topology"]
            or set(actual["anchors"]) != set(expected["anchors"])):
        raise ValueError("Structure changed: %s." % label)
    error = max(abs(a - b) for a, b in zip(numbers(actual), numbers(expected)))
    if not math.isfinite(error) or error > EPSILON:
        raise ValueError("%s differs by %g units." % (label, error))
    return error


def collect(font, glyph):
    axis, modern = smart_axis(glyph)
    axes = list(font.axes)
    ids = [identifier(item) for item in axes]
    widths = [i for i, item in enumerate(axes)
              if str(value(item, "axisTag", "")).lower() == "wdth"]
    if len(widths) != 1:
        raise ValueError("Expected exactly one font axis tagged wdth.")
    width_index = widths[0]
    masters = {str(master.id): master for master in font.masters}
    groups = {}
    for layer in glyph.layers:
        master = masters.get(str(layer.associatedMasterId or layer.layerId))
        if master is None:
            raise ValueError("Layer %r has no associated master." % layer.name)
        coordinates = master_coordinates(master, axes)
        raw = attribute(layer, "coordinates")
        height = None
        if raw is not None and len(raw):
            if hasattr(raw, "keys"):
                local_keys = {identifier(axis), str(axis.name)}
                local_values = set()
                for key in raw.keys():
                    if str(key) in local_keys:
                        local_values.add(float(raw[key]))
                    elif str(key) in ids:
                        coordinates[ids.index(str(key))] = float(raw[key])
                    else:
                        raise ValueError("Unknown coordinate axis %r on %r." % (key, layer.name))
                if len(local_values) > 1:
                    raise ValueError("Conflicting smart height coordinates.")
                height = next(iter(local_values), 0.0)
            else:
                if len(raw) != 1:
                    raise ValueError("Expected one smart-height coordinate on %r." % layer.name)
                height = float(raw[0])
        elif modern and str(layer.layerId) in masters:
            height = 0.0
        else:
            height = pole_height(layer, axis)
        if height is None:
            # Ordinary backup layers have neither coordinates nor height poles.
            continue
        if attribute(layer, "axisRules") is not None:
            raise ValueError("Alternate layers are unsupported: %r." % layer.name)
        if not all(math.isfinite(number) for number in coordinates + [height]):
            raise ValueError("Non-finite layer coordinates.")
        width = coordinates[width_index]
        if not (close(width, OLD_WIDTH) or close(width, FIXED_WIDTH)):
            raise ValueError("Unexpected participating font width %g." % width)
        width = OLD_WIDTH if close(width, OLD_WIDTH) else FIXED_WIDTH
        if height < 0 or height > 100:
            raise ValueError("Expected smart height in [0, 100].")
        key = tuple(number for index, number in enumerate(coordinates) if index != width_index)
        curve = groups.setdefault(key, {OLD_WIDTH: {}, FIXED_WIDTH: {}})[width]
        if height in curve:
            raise ValueError("Duplicate layers at the same font coordinates and smart height.")
        curve[height] = {"layer": layer, "master": master, "data": geometry(layer),
                         "location": tuple(coordinates + [height])}
    if not groups:
        raise ValueError("No participating smart-circle layers found.")
    for group in groups.values():
        for curve in group.values():
            if not {0.0, 100.0}.issubset(curve):
                raise ValueError("Every width/weight/optical-size group needs height 0 and 100.")
            baseline = curve[0.0]["data"]
            for record in curve.values():
                blend(baseline, record["data"], 0.0)  # Validate correspondence.
        blend(group[OLD_WIDTH][0.0]["data"], group[FIXED_WIDTH][0.0]["data"], 0.0)
    return groups, axis, modern, ids[width_index]


def native_model(locations, axis_order):
    import objc

    try:
        cls = objc.lookUpClass("VarLibModel")
    except objc.nosuchclass_error:
        raise ValueError("This script requires a Glyphs version with native VarLibModel.")
    return cls.alloc().initWithLocations_axisOrder_extrapolate_(locations, axis_order, True)


class CombinedModel:
    """Native weights in the complete font + glyph-local design space."""

    def __init__(self, records, axis_order, origin, width_index, factory=native_model,
                 ranges=None):
        self.records = list(records)
        self.axis_order = axis_order
        self.origin = origin
        self.width_index = width_index
        self.factory = factory
        if ranges is None:
            ranges = [(min(r["location"][i] for r in records), origin[i],
                       max(r["location"][i] for r in records))
                      for i in range(len(axis_order))]
        self.ranges = ranges
        self.model = factory([self.normalize(r["location"]) for r in records], axis_order)
        if self.model is None:
            raise ValueError("Glyphs could not construct the combined interpolation model.")
        self.template = records[0]["data"]
        for record in records:
            blend(self.template, record["data"], 0.0)

    def normalize(self, location):
        result = {}
        for axis_id, number, (low, default, high) in zip(
                self.axis_order, location, self.ranges):
            if close(number, default):
                continue
            span = high - default if number > default else default - low
            if close(span, 0.0):
                raise ValueError("Cannot normalize an axis beyond its sampled range.")
            result[axis_id] = (number - default) / span
        return result

    def at(self, location):
        weights = list(self.model.masterScalarsForLocation_(self.normalize(location)))
        if len(weights) != len(self.records):
            raise ValueError("Native interpolation returned the wrong number of coefficients.")
        if not all(math.isfinite(float(w)) for w in weights) or abs(math.fsum(weights) - 1) > EPSILON:
            raise ValueError("Invalid native interpolation coefficients.")
        values = [tuple(numbers(record["data"])) for record in self.records]
        combined = [math.fsum(float(w) * column[i] for w, column in zip(weights, values))
                    for i in range(len(values[0]))]
        it = iter(combined)
        points = tuple((next(it), next(it)) for unused in self.template["points"])
        anchors = {name: (next(it), next(it)) for name in sorted(self.template["anchors"])}
        return {"topology": self.template["topology"], "points": points,
                "anchors": anchors, "width": next(it)}

    def with_records(self, records):
        return CombinedModel(records, self.axis_order, self.origin, self.width_index,
                             self.factory, self.ranges)


def model_records(groups):
    return [record for group in groups.values() for curve in group.values()
            for record in curve.values()]


def original_model(font, glyph, groups, factory):
    axes = list(font.axes)
    height_axis, unused_modern = smart_axis(glyph)
    try:
        default_master = font.defaultFontMaster_(None)
    except AttributeError:
        default_master = font.masters[0]
    origin = tuple(master_coordinates(default_master, axes) + [0.0])
    ids = [identifier(axis) for axis in axes] + [identifier(height_axis)]
    width_index = next(i for i, axis in enumerate(axes)
                       if str(value(axis, "axisTag", "")).lower() == "wdth")
    return CombinedModel(model_records(groups), ids, origin, width_index, factory)


def verify_models(original, changed):
    """Check every cell's corners and interiors in all non-width dimensions."""
    choices = []
    for index in range(len(original.axis_order)):
        if index == original.width_index:
            choices.append([OLD_WIDTH])
            continue
        knots = sorted({r["location"][index] for r in original.records + changed.records})
        choices.append(sorted(set(knots + [(a + b) / 2 for a, b in zip(knots, knots[1:])])))
    if math.prod(len(choice) for choice in choices) > 10000:
        raise ValueError("Too many design-space cells for this glyph-specific script.")
    maximum_error = 0.0
    for location in product(*choices):
        old_location = list(location)
        new_location = list(location)
        new_location[original.width_index] = NEW_WIDTH
        maximum_error = max(maximum_error, assert_geometry(
            changed.at(new_location), original.at(old_location), "Width 100 reconstruction"))
        old_location[original.width_index] = FIXED_WIDTH
        maximum_error = max(maximum_error, assert_geometry(
            changed.at(old_location), original.at(old_location), "Width 113 curve preservation"))
    return maximum_error


def prepare(font, glyph, model_factory=native_model):
    groups, axis, modern, width_id = collect(font, glyph)
    original = original_model(font, glyph, groups, model_factory)
    changes = []
    factor = -(NEW_WIDTH - OLD_WIDTH) / (FIXED_WIDTH - NEW_WIDTH)
    for key, group in groups.items():
        for height in sorted(set(group[OLD_WIDTH]) | set(group[FIXED_WIDTH])):
            location = list(group[OLD_WIDTH][0.0]["location"])
            location[-1] = height
            expanded_location = list(location)
            expanded_location[original.width_index] = FIXED_WIDTH
            data = blend(original.at(location), original.at(expanded_location), factor)
            if height in group[OLD_WIDTH]:
                source = group[OLD_WIDTH][height]["layer"]
                layer = source.copy()
                layer.layerId = str(source.layerId)
                added = False
            else:
                # An expanded intermediate supplies the new layer's metadata shell.
                layer = group[FIXED_WIDTH][height]["layer"].copy()
                layer.layerId = str(uuid.uuid4()).upper()
                layer.associatedMasterId = str(group[OLD_WIDTH][0.0]["master"].id)
                layer.name = "%s height %g" % (group[OLD_WIDTH][0.0]["master"].name, height)
                if modern:
                    raw = attribute(layer, "coordinates")
                    coordinates = {str(k): float(raw[k]) for k in raw.keys()}
                    coordinates[identifier(axis)] = height
                    if width_id in coordinates:
                        coordinates[width_id] = OLD_WIDTH
                    layer.attributes["coordinates"] = coordinates
                else:
                    layer.attributes["coordinates"] = [height]
                # An intermediate must not also claim an endpoint pole.
                if attribute(layer, "partSelection") is not None:
                    del layer.attributes["partSelection"]
                added = True
            # Work only on detached copies; whole-layer replacement supplies undo.
            layer.parent = None
            changes.append({"layer": layer, "added": added, "height": height,
                            "data": data, "location": tuple(location),
                            "label": layer.name or group[OLD_WIDTH][0.0]["master"].name})
    candidate = original.with_records(changes + [record for group in groups.values()
                                                for record in group[FIXED_WIDTH].values()])
    error = verify_models(original, candidate)
    return groups, changes, error, original


def set_geometry(layer, data):
    from Foundation import NSPoint

    nodes = [node for path in layer.paths for node in path.nodes]
    layer.setWidthFast_(data["width"])
    for node, point in zip(nodes, data["points"]):
        node.setPositionFast_(NSPoint(*point))
    for anchor in layer.anchors:
        anchor.setPositionFast_(NSPoint(*data["anchors"][str(anchor.name)]))
    for path in layer.paths:
        path.elementDidChange_(None)
    layer.setNeedUpdateShapes()
    layer.setNeedUpdateMetrics()


def recenter(font, dry_run=False, model_factory=native_model):
    if font is None:
        raise ValueError("Open the intended Somerville font first.")
    glyph = font.glyphs[GLYPH_NAME]
    if glyph is None:
        raise ValueError("The open font has no %s glyph." % GLYPH_NAME)
    if glyph.userData[MARKER_KEY]:
        raise ValueError("This adjustment has already been applied. Undo it before running again.")
    groups, changes, error, original = prepare(font, glyph, model_factory)
    report = {
        "updated": sum(not change["added"] for change in changes),
        "added": sum(change["added"] for change in changes),
        "unchanged_expanded": sum(len(group[FIXED_WIDTH]) for group in groups.values()),
        "maximum_error": error,
        "dry_run": dry_run,
    }
    for change in changes:
        print("%s: %s; smart height %g; new advance %.10g" % (
            "Add" if change["added"] else "Update", change["label"],
            change["height"], change["data"]["width"]))
    if dry_run:
        print("Dry run: %s" % report)
        return report

    # Populate and verify all detached copies before changing the open font.
    for change in changes:
        set_geometry(change["layer"], change["data"])
        assert_geometry(geometry(change["layer"]), change["data"], "Prepared precise layer")

    # Keep the untouched original layer objects for exact rollback.
    originals = [record["layer"]
                 for group in groups.values() for record in group[OLD_WIDTH].values()]
    backup = glyph.copy()
    # GSGlyph.tempData is a native selector in Glyphs 4, not a Python dict proxy.
    # Store the backup before edits, so a storage error cannot change the font.
    glyph.setTempData_forKey_(backup, BACKUP_KEY)
    added_ids = []
    font.disableUpdateInterface()
    undo_open = False
    try:
        glyph.beginUndo()
        undo_open = True
        for change in changes:
            layer = change["layer"]
            if change["added"]:
                added_ids.append(str(layer.layerId))
            # append() assigns a fresh ID in Glyphs 4; retain all existing IDs.
            glyph.layers[str(layer.layerId)] = layer
            assert_geometry(geometry(layer), change["data"], "Written layer %r" % layer.name)
        after, unused_axis, unused_modern, unused_width = collect(font, glyph)
        if set(after) != set(groups):
            raise ValueError("Font-axis grouping changed during the operation.")
        for key, group in after.items():
            if set(group[FIXED_WIDTH]) != set(groups[key][FIXED_WIDTH]):
                raise ValueError("Expanded layer heights changed.")
            for height, record in group[FIXED_WIDTH].items():
                assert_geometry(record["data"], groups[key][FIXED_WIDTH][height]["data"],
                                "Unchanged expanded layer")
        report["maximum_error"] = verify_models(original, original.with_records(model_records(after)))
        glyph.userData[MARKER_KEY] = {"date": datetime.now().isoformat(),
                                     "from": OLD_WIDTH, "to": NEW_WIDTH,
                                     "fixed": FIXED_WIDTH}
    except Exception:
        for layer_id in added_ids:
            if glyph.layers[layer_id] is not None:
                del glyph.layers[layer_id]
        for layer in originals:
            glyph.layers[str(layer.layerId)] = layer
        if glyph.userData[MARKER_KEY]:
            del glyph.userData[MARKER_KEY]
        raise
    finally:
        try:
            if undo_open:
                glyph.endUndo()
        finally:
            font.enableUpdateInterface()
    print("Completed %s: %s" % (GLYPH_NAME, report))
    return report


def main():
    from GlyphsApp import Glyphs, Message
    import traceback

    try:
        recenter(Glyphs.font)
    except Exception as error:
        Glyphs.showMacroWindow()
        traceback.print_exc()
        Message("Smart Circle Width Adjustment", str(error))


if __name__ == "__main__":
    main()
