# MenuTitle: Refresh LSB and RSB for Selected Glyphs
# -*- coding: utf-8 -*-
"""Invalidate cached geometry and recalculate spacing in Glyphs 4.

Refresh every stored layer and existing background of the selected glyphs.
Selected component sources are processed before selected composites. Existing
automatic-alignment settings are respected; metrics keys are not synchronized
or rewritten. Alignment can update component positions and advance widths.
"""

import math
import traceback

from GlyphsApp import Glyphs


def api_value(obj, name, default=None):
    value = getattr(obj, name, default)
    return value() if callable(value) else value


def selected_glyphs(font):
    glyphs = []
    seen = set()
    layers = list(font.selectedLayers or [])
    candidates = [layer.parent for layer in layers]
    if not candidates:
        candidates = list(font.selection or [])
    for glyph in candidates:
        if glyph is not None and glyph.name not in seen:
            seen.add(glyph.name)
            glyphs.append(glyph)
    return glyphs


def all_layers(glyph):
    """Reading background is lazy, so only access one that already exists."""
    result = []
    for layer in glyph.layers:
        result.append(layer)
        if api_value(layer, "hasBackground", False):
            background = api_value(layer, "background")
            if background is not None:
                result.append(background)
    return result


def source_first(glyphs, layers_by_name):
    selected = {glyph.name: glyph for glyph in glyphs}
    done = set()
    active = set()
    ordered = []

    def visit(glyph):
        if glyph.name in done:
            return
        if glyph.name in active:
            raise ValueError("Component dependency cycle involving %s." % glyph.name)
        active.add(glyph.name)
        for layer in layers_by_name[glyph.name]:
            for component in layer.components:
                source = selected.get(component.componentName)
                if source is not None:
                    visit(source)
        active.remove(glyph.name)
        done.add(glyph.name)
        ordered.append(glyph)

    for glyph in glyphs:
        visit(glyph)
    return ordered


def cached_spacing(layer):
    # LSB/RSB getters may themselves update the cache. Use the Fast getters
    # only for the diagnostic snapshot, before explicitly invalidating it.
    return (api_value(layer, "LSBFast"), api_value(layer, "RSBFast"),
            float(layer.width))


def format_spacing(values):
    def number(value):
        return "%g" % value if value is not None and math.isfinite(value) else "?"
    return "LSB %s, RSB %s, width %s" % tuple(number(value) for value in values)


def refresh_layer(layer):
    for component in layer.components:
        component.baseGlyphsHasChanged()
    layer.setNeedUpdateShapes()
    if len(layer.components):
        layer.setNeedsAlignment()
        # setNeedsAlignment alone waits until drawing; export may happen first.
        layer.doAlignComponents()
    layer.setNeedUpdateMetrics()
    layer.updateMetrics()
    return float(layer.LSB), float(layer.RSB), float(layer.width)


def main():
    Glyphs.clearLog()
    Glyphs.showMacroWindow()
    print("Refresh LSB and RSB for Selected Glyphs")
    font = Glyphs.font
    if font is None:
        print("No font open.")
        return
    glyphs = selected_glyphs(font)
    if not glyphs:
        print("Select one or more glyphs in Font View or Edit View.")
        return
    layers_by_name = {glyph.name: all_layers(glyph) for glyph in glyphs}
    # Resolve cycles before making any changes.
    ordered = source_first(glyphs, layers_by_name)
    refreshed = changed = failures = 0
    font.disableUpdateInterface()
    try:
        for glyph in ordered:
            print("\n%s" % glyph.name)
            glyph.beginUndo()
            try:
                for layer in layers_by_name[glyph.name]:
                    label = "%s [%s]%s" % (
                        layer.name, layer.layerId,
                        " (background)" if api_value(layer, "isBackground", False) else "")
                    try:
                        before = cached_spacing(layer)
                        after = refresh_layer(layer)
                        differs = any(old is not None and abs(old - new) > .001
                                      for old, new in zip(before, after))
                        refreshed += 1
                        changed += int(differs)
                        if differs:
                            print("  %s: cached %s -> refreshed %s" % (
                                label, format_spacing(before), format_spacing(after)))
                    except Exception:
                        failures += 1
                        print("  FAILED: %s" % label)
                        traceback.print_exc()
            finally:
                glyph.endUndo()
    finally:
        font.enableUpdateInterface()
        Glyphs.redraw()
    print("\nRefreshed %i layer(s) in %i glyph(s); %i layer(s) with changed spacing; %i failure(s)."
          % (refreshed, len(glyphs), changed, failures))


if __name__ == "__main__":
    main()
