#MenuTitle: Create Blank SSTY Glyphs for Selection
# -*- coding: utf-8 -*-

"""Create blank .ssty1 and .ssty2 glyphs for the selected glyphs.

Run this Glyphs 3 script with one or more glyphs selected in Font View or Edit
View. For each unique selected glyph, it attempts to create ``<name>.ssty1``
and ``<name>.ssty2``. Existing glyphs with either target name are preserved
and reported; the script never overwrites them.

Each new glyph is deliberately blank. It receives only its name and the empty
master layers that Glyphs adds when a new GSGlyph is appended to the font. No
outlines, components, anchors, intermediate layers, Unicode values, metrics
keys, or other source-glyph metadata are copied.
"""

from GlyphsApp import Glyphs, GSGlyph, Message


SSTY_SUFFIXES = (".ssty1", ".ssty2")


def unique_selected_glyphs(font):
    result = []
    seen_names = set()
    try:
        selected_layers = list(font.selectedLayers or [])
    except Exception:
        selected_layers = []
    for layer in selected_layers:
        try:
            glyph = layer.parent
            glyph_name = str(glyph.name)
        except Exception:
            continue
        if glyph is None or not glyph_name or glyph_name in seen_names:
            continue
        seen_names.add(glyph_name)
        result.append(glyph)
    return result


def glyph_for_name(font, glyph_name):
    try:
        return font.glyphs[glyph_name]
    except Exception:
        return None


def glyph_is_blank(glyph):
    for layer in glyph.layers:
        try:
            if len(layer.shapes):
                return False
        except Exception:
            try:
                if len(layer.paths) or len(layer.components):
                    return False
            except Exception:
                pass
        try:
            if len(layer.anchors):
                return False
        except Exception:
            pass
    return True


def main():
    font = Glyphs.font
    Glyphs.clearLog()
    Glyphs.showMacroWindow()
    print("=" * 72)
    print("Create Blank SSTY Glyphs for Selection")
    print("=" * 72)

    if font is None:
        print("ERROR: No font is open.")
        Message("No Font Open", "Open a font before running this script.")
        return

    selected_glyphs = unique_selected_glyphs(font)
    if not selected_glyphs:
        print("ERROR: No glyphs are selected.")
        Message(
            "No Glyphs Selected",
            "Select one or more glyphs in Font View or Edit View.",
        )
        return

    print("Selected glyphs: %i" % len(selected_glyphs))
    print("  %s" % ", ".join(glyph.name for glyph in selected_glyphs))

    created_names = []
    existing_names = []
    errors = []
    font.disableUpdateInterface()
    try:
        for source_glyph in selected_glyphs:
            print("\nSource: %s" % source_glyph.name)
            for suffix in SSTY_SUFFIXES:
                target_name = "%s%s" % (source_glyph.name, suffix)
                if glyph_for_name(font, target_name) is not None:
                    existing_names.append(target_name)
                    print("  KEPT EXISTING: %s" % target_name)
                    continue
                try:
                    new_glyph = GSGlyph(target_name)
                    font.glyphs.append(new_glyph)
                    retained_glyph = glyph_for_name(font, target_name)
                    if retained_glyph is None:
                        raise RuntimeError("Glyphs did not retain the new glyph.")
                    if not glyph_is_blank(retained_glyph):
                        raise RuntimeError("The newly created glyph is unexpectedly nonblank.")
                    created_names.append(target_name)
                    print(
                        "  CREATED BLANK: %s (%i empty layer(s))"
                        % (target_name, len(retained_glyph.layers))
                    )
                except Exception as error:
                    errors.append("%s: %s" % (target_name, error))
                    print("  ERROR: %s" % error)
    finally:
        font.enableUpdateInterface()

    print("\n" + "-" * 72)
    print("Created blank glyphs: %i" % len(created_names))
    for glyph_name in created_names:
        print("  %s" % glyph_name)
    print("Existing glyphs preserved: %i" % len(existing_names))
    for glyph_name in existing_names:
        print("  %s" % glyph_name)
    print("Errors: %i" % len(errors))
    for error in errors:
        print("  %s" % error)

    summary = "Created %i blank glyph(s); preserved %i existing glyph(s)." % (
        len(created_names),
        len(existing_names),
    )
    if errors:
        summary += " See the Macro window for %i error(s)." % len(errors)
    Message("Blank SSTY Glyphs", summary)


main()
