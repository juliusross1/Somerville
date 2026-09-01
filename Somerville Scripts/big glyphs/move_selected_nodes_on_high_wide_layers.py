#MenuTitle: Move Selected Nodes on High/Wide Layers
# -*- coding: utf-8 -*-

import vanilla
from GlyphsApp import Glyphs


SCRIPT_VERSION = "2026-06-23 14:09 CDT move-selected-nodes-high-wide"
TARGET_LAYER_NAME_PARTS = ("High", "Wide")


def print_warning(message):
    print("WARNING: %s" % message)


def safe_call(value, default=None):
    if callable(value):
        try:
            return value()
        except Exception:
            return default
    return value


def layer_name(layer):
    return str(safe_call(getattr(layer, "name", ""), "") or "")


def path_records(layer):
    records = []
    try:
        shapes = list(layer.shapes)
    except Exception:
        shapes = []

    for shape_index, shape in enumerate(shapes):
        try:
            nodes = list(shape.nodes)
        except Exception:
            continue
        records.append(dict(shape_index=shape_index, path_index=len(records), path=shape, nodes=nodes))

    if records:
        return records

    try:
        paths = list(layer.paths)
    except Exception:
        paths = []

    for path_index, path in enumerate(paths):
        try:
            nodes = list(path.nodes)
        except Exception:
            continue
        records.append(dict(shape_index=None, path_index=path_index, path=path, nodes=nodes))
    return records


def node_is_selected(layer, node):
    selected = safe_call(getattr(node, "selected", False), False)
    if selected:
        return True

    try:
        selection = list(layer.selection or [])
    except Exception:
        selection = []
    return node in selection


def selected_node_addresses(layer):
    addresses = []
    for record in path_records(layer):
        for node_index, node in enumerate(record["nodes"]):
            if node_is_selected(layer, node):
                addresses.append(dict(
                    shape_index=record["shape_index"],
                    path_index=record["path_index"],
                    node_index=node_index,
                ))
    return addresses


def node_for_address(layer, address):
    shape_index = address["shape_index"]
    node_index = address["node_index"]

    if shape_index is not None:
        try:
            shape = list(layer.shapes)[shape_index]
            nodes = list(shape.nodes)
            return nodes[node_index]
        except Exception:
            pass

    path_index = address["path_index"]
    records = path_records(layer)
    if path_index >= len(records):
        return None
    nodes = records[path_index]["nodes"]
    if node_index >= len(nodes):
        return None
    return nodes[node_index]


def move_node(node, dx, dy):
    node.x = node.x + dx
    node.y = node.y + dy


def target_layers_for_glyph(glyph, current_layer):
    layers = []
    for layer in glyph.layers:
        if layer is current_layer:
            continue
        name = layer_name(layer)
        if any(part in name for part in TARGET_LAYER_NAME_PARTS):
            layers.append(layer)
    return layers


def parse_float(text, label):
    try:
        return float(str(text).strip())
    except Exception:
        raise ValueError("%s must be a number." % label)


def call_method(obj, method_name):
    method = getattr(obj, method_name, None)
    if callable(method):
        try:
            method()
        except Exception:
            pass


def move_selected_nodes(dx, dy):
    font = Glyphs.font
    if font is None:
        print_warning("No font open.")
        return

    selected_layers = list(font.selectedLayers or [])
    if not selected_layers:
        print_warning("No current layer selected.")
        return

    current_layer = selected_layers[0]
    glyph = current_layer.parent
    if glyph is None:
        print_warning("The current layer has no parent glyph.")
        return

    addresses = selected_node_addresses(current_layer)
    if not addresses:
        print_warning("%s: no selected nodes in the current layer." % glyph.name)
        return

    target_layers = target_layers_for_glyph(glyph, current_layer)
    moved_in_current = 0
    moved_in_target_layers = 0
    skipped_nodes = 0

    font.disableUpdateInterface()
    call_method(glyph, "beginUndo")
    try:
        for address in addresses:
            node = node_for_address(current_layer, address)
            if node is None:
                skipped_nodes += 1
                continue
            move_node(node, dx, dy)
            moved_in_current += 1

        for layer in target_layers:
            layer_moved = 0
            for address in addresses:
                node = node_for_address(layer, address)
                if node is None:
                    skipped_nodes += 1
                    continue
                move_node(node, dx, dy)
                moved_in_target_layers += 1
                layer_moved += 1
            print("%s: moved %i node(s)" % (layer_name(layer), layer_moved))
    finally:
        call_method(glyph, "endUndo")
        font.enableUpdateInterface()

    print("")
    print("%s: moved %i selected node(s) in current layer %s" % (
        glyph.name,
        moved_in_current,
        layer_name(current_layer) or current_layer.layerId,
    ))
    print("Moved %i matching node(s) across %i High/Wide layer(s)." % (
        moved_in_target_layers,
        len(target_layers),
    ))
    if skipped_nodes:
        print_warning("Skipped %i missing matching node(s)." % skipped_nodes)


class MoveNodesWindow(object):
    def __init__(self):
        self.w = vanilla.FloatingWindow((300, 128), "Move Nodes")
        self.w.xLabel = vanilla.TextBox((15, 18, 50, 18), "x")
        self.w.xValue = vanilla.EditText((65, 14, 80, 24), "0")
        self.w.yLabel = vanilla.TextBox((165, 18, 50, 18), "y")
        self.w.yValue = vanilla.EditText((215, 14, 70, 24), "0")
        self.w.moveButton = vanilla.Button((15, 58, -15, 28), "Move selected nodes", callback=self.move_callback)
        self.w.closeButton = vanilla.Button((15, 94, -15, 24), "Close", callback=self.close_callback)
        self.w.open()
        self.w.makeKey()
        print("UI opened.")

    def move_callback(self, sender):
        Glyphs.clearLog()
        Glyphs.showMacroWindow()
        print("Move Selected Nodes on High/Wide Layers")
        print("Script version: %s" % SCRIPT_VERSION)
        print("")

        try:
            dx = parse_float(self.w.xValue.get(), "x")
            dy = parse_float(self.w.yValue.get(), "y")
        except Exception as error:
            print_warning(error)
            return

        print("Move by x=%s, y=%s" % (dx, dy))
        move_selected_nodes(dx, dy)

    def close_callback(self, sender):
        self.w.close()


try:
    Glyphs.clearLog()
    Glyphs.showMacroWindow()
    print("Move Selected Nodes on High/Wide Layers")
    print("Script version: %s" % SCRIPT_VERSION)
    print("")
    MOVE_NODES_WINDOW = MoveNodesWindow()
except Exception as error:
    import traceback

    Glyphs.clearLog()
    Glyphs.showMacroWindow()
    print("Move Selected Nodes on High/Wide Layers")
    print("")
    print_warning("Could not open UI: %s" % error)
    print_warning(traceback.format_exc())
