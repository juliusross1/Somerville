#MenuTitle: Add Node at Y on All Layers
# -*- coding: utf-8 -*-

"""Split one corresponding path segment at a specified Y on every glyph layer.

Select exactly two consecutive on-curve nodes belonging to one path in the
currently edited glyph, then run the script and enter a Y coordinate. The
selected segment is identified by its path and node indices and the same
segment is located on every layer, including master, intermediate, and other
special layers.

Before changing anything, the script validates every layer. Each corresponding
segment must have compatible structure and must cross the requested Y at one
and only one point strictly inside the segment. Lines and cubic curves are
supported; cubic curves are divided with de Casteljau's construction so their
shape is preserved. Wrapped segments across the stored start/end of a closed
path are rejected. If any validation fails, no layer is changed and the full
reason is printed in the Macro window.
"""

import math

import vanilla
from Foundation import NSPoint
from GlyphsApp import Glyphs, GSNode, LINE, CURVE, OFFCURVE, Message


EPSILON = 0.000001


def node_type(node):
    try:
        return node.type
    except Exception:
        return None


def is_oncurve(node):
    return node_type(node) != OFFCURVE


def node_point(node):
    return (float(node.position.x), float(node.position.y))


def interpolate(first, second, t):
    return (
        first[0] + (second[0] - first[0]) * t,
        first[1] + (second[1] - first[1]) * t,
    )


def polynomial_value(coefficients, t):
    a, b, c, d = coefficients
    return ((a * t + b) * t + c) * t + d


def unique_values(values, tolerance=EPSILON):
    result = []
    for value in sorted(values):
        if not result or abs(value - result[-1]) > tolerance:
            result.append(value)
    return result


def derivative_roots(a, b, c):
    """Roots in (0, 1) of 3*a*t^2 + 2*b*t + c."""
    if abs(a) <= EPSILON:
        if abs(b) <= EPSILON:
            return []
        root = -c / (2.0 * b)
        return [root] if EPSILON < root < 1.0 - EPSILON else []
    discriminant = 4.0 * b * b - 12.0 * a * c
    if discriminant < -EPSILON:
        return []
    discriminant = max(0.0, discriminant)
    root_discriminant = math.sqrt(discriminant)
    roots = [
        (-2.0 * b - root_discriminant) / (6.0 * a),
        (-2.0 * b + root_discriminant) / (6.0 * a),
    ]
    return unique_values(
        root for root in roots if EPSILON < root < 1.0 - EPSILON
    )


def cubic_roots_in_unit_interval(coefficients):
    """Find all roots strictly inside (0, 1), including tangent roots."""
    a, b, c, d = coefficients
    boundaries = [0.0] + derivative_roots(a, b, c) + [1.0]
    roots = []
    for boundary in boundaries[1:-1]:
        if abs(polynomial_value(coefficients, boundary)) <= EPSILON:
            roots.append(boundary)
    for left, right in zip(boundaries, boundaries[1:]):
        left_value = polynomial_value(coefficients, left)
        right_value = polynomial_value(coefficients, right)
        if abs(left_value) <= EPSILON and EPSILON < left < 1.0 - EPSILON:
            roots.append(left)
        if abs(right_value) <= EPSILON and EPSILON < right < 1.0 - EPSILON:
            roots.append(right)
        if left_value * right_value >= 0.0:
            continue
        low, high = left, right
        low_value = left_value
        for unused in range(70):
            middle = (low + high) * 0.5
            middle_value = polynomial_value(coefficients, middle)
            if abs(middle_value) <= EPSILON:
                low = high = middle
                break
            if low_value * middle_value <= 0.0:
                high = middle
            else:
                low = middle
                low_value = middle_value
        root = (low + high) * 0.5
        if EPSILON < root < 1.0 - EPSILON:
            roots.append(root)
    return unique_values(roots)


def segment_data(path, start_index, end_index):
    nodes = list(path.nodes)
    if start_index >= end_index:
        raise ValueError("the selected segment wraps across the path's stored boundary")
    between = nodes[start_index + 1:end_index]
    if not is_oncurve(nodes[start_index]) or not is_oncurve(nodes[end_index]):
        raise ValueError("the segment endpoints are not both on-curve nodes")
    if any(is_oncurve(node) for node in between):
        raise ValueError("the selected nodes are not consecutive on-curve nodes")
    if len(between) == 0:
        return {"kind": "line", "points": [node_point(nodes[start_index]), node_point(nodes[end_index])]}
    if len(between) == 2 and all(node_type(node) == OFFCURVE for node in between):
        return {
            "kind": "curve",
            "points": [
                node_point(nodes[start_index]),
                node_point(between[0]),
                node_point(between[1]),
                node_point(nodes[end_index]),
            ],
        }
    raise ValueError("the segment is neither a line nor a cubic curve")


def intersection_parameter(data, wanted_y):
    points = data["points"]
    if data["kind"] == "line":
        difference = points[1][1] - points[0][1]
        if abs(difference) <= EPSILON:
            raise ValueError("the segment is horizontal at or away from the requested Y")
        roots = [(wanted_y - points[0][1]) / difference]
    else:
        y0, y1, y2, y3 = [point[1] for point in points]
        coefficients = (
            -y0 + 3.0 * y1 - 3.0 * y2 + y3,
            3.0 * y0 - 6.0 * y1 + 3.0 * y2,
            -3.0 * y0 + 3.0 * y1,
            y0 - wanted_y,
        )
        roots = cubic_roots_in_unit_interval(coefficients)
    roots = [root for root in roots if EPSILON < root < 1.0 - EPSILON]
    if len(roots) != 1:
        raise ValueError(
            "the segment has %i interior intersections with Y=%g (exactly one is required)"
            % (len(roots), wanted_y)
        )
    return roots[0]


def new_node(point, node_kind):
    node = GSNode(NSPoint(point[0], point[1]), type=node_kind)
    return node


def split_path(path, start_index, end_index, data, t):
    points = data["points"]
    if data["kind"] == "line":
        point = interpolate(points[0], points[1], t)
        path.nodes.insert(end_index, new_node(point, LINE))
        return point

    p0, p1, p2, p3 = points
    q0 = interpolate(p0, p1, t)
    q1 = interpolate(p1, p2, t)
    q2 = interpolate(p2, p3, t)
    r0 = interpolate(q0, q1, t)
    r1 = interpolate(q1, q2, t)
    split = interpolate(r0, r1, t)

    path.nodes[start_index + 1].position = NSPoint(q0[0], q0[1])
    path.nodes[start_index + 2].position = NSPoint(r0[0], r0[1])
    # Insert in reverse order at the same index to produce S, R1, Q2, P3.
    path.nodes.insert(end_index, new_node(q2, OFFCURVE))
    path.nodes.insert(end_index, new_node(r1, OFFCURVE))
    path.nodes.insert(end_index, new_node(split, CURVE))
    return split


def layer_label(layer):
    try:
        return str(layer.name or layer.layerId)
    except Exception:
        return "unnamed layer"


def selected_segment(font):
    selected_layers = list(font.selectedLayers or [])
    if not selected_layers:
        raise ValueError("no edited layer is selected")
    layer = selected_layers[0]
    selected = []
    for path_index, path in enumerate(layer.paths):
        for node_index, node in enumerate(path.nodes):
            try:
                is_selected = bool(node.selected)
            except Exception:
                try:
                    is_selected = node in layer.selection
                except Exception:
                    is_selected = False
            if is_selected:
                selected.append((path_index, node_index, node))
    if len(selected) != 2:
        raise ValueError("select exactly two nodes; %i nodes are selected" % len(selected))
    if selected[0][0] != selected[1][0]:
        raise ValueError("the two selected nodes belong to different paths")
    path_index = selected[0][0]
    first_index, second_index = sorted((selected[0][1], selected[1][1]))
    reference_path = layer.paths[path_index]
    reference_data = segment_data(reference_path, first_index, second_index)
    return (
        layer.parent,
        path_index,
        first_index,
        second_index,
        len(reference_path.nodes),
        bool(reference_path.closed),
        reference_data["kind"],
    )


class AddNodeAtYWindow(object):
    def __init__(self):
        self.w = vanilla.FloatingWindow((330, 132), "Add Node at Y on All Layers")
        self.w.label = vanilla.TextBox((15, 18, 105, 20), "Y coordinate:")
        self.w.yValue = vanilla.EditText((120, 15, -15, 24), "0")
        self.w.note = vanilla.TextBox(
            (15, 50, -15, 34),
            "Select two consecutive on-curve nodes. Every layer is validated before any change.",
        )
        self.w.cancel = vanilla.Button((-190, -34, 80, 22), "Cancel", callback=self.cancel)
        self.w.run = vanilla.Button((-100, -34, 85, 22), "Add Node", callback=self.run)
        self.w.setDefaultButton(self.w.run)
        self.w.open()
        self.w.makeKey()

    def cancel(self, sender):
        self.w.close()

    def run(self, sender):
        font = Glyphs.font
        if font is None:
            Message("No Font Open", "Open a font before running this script.")
            return
        try:
            wanted_y = float(str(self.w.yValue.get()).strip())
        except Exception:
            Message("Invalid Y Coordinate", "Enter a numeric Y coordinate.")
            return

        print("=" * 72)
        print("Add Node at Y on All Layers")
        print("Requested Y: %g" % wanted_y)
        try:
            (
                glyph,
                path_index,
                start_index,
                end_index,
                reference_node_count,
                reference_closed,
                reference_kind,
            ) = selected_segment(font)
        except Exception as error:
            print("ABORTED before validation: %s" % error)
            Message("No Changes Made", str(error))
            return
        print("Glyph: %s" % glyph.name)
        print("Selected segment: path %i, nodes %i to %i" % (path_index, start_index, end_index))

        plans = []
        failures = []
        for layer in glyph.layers:
            label = layer_label(layer)
            try:
                paths = list(layer.paths)
                if path_index >= len(paths):
                    raise ValueError("path index %i does not exist" % path_index)
                path = paths[path_index]
                if len(path.nodes) != reference_node_count:
                    raise ValueError(
                        "the corresponding path has %i nodes instead of %i"
                        % (len(path.nodes), reference_node_count)
                    )
                if bool(path.closed) != reference_closed:
                    raise ValueError("the corresponding path has different open/closed status")
                if end_index >= len(path.nodes):
                    raise ValueError("node index %i does not exist" % end_index)
                data = segment_data(path, start_index, end_index)
                if data["kind"] != reference_kind:
                    raise ValueError(
                        "the corresponding segment is a %s instead of a %s"
                        % (data["kind"], reference_kind)
                    )
                t = intersection_parameter(data, wanted_y)
                plans.append((layer, path, data, t))
                print("  VALID %-30s t=%.8f (%s)" % (label, t, data["kind"]))
            except Exception as error:
                failures.append("%s: %s" % (label, error))
                print("  INVALID %s: %s" % (label, error))

        if failures:
            print("\nABORTED: %i layer(s) failed validation. No changes were made." % len(failures))
            for failure in failures:
                print("  %s" % failure)
            Message(
                "No Changes Made",
                "%i layer(s) could not be handled safely. See the Macro window."
                % len(failures),
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
            for layer, path, data, t in plans:
                point = split_path(path, start_index, end_index, data, t)
                print("  CHANGED %-30s node=(%.3f, %.3f)" % (layer_label(layer), point[0], point[1]))
        finally:
            if undo_started:
                try:
                    glyph.endUndo()
                except Exception:
                    pass
            font.enableUpdateInterface()

        self.w.close()
        Message("Nodes Added", "Added one node at Y=%g to %i layer(s)." % (wanted_y, len(plans)))


AddNodeAtYWindow()
