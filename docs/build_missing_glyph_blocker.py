#!/usr/bin/env python3
"""Build a fallback font that blocks per-character system-font fallback."""

from pathlib import Path

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import newTable
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable


OUTPUT_PATH = Path(__file__).with_name("MissingGlyphBlocker.ttf")
UNITS_PER_EM = 1000
GLYPH_NAME = "missingGlyphBox"


def box_glyph():
    pen = TTGlyphPen(None)

    # Clockwise outer contour.
    pen.moveTo((250, 150))
    pen.lineTo((250, 650))
    pen.lineTo((750, 650))
    pen.lineTo((750, 150))
    pen.closePath()

    # Counter-clockwise inner contour, producing a hollow box.
    pen.moveTo((290, 190))
    pen.lineTo((710, 190))
    pen.lineTo((710, 610))
    pen.lineTo((290, 610))
    pen.closePath()
    return pen.glyph()


def unicode_map():
    # Cover every non-control Unicode scalar value. Surrogates are not Unicode
    # scalar values. A format-13 cmap compacts these mappings into two ranges.
    mapping = {codepoint: GLYPH_NAME for codepoint in range(0x20, 0xD800)}
    mapping.update({codepoint: GLYPH_NAME for codepoint in range(0xE000, 0x110000)})
    return mapping


def cmap_table(mapping):
    cmap = newTable("cmap")
    cmap.tableVersion = 0
    cmap.tables = []

    for platform_id, encoding_id in ((0, 6), (3, 10)):
        subtable = CmapSubtable.newSubtable(13)
        subtable.platformID = platform_id
        subtable.platEncID = encoding_id
        subtable.language = 0
        subtable.cmap = mapping
        cmap.tables.append(subtable)

    return cmap


def build():
    builder = FontBuilder(UNITS_PER_EM, isTTF=True)
    builder.setupGlyphOrder([".notdef", GLYPH_NAME])

    empty_pen = TTGlyphPen(None)
    builder.setupGlyf({
        ".notdef": empty_pen.glyph(),
        GLYPH_NAME: box_glyph(),
    })
    builder.setupHorizontalMetrics({
        ".notdef": (1000, 0),
        GLYPH_NAME: (1000, 0),
    })
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.font["cmap"] = cmap_table(unicode_map())
    builder.setupNameTable({
        "familyName": "Missing Glyph Blocker",
        "styleName": "Regular",
        "uniqueFontIdentifier": "Missing Glyph Blocker Regular 1.000",
        "fullName": "Missing Glyph Blocker Regular",
        "psName": "MissingGlyphBlocker-Regular",
        "version": "Version 1.000",
    })
    builder.setupOS2(
        sTypoAscender=800,
        sTypoDescender=-200,
        usWinAscent=800,
        usWinDescent=200,
        sxHeight=500,
        sCapHeight=700,
    )
    builder.setupPost()
    builder.setupMaxp()

    # Stable timestamps make repeated builds byte-for-byte reproducible.
    builder.font["head"].created = 2082844800
    builder.font["head"].modified = 2082844800
    builder.font.recalcTimestamp = False
    builder.save(OUTPUT_PATH)
    print(f"Built {OUTPUT_PATH}")


if __name__ == "__main__":
    build()
