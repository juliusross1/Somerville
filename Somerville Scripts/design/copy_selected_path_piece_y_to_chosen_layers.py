#MenuTitle: Copy Selected Path Piece Y to Chosen Layers
# -*- coding: utf-8 -*-

"""Copy selected path-piece Y coordinates to checked layers.

Handles between selected segment endpoints are included automatically.
X coordinates remain unchanged. Only checked layers are modified.
"""

import traceback
import vanilla

from GlyphsApp import Glyphs, OFFCURVE, Message
from Foundation import NSPoint


class CopyPieceYWindow:

    def __init__(self):
        self.font = Glyphs.font
        if self.font is None or not self.font.selectedLayers:
            raise ValueError("Select a path piece in Edit View first.")

        source = self.font.selectedLayers[0]
        self.glyph = source.parent

        selected_paths = []
        for path_index, path in enumerate(source.paths):
            indices = {
                index for index, node in enumerate(path.nodes)
                if node.selected
            }
            if indices:
                selected_paths.append((path_index, path, indices))

        if len(selected_paths) != 1:
            raise ValueError(
                "Select nodes or handles belonging to exactly one path."
            )

        self.path_index, source_path, indices = selected_paths[0]
        selected_endpoints = set(indices)

        oncurves = [
            index for index, node in enumerate(source_path.nodes)
            if node.type != OFFCURVE
        ]
        ends = oncurves[1:]
        if source_path.closed and oncurves:
            ends += oncurves[:1]

        # Include handles between selected segment endpoints.
        for start, end in zip(oncurves, ends):
            if start in selected_endpoints and end in selected_endpoints:
                index = (start + 1) % len(source_path.nodes)
                while index != end:
                    indices.add(index)
                    index = (index + 1) % len(source_path.nodes)

        self.y_values = {
            index: float(source_path.nodes[index].position.y)
            for index in indices
        }
        self.signature = (
            bool(source_path.closed),
            tuple(node.type for node in source_path.nodes),
        )

        rows = []
        for layer in self.glyph.layers:
            if layer.layerId == source.layerId:
                continue
            rows.append({
                "apply": True,
                "layer": str(layer.name or layer.layerId),
                "layerId": str(layer.layerId),
            })

        if not rows:
            raise ValueError("This glyph has no other layers.")

        self.w = vanilla.FloatingWindow(
            (580, 420),
            "Copy Path Piece Y",
            minSize=(480, 280),
        )

        self.w.info = vanilla.TextBox(
            (15, 12, -15, 38),
            "Source: %s / %s\nCopy Y for %d nodes/handles on path %d."
            % (
                self.glyph.name,
                source.name or source.layerId,
                len(indices),
                self.path_index + 1,
            ),
        )

        self.w.layers = vanilla.List(
            (15, 58, -15, -60),
            rows,
            columnDescriptions=[
                {
                    "title": "Apply",
                    "key": "apply",
                    "width": 50,
                    "editable": True,
                    "cell": vanilla.CheckBoxListCell(),
                },
                {
                    "title": "Layer",
                    "key": "layer",
                    "editable": False,
                },
            ],
            allowsMultipleSelection=False,
        )

        self.w.allButton = vanilla.Button(
            (15, -40, 65, 24), "All", callback=self.select_all,
        )
        self.w.noneButton = vanilla.Button(
            (85, -40, 65, 24), "None", callback=self.select_none,
        )
        self.w.cancelButton = vanilla.Button(
            (-210, -40, 90, 24), "Cancel", callback=self.cancel,
        )
        self.w.applyButton = vanilla.Button(
            (-110, -40, 95, 24), "Apply", callback=self.apply,
        )

        self.w.open()
        self.w.makeKey()

    def set_checks(self, checked):
        rows = []
        for row in self.w.layers.get():
            row = dict(row)
            row["apply"] = checked
            rows.append(row)
        self.w.layers.set(rows)

    def select_all(self, sender):
        self.set_checks(True)

    def select_none(self, sender):
        self.set_checks(False)

    def cancel(self, sender):
        self.w.close()

    def apply(self, sender):
        selected_rows = [
            row for row in self.w.layers.get()
            if row["apply"]
        ]

        if not selected_rows:
            Message("No Layers Checked", "Check at least one target layer.")
            return

        try:
            self.copy_to_layers(selected_rows)
        except Exception as error:
            Glyphs.showMacroWindow()
            traceback.print_exc()
            Message("Copy Path Piece Y", str(error))
            return

        self.w.close()

    def copy_to_layers(self, rows):
        originals = []
        incompatible = []

        # Validate every checked layer before preparing or applying changes.
        for row in rows:
            layer = self.glyph.layers[row["layerId"]]
            if layer is None:
                raise ValueError(
                    "Layer no longer exists: %s" % row["layer"]
                )

            if self.path_index >= len(layer.paths):
                incompatible.append(row["layer"])
                continue

            path = layer.paths[self.path_index]
            signature = (
                bool(path.closed),
                tuple(node.type for node in path.nodes),
            )
            if signature != self.signature:
                incompatible.append(row["layer"])
                continue

            originals.append(layer)

        if incompatible:
            raise ValueError(
                "Nothing changed. These layers have incompatible paths:\n\n"
                + "\n".join(incompatible)
            )

        replacements = []
        for original in originals:
            copy = original.copy()
            copy.parent = None
            copy.layerId = original.layerId
            path = copy.paths[self.path_index]

            for index, y in self.y_values.items():
                node = path.nodes[index]
                node.setPositionFast_(NSPoint(node.position.x, y))

            path.elementDidChange_(None)
            copy.setNeedUpdateShapes()
            copy.setNeedUpdateMetrics()
            replacements.append(copy)

        undo_open = False
        self.font.disableUpdateInterface()
        try:
            self.glyph.beginUndo()
            undo_open = True
            try:
                for layer in replacements:
                    self.glyph.layers[layer.layerId] = layer
            except Exception:
                for original in originals:
                    self.glyph.layers[original.layerId] = original
                raise
        finally:
            try:
                if undo_open:
                    self.glyph.endUndo()
            finally:
                self.font.enableUpdateInterface()

        print(
            "Copied Y for %d nodes/handles on path %d to %d chosen layers."
            % (
                len(self.y_values),
                self.path_index + 1,
                len(replacements),
            )
        )


try:
    copyPieceYWindow = CopyPieceYWindow()
except ValueError as error:
    Message("Copy Path Piece Y", str(error))
