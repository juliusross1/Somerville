#MenuTitle: Insert math.ta Anchors for Math Accents
# -*- coding: utf-8 -*-

"""
Insert missing `math.ta` anchors on common math accent glyphs.

The script works from the fixed `TARGET_GLYPHS` Unicode list below. For each
Unicode value, it finds the matching glyph in the current font and visits every
layer of that glyph.

Existing `math.ta` anchors are preserved. If a layer does not already have one,
the script adds a new `math.ta` anchor using this placement rule:

- Use the x-position of `_top` if that anchor exists.
- Otherwise use the x-position of `_bottom` if that anchor exists.
- Otherwise use the horizontal center of the layer.
- In all cases, place the y-position at that layer's master's cap height.

For non-master layers, the cap height comes from the associated master when
available; otherwise it falls back to the selected font master.

This is intended as a first-pass placement helper for accents used by
mathematics layout, including both combining marks and spacing/non-combining
accent glyphs. The y-position of `math.ta` is not used by the math engine, but
placing it at cap height keeps the anchors visually easy to inspect in Glyphs.
Some anchors may still need manual adjustment after the script runs.

The Macro panel reports each glyph, whether an anchor was kept or added on each
layer, and any target Unicode values that are missing from the font.
"""

from GlyphsApp import Glyphs, GSAnchor


TARGET_GLYPHS = [
    ("0060", "grave"),
    ("0300", "grave"),
    ("00B4", "acute"),
    ("0301", "acute"),
    ("005E", "hat"),
    ("0302", "hat"),
    ("02C6", "hat"),
    ("007E", "tilde"),
    ("0303", "tilde"),
    ("02DC", "tilde"),
    ("00AF", "overline"),
    ("203E", "over bar"),
    ("0304", "macron"),
    ("0305", "overbar"),
    ("005F", "lowline / lowline(mover)"),
    ("0332", "underbar"),
    ("0306", "breve"),
    ("02D8", "breve"),
    ("002E", "dot above"),
    ("02D9", "dot above"),
    ("0307", "dot above"),
    ("00A8", "double dot"),
    ("0308", "double dot"),
    ("0309", "hook above"),
    ("02DA", "ring"),
    ("030A", "ring"),
    ("02C7", "caron"),
    ("030C", "caron"),
    ("20D0", "left harpoon"),
    ("21BC", "left harpoon"),
    ("20D1", "right harpoon"),
    ("21C0", "right harpoon"),
    ("20D7", "right arrow"),
    ("2192", "right arrow"),
    ("27F6", "long right arrow"),
    ("20DB", "triple dots"),
    ("20DC", "four dots"),
    ("23B4", "top square bracket"),
    ("23B5", "bottom square bracket"),
    ("23DC", "top parenthesis"),
    ("23DD", "bottom parenthesis"),
    ("23DE", "top curly bracket"),
    ("23DF", "bottom curly bracket"),
]

TARGET_ANCHOR = "math.ta"


def layer_label(layer):
    return layer.name or layer.layerId


def cap_height_for_layer(font, layer):
    master = getattr(layer, "master", None)
    if master is not None:
        return master.capHeight

    associated_master_id = getattr(layer, "associatedMasterId", None)
    if associated_master_id:
        master = font.masters[associated_master_id]
        if master is not None:
            return master.capHeight

    return font.selectedFontMaster.capHeight


def anchor_position_for_layer(font, layer):
    cap_height = cap_height_for_layer(font, layer)

    top_anchor = layer.anchors["_top"]
    if top_anchor is not None:
        return (top_anchor.position.x, cap_height), "_top x + cap-height y"

    bottom_anchor = layer.anchors["_bottom"]
    if bottom_anchor is not None:
        return (bottom_anchor.position.x, cap_height), "_bottom x + cap-height y"

    return (layer.width / 2.0, cap_height), "center x + cap-height y"


def add_anchor(layer, position):
    anchor = GSAnchor()
    anchor.name = TARGET_ANCHOR
    anchor.position = position
    layer.anchors.append(anchor)
    return anchor


def glyph_for_unicode(font, unicode_value):
    glyph = None

    if hasattr(font, "glyphForUnicode_"):
        glyph = font.glyphForUnicode_(unicode_value)
        if glyph is not None:
            return glyph

    for candidate in font.glyphs:
        if candidate.unicode and candidate.unicode.upper() == unicode_value:
            return candidate

    return None


font = Glyphs.font
Glyphs.clearLog()
Glyphs.showMacroWindow()

if font is None:
    print("No font open.")
else:
    print("Adding missing '%s' anchors for math accent glyphs in %s" % (TARGET_ANCHOR, font.familyName))
    print("Existing '%s' anchors will be left unchanged.\n" % TARGET_ANCHOR)

    font.disableUpdateInterface()
    added_count = 0
    existing_count = 0
    missing_count = 0

    try:
        for unicode_value, description in TARGET_GLYPHS:
            glyph = glyph_for_unicode(font, unicode_value)

            if glyph is None:
                print("MISSING GLYPH: U+%s %s" % (unicode_value, description))
                missing_count += 1
                continue

            print("%s: %s (%s)" % (glyph.name, "U+" + unicode_value, description))

            for layer in glyph.layers:
                existing_anchor = layer.anchors[TARGET_ANCHOR]
                if existing_anchor is not None:
                    print("  - %s: kept existing %s at (%.1f, %.1f)" % (
                        layer_label(layer),
                        TARGET_ANCHOR,
                        existing_anchor.position.x,
                        existing_anchor.position.y,
                    ))
                    existing_count += 1
                    continue

                position, source_name = anchor_position_for_layer(font, layer)
                new_anchor = add_anchor(layer, position)

                print("  + %s: added %s from %s at (%.1f, %.1f)" % (
                    layer_label(layer),
                    TARGET_ANCHOR,
                    source_name,
                    new_anchor.position.x,
                    new_anchor.position.y,
                ))
                added_count += 1

            print("")

    finally:
        font.enableUpdateInterface()

    print("Done.")
    print("Added anchors: %i" % added_count)
    print("Existing anchors kept: %i" % existing_count)
    print("Missing glyphs: %i" % missing_count)
