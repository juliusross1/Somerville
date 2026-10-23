# MenuTitle: Steal Math Anchors
# -*- coding: utf-8 -*-
"""Copy chosen math.* anchors between selected glyphs, across all layers.

Master layers match by ID. Other layers match by associated master and
coordinates (including smart layers), axis rules, or (for backups) layer name.
Optional fallback uses the source's associated master when no match exists.
Background layers are not included. math.tr and math.br retain their horizontal
offset from the right sidebearing line (layer width). Other anchors retain
their absolute coordinates. All y coordinates are copied without scaling.
"""

import traceback

import vanilla
from Foundation import NSMakePoint
from GlyphsApp import Glyphs, Message


ANCHOR_ORDER = ("math.ta", "math.tr", "math.br", "math.tl", "math.bl", "math.ic")
RIGHT_ANCHORS = frozenset(("math.tr", "math.br"))


def frozen(value):
    """Make Foundation dictionaries and arrays comparable by content."""
    if value is None:
        return None
    if hasattr(value, "keys"):
        return tuple(sorted((str(key), frozen(value[key])) for key in value.keys()))
    if isinstance(value, (str, int, float, bool)):
        return value
    return tuple(frozen(item) for item in value)


def layer_key(layer):
    if layer.isMasterLayer:
        return ("master", layer.layerId)
    attributes = layer.attributes
    coordinates = attributes["coordinates"]
    rules = attributes["axisRules"]
    if coordinates is not None or rules is not None:
        return ("special", layer.associatedMasterId, frozen(coordinates),
                frozen(rules))
    return ("named", layer.associatedMasterId, layer.name)


def copy_plan(source, target, names, overwrite, fallback):
    by_key = {}
    masters = {}
    for layer in source.layers:
        by_key.setdefault(layer_key(layer), []).append(layer)
        if layer.isMasterLayer:
            masters[layer.layerId] = layer
    changes, report = [], []
    for target_layer in target.layers:
        matches = by_key.get(layer_key(target_layer), [])
        if len(matches) > 1:
            report.append("%s: skipped ambiguous source layers" % target_layer.name)
            continue
        origin = matches[0] if matches else None
        if origin is None and fallback:
            origin = masters.get(target_layer.associatedMasterId)
            if origin is not None:
                report.append("%s: using source master %s" % (target_layer.name, origin.name))
        if origin is None:
            report.append("%s: skipped; no matching source layer" % target_layer.name)
            continue
        for name in names:
            anchor = origin.anchors[name]
            if anchor is None:
                report.append("%s: source has no %s" % (target_layer.name, name))
                continue
            if target_layer.anchors[name] is not None and not overwrite:
                continue
            copied_anchor = anchor.copy()
            if name in RIGHT_ANCHORS:
                copied_anchor.position = NSMakePoint(
                    anchor.position.x + target_layer.width - origin.width,
                    anchor.position.y,
                )
            changes.append((target_layer, copied_anchor))
    return changes, report


class StealMathAnchors:
    def __init__(self):
        self.font = None
        self.glyphs = []
        self.checks = []
        self.w = vanilla.FloatingWindow((420, 470), "Steal Math Anchors")
        self.w.sourceLabel = vanilla.TextBox((12, 15, 65, 20), "Source:")
        self.w.source = vanilla.PopUpButton((80, 12, -12, 24), [], callback=self.source_changed)
        self.w.targetLabel = vanilla.TextBox((12, 47, 65, 20), "Target:")
        self.w.target = vanilla.PopUpButton((80, 44, -12, 24), [], callback=self.update_button)
        self.w.refresh = vanilla.Button((12, 80, -12, 24), "Refresh from selected glyphs", callback=self.refresh)
        self.w.anchorsLabel = vanilla.TextBox((12, 116, -12, 20), "Math anchors to copy:")
        self.w.overwrite = vanilla.CheckBox((12, 310, -12, 22), "Replace chosen anchors already in target", value=True)
        self.w.fallback = vanilla.CheckBox((12, 338, -12, 22), "Use source master for unmatched target layers", value=True)
        self.w.note = vanilla.TextBox((12, 368, -12, 36), "math.tr / math.br keep their offset from the RSB line.\nOther chosen anchors keep their source coordinates.", sizeStyle="small")
        self.w.status = vanilla.TextBox((12, 410, 275, 44), "", sizeStyle="small")
        self.w.run = vanilla.Button((-112, 420, 100, 28), "Steal", callback=self.run)
        self.refresh()
        self.w.open()

    def refresh(self, sender=None):
        self.font = Glyphs.font
        self.glyphs = []
        seen = set()
        if self.font is not None:
            for layer in self.font.selectedLayers or []:
                glyph = layer.parent
                if glyph is not None and glyph.name not in seen:
                    self.glyphs.append(glyph)
                    seen.add(glyph.name)
        names = [glyph.name for glyph in self.glyphs]
        self.w.source.setItems(names)
        self.w.target.setItems(names)
        if names:
            self.w.source.set(0)
            self.w.target.set(min(1, len(names) - 1))
        self.w.status.set("Select at least two glyphs, then refresh." if len(names) < 2 else "Ready.")
        self.source_changed()

    def source_changed(self, sender=None):
        if hasattr(self.w, "anchors"):
            del self.w.anchors
        self.checks = []
        names = set()
        if self.glyphs:
            source = self.glyphs[self.w.source.get()]
            names = {a.name for layer in source.layers for a in layer.anchors
                     if a.name.startswith("math.")}
        ordered = [name for name in ANCHOR_ORDER if name in names]
        ordered.extend(sorted(names.difference(ANCHOR_ORDER)))
        group = vanilla.Group((0, 0, 370, max(30, len(ordered) * 26)))
        for index, name in enumerate(ordered):
            check = vanilla.CheckBox((0, index * 26, -8, 22), name, value=True, callback=self.update_button)
            setattr(group, "anchor%d" % index, check)
            self.checks.append((name, check))
        if not ordered:
            group.empty = vanilla.TextBox((0, 0, -8, 22), "No math anchors in source.")
        self.anchor_group = group
        self.w.anchors = vanilla.ScrollView((12, 142, -12, 156), group.getNSView(), hasHorizontalScroller=False)
        self.update_button()

    def update_button(self, sender=None):
        self.w.run.enable(len(self.glyphs) >= 2
                          and self.w.source.get() != self.w.target.get()
                          and any(check.get() for _, check in self.checks))

    def run(self, sender):
        if not any(font == self.font for font in Glyphs.fonts):
            Message("Font closed", "Open the font and refresh the selected glyphs.")
            return
        source = self.glyphs[self.w.source.get()]
        target = self.glyphs[self.w.target.get()]
        if source == target:
            return
        names = [name for name, check in self.checks if check.get()]
        try:
            changes, report = copy_plan(source, target, names,
                                        self.w.overwrite.get(), self.w.fallback.get())
            self.font.disableUpdateInterface()
            try:
                target.beginUndo()
                try:
                    for layer, anchor in changes:
                        layer.anchors[anchor.name] = anchor
                finally:
                    target.endUndo()
            finally:
                self.font.enableUpdateInterface()
                Glyphs.redraw()
            count = len({layer.layerId for layer, _ in changes})
            summary = "Copied %d anchors on %d layers." % (len(changes), count)
            self.w.status.set(summary + (" See Macro Window for details." if report else ""))
            print("Steal Math Anchors: %s → %s\n%s" % (source.name, target.name, summary))
            if report:
                Glyphs.showMacroWindow()
                print("\n".join(report))
        except Exception:
            self.w.status.set("Copy failed; see Macro Window.")
            Glyphs.showMacroWindow()
            traceback.print_exc()


if __name__ == "__main__":
    previous_window = getattr(globals().get("steal_math_anchors"), "w", None)
    # Vanilla clears _window on close, but the script instance can survive.
    if getattr(previous_window, "_window", None) is not None:
        previous_window.close()
    steal_math_anchors = StealMathAnchors()
