#MenuTitle: Delete Selected Nodes on All Layers
# -*- coding: utf-8 -*-

"""
Delete matching nodes on every layer of the current glyph.

Select one or more nodes in the current layer, then run the script. The script
records each selected node by path/component-shape position and node index, then
visits every layer in the glyph and deletes the node at the same address.

This is useful when the same point needs to be removed from corresponding
outlines across masters, brace layers, bracket layers, and other layers. It
does not compare coordinates or node types; it assumes the layer structures
match closely enough that the selected node indexes identify the same intended
points everywhere.

If a matching path or node index is missing on a layer, that node is skipped and
reported in the Macro panel. All deletions are grouped into one glyph undo
operation.
"""

from GlyphsApp import Glyphs


SCRIPT_VERSION = "2026-06-24 10:05 CDT delete-selected-nodes-all-layers"


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


def layer_label(layer):
    return layer_name(layer) or str(safe_call(getattr(layer, "layerId", ""), "") or "<unnamed layer>")


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
    seen = set()
    for record in path_records(layer):
        for node_index, node in enumerate(record["nodes"]):
            if not node_is_selected(layer, node):
                continue
            key = (record["shape_index"], record["path_index"], node_index)
            if key in seen:
                continue
            seen.add(key)
            addresses.append(dict(
                shape_index=record["shape_index"],
                path_index=record["path_index"],
                node_index=node_index,
            ))
    return addresses


def path_for_address(layer, address):
    shape_index = address["shape_index"]

    if shape_index is not None:
        try:
            shape = list(layer.shapes)[shape_index]
            list(shape.nodes)
            return shape
        except Exception:
            pass

    path_index = address["path_index"]
    records = path_records(layer)
    if path_index >= len(records):
        return None
    return records[path_index]["path"]


def delete_node_from_path(path, node_index):
    try:
        nodes = list(path.nodes)
    except Exception:
        return False
    if node_index >= len(nodes):
        return False

    node = nodes[node_index]

    delete_method = getattr(node, "delete", None)
    if callable(delete_method):
        try:
            delete_method()
            return True
        except Exception:
            pass

    for method_name in ("removeNodeCheckKeepShape_", "removeNode_", "removeObject_"):
        method = getattr(path, method_name, None)
        if callable(method):
            try:
                method(node)
                return True
            except Exception:
                pass

    for method_name in ("removeNode_", "removeObject_", "remove_"):
        method = getattr(path.nodes, method_name, None)
        if callable(method):
            try:
                method(node)
                return True
            except Exception:
                pass

    try:
        del path.nodes[node_index]
        return True
    except Exception:
        pass

    try:
        path.nodes.remove(node)
        return True
    except Exception:
        return False


def delete_addresses_from_layer(layer, addresses):
    grouped = {}
    for address in addresses:
        key = (address["shape_index"], address["path_index"])
        grouped.setdefault(key, []).append(address["node_index"])

    deleted = 0
    skipped = 0
    for key in sorted(grouped.keys(), reverse=True):
        address = dict(shape_index=key[0], path_index=key[1], node_index=0)
        path = path_for_address(layer, address)
        if path is None:
            skipped += len(grouped[key])
            continue

        for node_index in sorted(set(grouped[key]), reverse=True):
            if delete_node_from_path(path, node_index):
                deleted += 1
            else:
                skipped += 1

    return deleted, skipped


def call_method(obj, method_name):
    method = getattr(obj, method_name, None)
    if callable(method):
        try:
            method()
        except Exception:
            pass


def delete_selected_nodes_on_all_layers():
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

    total_deleted = 0
    total_skipped = 0
    layers_changed = 0

    font.disableUpdateInterface()
    call_method(glyph, "beginUndo")
    try:
        for layer in glyph.layers:
            deleted, skipped = delete_addresses_from_layer(layer, addresses)
            total_deleted += deleted
            total_skipped += skipped
            if deleted:
                layers_changed += 1
            print("%s: deleted %i node(s)" % (layer_label(layer), deleted))
    finally:
        call_method(glyph, "endUndo")
        font.enableUpdateInterface()

    print("")
    print("%s: deleted %i matching node(s) across %i layer(s)." % (
        glyph.name,
        total_deleted,
        layers_changed,
    ))
    if total_skipped:
        print_warning("Skipped %i missing matching node(s)." % total_skipped)


try:
    Glyphs.clearLog()
    Glyphs.showMacroWindow()
    print("Delete Selected Nodes on All Layers")
    print("Script version: %s" % SCRIPT_VERSION)
    print("")
    delete_selected_nodes_on_all_layers()
except Exception as error:
    import traceback

    Glyphs.clearLog()
    Glyphs.showMacroWindow()
    print("Delete Selected Nodes on All Layers")
    print("")
    print_warning("Could not delete selected nodes: %s" % error)
    print_warning(traceback.format_exc())
