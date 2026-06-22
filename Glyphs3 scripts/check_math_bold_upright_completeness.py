#MenuTitle: Check math bold upright completeness
# -*- coding: utf-8 -*-

"""
Warn about missing math-bold glyphs for upright math alphabet glyphs.

The script reads the upright blocks from "CustomFilter Mathematics Alphabets.plist".
For each upright glyph that exists in the open font, it checks that matching
bold-math and bolditalic-math glyphs also exist. It also checks .ssNN and .cvNN
alternates of each upright glyph when those alternates exist in the font.
"""

import os
import plistlib
import re

from GlyphsApp import Glyphs


MATHEMATICAL_ALPHABETS_PLIST = "CustomFilter Mathematics Alphabets.plist"
BOLD_MATH_SUFFIX = "bold-math"
BOLD_ITALIC_MATH_SUFFIX = "bolditalic-math"
UPRIGHT_BLOCK_NAME_PART = "Upright"
ALTERNATE_SUFFIX_PATTERN = re.compile(r"\.(ss|cv)\d+$")


def script_directory():
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except Exception:
        return os.getcwd()


SCRIPT_DIR = script_directory()


def print_warning(message):
    print("WARNING: %s" % message)


def mathematical_alphabets_plist_path():
    candidate_directories = [
        os.path.join(SCRIPT_DIR, "..", "sources"),
        os.path.join(SCRIPT_DIR, "..", "..", "sources"),
        os.path.join(os.getcwd(), "sources"),
    ]

    for directory in candidate_directories:
        path = os.path.abspath(os.path.join(directory, MATHEMATICAL_ALPHABETS_PLIST))
        if os.path.exists(path):
            return path
    return None


def load_upright_names():
    plist_path = mathematical_alphabets_plist_path()
    if plist_path is None:
        print_warning("Could not find %s." % MATHEMATICAL_ALPHABETS_PLIST)
        return [], []

    try:
        with open(plist_path, "rb") as plist_file:
            blocks = plistlib.load(plist_file)
    except Exception as error:
        print_warning("Could not read %s: %s" % (plist_path, error))
        return [], []

    glyph_names = []
    block_names = []
    seen = set()
    for block in blocks:
        block_name = block.get("name", "")
        if UPRIGHT_BLOCK_NAME_PART not in block_name:
            continue
        block_names.append(block_name)
        for glyph_name in block.get("list", []):
            if glyph_name in seen:
                continue
            seen.add(glyph_name)
            glyph_names.append(glyph_name)

    return glyph_names, block_names


def glyph_names_in_font(font):
    names = set()
    for glyph in font.glyphs:
        name = getattr(glyph, "name", None)
        if name:
            names.add(name)
    return names


def alternate_names_for_base(base_name, all_glyph_names):
    alternate_pattern = re.compile(r"^%s(\.(?:ss|cv)\d+)$" % re.escape(base_name))
    alternates = []
    for glyph_name in all_glyph_names:
        match = alternate_pattern.match(glyph_name)
        if match:
            alternates.append(glyph_name)
    return sorted(alternates, key=alternate_sort_key)


def alternate_sort_key(glyph_name):
    match = ALTERNATE_SUFFIX_PATTERN.search(glyph_name)
    if not match:
        return (glyph_name, "", -1)
    suffix = match.group(0)
    kind = suffix[1:3]
    number = int(suffix[3:])
    base_name = glyph_name[:-len(suffix)]
    return (base_name, kind, number)


def expected_bold_names(upright_name):
    suffix = ""
    base_name = upright_name
    alternate_match = ALTERNATE_SUFFIX_PATTERN.search(upright_name)
    if alternate_match:
        suffix = alternate_match.group(0)
        base_name = upright_name[:-len(suffix)]

    return (
        "%s%s%s" % (base_name, BOLD_MATH_SUFFIX, suffix),
        "%s%s%s" % (base_name, BOLD_ITALIC_MATH_SUFFIX, suffix),
    )


def check_upright_name(upright_name, all_glyph_names):
    missing_names = []
    bold_name, bold_italic_name = expected_bold_names(upright_name)

    if bold_name not in all_glyph_names:
        print_warning("%s exists, but %s is missing." % (upright_name, bold_name))
        missing_names.append(bold_name)

    if bold_italic_name not in all_glyph_names:
        print_warning("%s exists, but %s is missing." % (upright_name, bold_italic_name))
        missing_names.append(bold_italic_name)

    return missing_names


def append_unique(items, item):
    if item not in items:
        items.append(item)


def main():
    Glyphs.clearLog()
    Glyphs.showMacroWindow()
    print("Check math bold upright completeness")
    print("")

    font = Glyphs.font
    if font is None:
        print("No font is open.")
        return

    upright_names, block_names = load_upright_names()
    if not upright_names:
        print_warning("No upright glyph names were loaded.")
        return

    all_glyph_names = glyph_names_in_font(font)
    print("Font: %s" % (font.familyName or "Untitled"))
    print("Loaded %i upright glyph names from %s." % (len(upright_names), MATHEMATICAL_ALPHABETS_PLIST))
    print("Filter blocks: %s" % ", ".join(block_names))
    print("")

    checked_count = 0
    skipped_count = 0
    missing_names = []

    for upright_name in upright_names:
        if upright_name not in all_glyph_names:
            skipped_count += 1
            continue

        names_to_check = [upright_name]
        names_to_check.extend(alternate_names_for_base(upright_name, all_glyph_names))

        for name_to_check in names_to_check:
            checked_count += 1
            for missing_name in check_upright_name(name_to_check, all_glyph_names):
                append_unique(missing_names, missing_name)

    print("")
    print("Done. Checked %i upright glyph(s), skipped %i missing plist glyph(s), found %i missing bold glyph(s)." % (
        checked_count,
        skipped_count,
        len(missing_names),
    ))
    print("")
    print("Missing glyphs:")
    print(" ".join(missing_names) or "none")


try:
    main()
except Exception as error:
    import traceback

    Glyphs.clearLog()
    Glyphs.showMacroWindow()
    print("Check math bold upright completeness")
    print("")
    print("Error: %s" % error)
    print(traceback.format_exc())
