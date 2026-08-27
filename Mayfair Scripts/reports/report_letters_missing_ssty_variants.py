#MenuTitle: Report Letters Missing SSTY Variants
# -*- coding: utf-8 -*-

"""Report letter glyphs that lack an associated .ssty1 or .ssty2 glyph."""

from GlyphsApp import Glyphs, Message


SSTY1_SUFFIX = ".ssty1"
SSTY2_SUFFIX = ".ssty2"
SSTY_SUFFIXES = (SSTY1_SUFFIX, SSTY2_SUFFIX)


def is_ssty_glyph_name(glyph_name):
    return any(glyph_name.endswith(suffix) for suffix in SSTY_SUFFIXES)


def is_letter_glyph(glyph):
    try:
        return glyph.category == "Letter"
    except Exception:
        return False


def glyph_names_in_font(font):
    names = set()
    for glyph in font.glyphs:
        glyph_name = getattr(glyph, "name", None)
        if glyph_name:
            names.add(str(glyph_name))
    return names


def print_group(heading, glyph_names):
    print("%s: %i" % (heading, len(glyph_names)))
    if not glyph_names:
        print("  None")
        return
    for glyph_name in glyph_names:
        print("  %s" % glyph_name)


def main():
    Glyphs.clearLog()
    Glyphs.showMacroWindow()
    print("Report Letters Missing SSTY Variants")
    print("=" * 72)

    font = Glyphs.font
    if font is None:
        print("ERROR: No font is open.")
        Message("No Font Open", "Open a font before running this report.")
        return

    all_names = glyph_names_in_font(font)
    letter_names = sorted(
        str(glyph.name)
        for glyph in font.glyphs
        if getattr(glyph, "name", None)
        and is_letter_glyph(glyph)
        and not is_ssty_glyph_name(str(glyph.name))
    )

    missing_ssty1 = []
    missing_ssty2 = []
    incomplete_letters = set()
    complete_count = 0

    for glyph_name in letter_names:
        has_ssty1 = glyph_name + SSTY1_SUFFIX in all_names
        has_ssty2 = glyph_name + SSTY2_SUFFIX in all_names

        if has_ssty1 and has_ssty2:
            complete_count += 1
            continue

        incomplete_letters.add(glyph_name)
        if not has_ssty1:
            missing_ssty1.append(glyph_name + SSTY1_SUFFIX)
        if not has_ssty2:
            missing_ssty2.append(glyph_name + SSTY2_SUFFIX)

    incomplete_count = len(incomplete_letters)

    print("Font: %s" % (font.familyName or "Untitled"))
    print("Letter glyphs checked: %i" % len(letter_names))
    print("Complete pairs: %i" % complete_count)
    print("Letters missing one or both variants: %i" % incomplete_count)
    print("")
    print_group("Missing .ssty1 glyphs", missing_ssty1)
    print("")
    print_group("Missing .ssty2 glyphs", missing_ssty2)
    print("")
    print("Done.")


main()
