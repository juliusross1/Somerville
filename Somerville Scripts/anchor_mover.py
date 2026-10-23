# MenuTitle: anchor mover
# -*- coding: utf-8 -*-
"""Move named anchors horizontally by 10 units on every layer of a glyph."""

import traceback

import vanilla
from Foundation import NSMakePoint
from GlyphsApp import Glyphs, UPDATEINTERFACE


# The repeated math.br in the requested order is interpreted as math.bl.
ANCHOR_ORDER = ("math.ta", "math.tr", "math.br", "math.tl", "math.bl", "math.ic")
STEP = 10


class AnchorMover:
    def __init__(self):
        self.signature = None
        self.actions = {}
        self.w = vanilla.FloatingWindow((330, 330), "anchor mover")
        self.w.glyphName = vanilla.TextBox((12, 12, -12, 20), "")
        self.w.hint = vanilla.TextBox(
            (12, 36, -12, 20), "Move by 10 units on all layers.", sizeStyle="small"
        )
        self.w.bind("close", self.close)
        self.refresh()
        Glyphs.addCallback(self.refresh, UPDATEINTERFACE)
        self.w.open()

    def selection(self):
        font = Glyphs.font
        if font is None or not font.selectedLayers:
            return None, None
        return font, font.selectedLayers[0].parent

    def refresh(self, sender=None):
        font, glyph = self.selection()
        names = {
            anchor.name
            for layer in glyph.layers
            for anchor in layer.anchors
        } if glyph is not None else set()
        ordered = [name for name in ANCHOR_ORDER if name in names]
        ordered.extend(sorted(names.difference(ANCHOR_ORDER)))
        signature = (font, glyph, tuple(ordered))
        if signature == self.signature:
            return
        self.signature = signature
        self.w.glyphName.set(glyph.name if glyph is not None else "Select a glyph.")
        self.actions = {}
        if hasattr(self.w, "anchors"):
            del self.w.anchors
        rows = vanilla.Group((0, 0, 300, max(30, len(ordered) * 30)))
        for index, name in enumerate(ordered):
            y = index * 30
            setattr(rows, "label%d" % index, vanilla.TextBox((0, y + 3, 190, 20), name))
            for direction, label, x, delta in (
                ("left", "←", 200, -STEP),
                ("right", "→", 245, STEP),
            ):
                button = vanilla.Button((x, y, 40, 24), label, callback=self.move)
                setattr(rows, "%s%d" % (direction, index), button)
                self.actions[id(button)] = (name, delta)
        if glyph is not None and not ordered:
            rows.empty = vanilla.TextBox((0, 3, 290, 20), "No anchors on this glyph.")
        self.anchor_group = rows
        self.w.anchors = vanilla.ScrollView(
            (12, 64, -12, -12), rows.getNSView(), hasHorizontalScroller=False
        )

    def move(self, sender):
        action = self.actions.get(id(sender))
        font, glyph = self.selection()
        if action is None or glyph is None:
            return
        # An old button must never act on a newly selected glyph.
        if (font, glyph) != self.signature[:2]:
            self.refresh()
            return
        name, delta = action
        font.disableUpdateInterface()
        try:
            glyph.beginUndo()
            try:
                for layer in glyph.layers:
                    anchor = layer.anchors[name]
                    if anchor is not None:
                        anchor.position = NSMakePoint(
                            anchor.position.x + delta, anchor.position.y
                        )
            finally:
                glyph.endUndo()
        except Exception:
            Glyphs.showMacroWindow()
            traceback.print_exc()
        finally:
            font.enableUpdateInterface()
            Glyphs.redraw()

    def close(self, sender):
        Glyphs.removeCallback(self.refresh)


if __name__ == "__main__":
    # A closed Vanilla window can leave its script instance alive.
    previous_window = getattr(globals().get("anchor_mover"), "w", None)
    if getattr(previous_window, "_window", None) is not None:
        previous_window.close()
    anchor_mover = AnchorMover()
