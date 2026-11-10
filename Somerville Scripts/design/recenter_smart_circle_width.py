#MenuTitle: Move Smart Circle Design from Width 95 to 100
# -*- coding: utf-8 -*-

"""Build _smart.circle from _smart.circle.uncentered, moving Width 95 to 100.

Run in Glyphs with the intended font open and both glyphs present. All target
layers are replaced; the source glyph is never modified. The script does not
save the font. The ideal Width=95 adjustment would move the source design to
Width=100 at every smart height, weight, and optical size:

    new95 = (18 * old95 - 5 * old113) / 13

The result is constrained and rounded to whole units. On-curve nodes move
only horizontally. Each off-curve handle moves along one axis, preserving
existing horizontal/vertical tangents at smooth nodes. Diagonal handles at
smooth nodes follow their endpoint horizontally. Other handles use whichever
rounded single-axis move best approximates the ideal result. Existing locked
coordinates stay exactly as in the source, even if already fractional.
Anchors and advance widths use the rounded ideal result. A newly added layer
uses the rounded original Width=95 sample as its reference geometry.
Interpolation error is reported rather than rejected; layer read-back and
movement constraints are still checked strictly.

Each pair must agree on EVERY other font axis. Height is the glyph's one
local smart axis, not a font axis. Missing counterparts are sampled from the
ORIGINAL combined font-axis/smart-height interpolation, using Glyphs' native
VarLibModel. This accounts for sparse intermediates affecting other masters.
Missing Width=95 height layers are added where necessary.
For the original Somerville source this updates nine layers and adds one:
Agate Black SemiCondensed at smart height 30. Source Width=113 is copied exactly.

Requires Glyphs' native VarLibModel class. Reads legacy pole mappings and
one-element smart coordinates as well as Glyphs 4 coordinate dictionaries.
Unrecognized or ambiguous setups,
incompatible paths, components, and unsupported font-width locations abort
before edits. All interpolation and layer creation are prepared and checked
first. Read-back verification follows the edits; failure restores all old
target layers. The operation is one glyph undo group. Layer
copies are positioned through the unrounded native API, then installed by ID;
the font grid is not changed. Target glyph identity, metadata, and smart-axis
IDs are retained; copied layer coordinates are remapped to the target axes.

Every run starts from the unmodified source, so rerunning replaces the target
without compounding the adjustment. A full copy of the previous target is
retained for the current session via target.tempDataForKey_(BACKUP_KEY).
It is not saved to disk.
For a read-only report from the Macro window:

    report = recenter(Glyphs.font, dry_run=True)
"""

from datetime import datetime
from itertools import product
import math
import uuid


GLYPH_NAME = "_smart.circle"
SOURCE_GLYPH_NAME = "_smart.circle.uncentered"
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


def nearest_unit(number):
    """Round half units away from zero, consistently on either side of zero."""
    return math.floor(number + 0.5) if number >= 0 else math.ceil(number - 0.5)


def rounded_geometry(data):
    return {"topology": data["topology"],
            "points": tuple(tuple(nearest_unit(v) for v in p) for p in data["points"]),
            "anchors": {name: tuple(nearest_unit(v) for v in p)
                        for name, p in data["anchors"].items()},
            "width": nearest_unit(data["width"])}


def is_handle(kind):
    return str(kind).lower() in ("offcurve", "o", "65")


def constrained_geometry(baseline, ideal):
    """Project onto allowed moves while keeping smooth tangents aligned."""
    blend(baseline, ideal, 0.0)  # Validate correspondence first.
    projected = []
    offset = 0
    for closed, nodes in baseline["topology"]:
        count = len(nodes)
        original = baseline["points"][offset:offset + count]
        desired = ideal["points"][offset:offset + count]
        points = [(nearest_unit(p[0]), old[1]) if not is_handle(kind) else None
                  for (kind, smooth), old, p in zip(nodes, original, desired)]
        for index, ((kind, smooth), old, wanted) in enumerate(zip(nodes, original, desired)):
            if not is_handle(kind):
                continue
            previous = (index - 1) % count if index or closed else None
            following = (index + 1) % count if index + 1 < count or closed else None
            endpoint = next((i for i in (previous, following)
                             if i is not None and not is_handle(nodes[i][0])), None)
            if endpoint is None:
                raise ValueError("An off-curve handle has no adjacent on-curve endpoint.")
            horizontal = (nearest_unit(wanted[0]), old[1])
            vertical = (old[0], nearest_unit(wanted[1]))
            if nodes[endpoint][1]:
                anchor, moved = original[endpoint], points[endpoint]
                if close(old[1], anchor[1]):
                    # A horizontal tangent cannot change its handle's Y.
                    point = horizontal
                elif close(old[0], anchor[0]):
                    # A vertical tangent must follow its endpoint's X first.
                    point = vertical if close(moved[0], old[0]) else (moved[0], old[1])
                else:
                    point = (nearest_unit(old[0] + moved[0] - anchor[0]), old[1])
            else:
                def error(point):
                    return (point[0] - wanted[0]) ** 2 + (point[1] - wanted[1]) ** 2
                point = min((horizontal, vertical), key=error)
            points[index] = point
        projected.extend(points)
        offset += count
    result = rounded_geometry(ideal)
    result["points"] = tuple(projected)
    assert_movement_constraints(result, baseline)
    return result


def assert_movement_constraints(actual, baseline):
    for (kind, smooth), point, old in zip(
            (node for closed, nodes in baseline["topology"] for node in nodes),
            actual["points"], baseline["points"]):
        dx, dy = point[0] - old[0], point[1] - old[1]
        if (not is_handle(kind) and not close(dy, 0.0)) or (
                is_handle(kind) and not close(dx, 0.0) and not close(dy, 0.0)):
            raise ValueError("A node or handle moved along a forbidden axis.")
        for coordinate, before in zip(point, old):
            if not close(coordinate, before) and not close(coordinate, nearest_unit(coordinate)):
                raise ValueError("A moved coordinate was not rounded to a whole unit.")
    if any(not close(v, nearest_unit(v)) for p in actual["anchors"].values() for v in p):
        raise ValueError("An anchor was not rounded to a whole unit.")
    if not close(actual["width"], nearest_unit(actual["width"])):
        raise ValueError("The advance width was not rounded to a whole unit.")


def geometry_error(actual, expected, label):
    if (actual["topology"] != expected["topology"]
            or set(actual["anchors"]) != set(expected["anchors"])):
        raise ValueError("Structure changed: %s." % label)
    error = max(abs(a - b) for a, b in zip(numbers(actual), numbers(expected)))
    if not math.isfinite(error):
        raise ValueError("Non-finite interpolation error: %s." % label)
    return error


def assert_geometry(actual, expected, label):
    error = geometry_error(actual, expected, label)
    if error > EPSILON:
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
    """Measure approximation error across design-space cells; allow finite error."""
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
        maximum_error = max(maximum_error, geometry_error(
            changed.at(new_location), original.at(old_location), "Width 100 reconstruction"))
        old_location[original.width_index] = FIXED_WIDTH
        maximum_error = max(maximum_error, geometry_error(
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
            ideal = blend(original.at(location), original.at(expanded_location), factor)
            baseline = (group[OLD_WIDTH][height]["data"] if height in group[OLD_WIDTH]
                        else rounded_geometry(original.at(location)))
            data = constrained_geometry(baseline, ideal)
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
                            "baseline": baseline,
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


def remap_smart_axis(layer, source_axis, target_axis):
    """Keep dependent components' existing target smart-axis identifier valid."""
    source_id, target_id = identifier(source_axis), identifier(target_axis)
    if source_id == target_id:
        return

    def remap(mapping):
        result = {str(key): mapping[key] for key in mapping.keys()}
        if source_id in result:
            item = result.pop(source_id)
            if target_id in result and result[target_id] != item:
                raise ValueError("Conflicting source/target smart-axis coordinates.")
            result[target_id] = item
        return result

    for name in ("coordinates", "partSelection", "axisRules"):
        mapping = attribute(layer, name)
        if mapping is not None and hasattr(mapping, "keys"):
            layer.attributes[name] = remap(mapping)
    try:
        mapping = layer.smartComponentPoleMapping
    except (AttributeError, NotImplementedError):
        mapping = None
    if mapping is not None and source_id in mapping.keys():
        layer.smartComponentPoleMapping = remap(mapping)


def recenter(font, dry_run=False, model_factory=native_model):
    if font is None:
        raise ValueError("Open the intended Somerville font first.")
    glyph = font.glyphs[GLYPH_NAME]
    if glyph is None:
        raise ValueError("The open font has no %s glyph." % GLYPH_NAME)
    source = font.glyphs[SOURCE_GLYPH_NAME]
    if source is None:
        raise ValueError("The open font has no %s glyph." % SOURCE_GLYPH_NAME)
    if source is glyph:
        raise ValueError("Source and target must be different glyphs.")
    source_axis, unused_source_modern = smart_axis(source)
    target_axis, unused_target_modern = smart_axis(glyph)
    groups, changes, error, original = prepare(font, source, model_factory)

    # Rebuild ALL target layers from the source, including unchanged expanded
    # layers and any ordinary backup layers. Old target-only layers are removed.
    changed_by_id = {str(change["layer"].layerId): change for change in changes
                     if not change["added"]}
    replacements = []
    for source_layer in source.layers:
        change = changed_by_id.get(str(source_layer.layerId))
        layer = change["layer"] if change else source_layer.copy()
        layer.layerId = str(source_layer.layerId)
        layer.parent = None
        replacements.append(layer)
    replacements.extend(change["layer"] for change in changes if change["added"])
    for layer in replacements:
        remap_smart_axis(layer, source_axis, target_axis)
    replacement_ids = {str(layer.layerId) for layer in replacements}
    if len(replacement_ids) != len(replacements):
        raise ValueError("Source layers have duplicate identifiers.")
    report = {
        "source": SOURCE_GLYPH_NAME,
        "target": GLYPH_NAME,
        "updated": sum(not change["added"] for change in changes),
        "added": sum(change["added"] for change in changes),
        "unchanged_expanded": sum(len(group[FIXED_WIDTH]) for group in groups.values()),
        "maximum_error": error,
        "approximate": True,
        "dry_run": dry_run,
        "target_layers": len(replacements),
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
        assert_movement_constraints(geometry(change["layer"]), change["baseline"])

    # Keep EVERY original target layer for exact rollback, regardless of shape.
    originals = list(glyph.layers)
    original_ids = {str(layer.layerId) for layer in originals}
    previous_marker = glyph.userData[MARKER_KEY]
    backup = glyph.copy()
    # GSGlyph.tempData is a native selector in Glyphs 4, not a Python dict proxy.
    # Store the backup before edits, so a storage error cannot change the font.
    glyph.setTempData_forKey_(backup, BACKUP_KEY)
    font.disableUpdateInterface()
    undo_open = False
    try:
        glyph.beginUndo()
        undo_open = True
        for layer in replacements:
            # append() assigns a fresh ID in Glyphs 4; use source layer IDs.
            glyph.layers[str(layer.layerId)] = layer
        for layer in originals:
            if str(layer.layerId) not in replacement_ids:
                del glyph.layers[str(layer.layerId)]
        for change in changes:
            layer = glyph.layers[str(change["layer"].layerId)]
            assert_geometry(geometry(layer), change["data"], "Written layer %r" % layer.name)
            assert_movement_constraints(geometry(layer), change["baseline"])
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
                                     "source": SOURCE_GLYPH_NAME,
                                     "from": OLD_WIDTH, "to": NEW_WIDTH,
                                     "fixed": FIXED_WIDTH}
    except Exception:
        for layer in list(glyph.layers):
            if str(layer.layerId) not in original_ids:
                del glyph.layers[str(layer.layerId)]
        for layer in originals:
            glyph.layers[str(layer.layerId)] = layer
        if previous_marker is not None:
            glyph.userData[MARKER_KEY] = previous_marker
        elif glyph.userData[MARKER_KEY]:
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
