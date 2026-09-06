# -*- coding: utf-8 -*-
"""Prepare nested double, triple, quadruple, and contour integrals before export.

Use with glyphs export --script <this file> <source.glyphspackage>.
Decomposes every layer of the glyphs listed below in each loaded font before
export processing. The source file is never saved. This is a CLI export hook,
not a Scripts menu item.
"""

from GlyphsApp import Glyphs


GLYPH_NAMES = (
    "_smart.dblIntegral",
    "_smart.tripleIntegral",
    "_smart.quadrupleIntegral",
    "_smart.contourIntegral",
)


def main():
    for font in Glyphs.fonts:
        for glyph_name in GLYPH_NAMES:
            glyph = font.glyphs[glyph_name]
            if glyph is None:
                print("SKIP: %s is not in %s" % (glyph_name, font.familyName))
                continue
            count = 0
            for layer in glyph.layers:
                if len(layer.components):
                    layer.decomposeComponents()
                    count += 1
            print("Decomposed components in %i layers of %s" % (count, glyph_name))


main()
