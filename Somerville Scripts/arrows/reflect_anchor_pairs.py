# MenuTitle: Reflect Paired Anchors Around Center Anchor
# -*- coding: utf-8 -*-

from GlyphsApp import Glyphs


# --------------------------------------------------------------------
# SETTINGS
# --------------------------------------------------------------------
#
# Add reusable source/target anchor pairs here.
#
# For each pair:
#     A = X position of source anchor
#     B = X position assigned to target anchor
#     C = X position of CENTER_ANCHOR_NAME
#
# The script enforces:
#
#     A - C = C - B
#
# so:
#
#     B = 2C - A
#

CENTER_ANCHOR_NAME = "center"

ANCHOR_PAIRS = [
    (
        "stroke_doublehead_tail",
        "stroke_tail_doublehead",
    )
   	,
   	(
        "stroke_doubletail_head",
        "stroke_head_doubletail",
    ),
       	(
        "stroke_doubletail_doublehead",
        "stroke_doublehead_doubletail",
    ),
           	(
        "stroke_DoubleStrokeHead_DoubleStrokeTail",
        "stroke_DoubleStrokeTail_DoubleStrokeHead",
    )
    # Add more pairs here:
    #
    # (
    #     "source_anchor_name",
    #     "target_anchor_name",
    # ),
]


# --------------------------------------------------------------------
# HELPERS
# --------------------------------------------------------------------

def anchor_by_name(layer, anchor_name):
    """
    Return an explicitly defined anchor from the layer, or None.
    """
    try:
        return layer.anchors[anchor_name]
    except Exception:
        pass

    try:
        for anchor in layer.anchors:
            if anchor.name == anchor_name:
                return anchor
    except Exception:
        pass

    return None


def layer_type(layer):
    try:
        if layer.isMasterLayer:
            return "master"
    except Exception:
        pass

    try:
        if layer.isSpecialLayer:
            return "special/intermediate"
    except Exception:
        pass

    return "other"


# --------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------

Glyphs.clearLog()
Glyphs.showMacroWindow()

font = Glyphs.font

print("=" * 80)
print("REFLECT PAIRED ANCHORS AROUND THE 'CENTER' ANCHOR")
print("=" * 80)

if font is None:
    print("ERROR: No font is open.")

elif not font.selectedLayers:
    print("ERROR: No glyph is selected.")

else:
    glyph = font.selectedLayers[0].parent

    changed = []
    already_correct = []
    missing_center = []
    missing_source = []
    missing_target = []
    errors = []

    print("Glyph              : %s" % glyph.name)
    print("Layers             : %d" % len(glyph.layers))
    print("Center anchor      : %s" % CENTER_ANCHOR_NAME)
    print("Configured pairs   : %d" % len(ANCHOR_PAIRS))
    print()

    print("Formula:")
    print("    A - C = C - B")
    print("    B = 2C - A")
    print()

    print("Configured anchor pairs:")

    for source_name, target_name in ANCHOR_PAIRS:
        print("    %s  ->  %s" % (source_name, target_name))

    interface_disabled = False

    try:
        try:
            font.disableUpdateInterface()
            interface_disabled = True
        except Exception:
            pass

        for layer in glyph.layers:
            print()
            print("=" * 80)
            print("LAYER: %s" % layer.name)
            print("TYPE : %s" % layer_type(layer))
            print("-" * 80)

            center_anchor = anchor_by_name(
                layer,
                CENTER_ANCHOR_NAME,
            )

            if center_anchor is None:
                print(
                    "SKIPPED ENTIRE LAYER: center anchor '%s' is missing."
                    % CENTER_ANCHOR_NAME
                )

                missing_center.append(layer.name)
                continue

            center_x = float(center_anchor.position.x)

            print("Center X, C: %.3f" % center_x)

            for source_name, target_name in ANCHOR_PAIRS:
                print()
                print("Pair: %s -> %s" % (source_name, target_name))

                source_anchor = anchor_by_name(
                    layer,
                    source_name,
                )

                if source_anchor is None:
                    print(
                        "    SKIPPED: source anchor '%s' is missing."
                        % source_name
                    )

                    missing_source.append(
                        (
                            layer.name,
                            source_name,
                            target_name,
                        )
                    )
                    continue

                target_anchor = anchor_by_name(
                    layer,
                    target_name,
                )

                if target_anchor is None:
                    print(
                        "    SKIPPED: target anchor '%s' is missing."
                        % target_name
                    )

                    missing_target.append(
                        (
                            layer.name,
                            source_name,
                            target_name,
                        )
                    )
                    continue

                try:
                    source_x = float(source_anchor.position.x)
                    old_target_x = float(target_anchor.position.x)
                    target_y = float(target_anchor.position.y)

                    new_target_x = 2.0 * center_x - source_x

                    left_difference = source_x - center_x
                    right_difference = center_x - new_target_x

                    print("    Source X, A       : %.3f" % source_x)
                    print("    Center X, C       : %.3f" % center_x)
                    print("    Old target X      : %.3f" % old_target_x)
                    print("    Required target B : %.3f" % new_target_x)
                    print(
                        "    Equation check     : "
                        "%.3f - %.3f = %.3f - %.3f"
                        % (
                            source_x,
                            center_x,
                            center_x,
                            new_target_x,
                        )
                    )
                    print(
                        "    Difference check   : %.3f = %.3f"
                        % (
                            left_difference,
                            right_difference,
                        )
                    )

                    if abs(old_target_x - new_target_x) < 0.0001:
                        print("    STATUS: already correct")

                        already_correct.append(
                            (
                                layer.name,
                                source_name,
                                target_name,
                                source_x,
                                center_x,
                                new_target_x,
                            )
                        )
                        continue

                    # Change only X; preserve the target anchor's Y.
                    target_anchor.position = (
                        new_target_x,
                        target_y,
                    )

                    actual_target_x = float(
                        target_anchor.position.x
                    )

                    print(
                        "    Target X changed   : %.3f -> %.3f"
                        % (
                            old_target_x,
                            actual_target_x,
                        )
                    )
                    print(
                        "    Target Y preserved : %.3f"
                        % target_y
                    )
                    print("    STATUS: changed")

                    changed.append(
                        (
                            layer.name,
                            source_name,
                            target_name,
                            source_x,
                            center_x,
                            old_target_x,
                            actual_target_x,
                        )
                    )

                except Exception as error:
                    print("    ERROR: %s" % error)

                    errors.append(
                        (
                            layer.name,
                            source_name,
                            target_name,
                            str(error),
                        )
                    )

    finally:
        if interface_disabled:
            try:
                font.enableUpdateInterface()
            except Exception:
                pass

    try:
        font.currentTab.redraw()
    except Exception:
        pass

    # ----------------------------------------------------------------
    # SUMMARY
    # ----------------------------------------------------------------

    print()
    print()
    print("=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)
    print("Glyph                    : %s" % glyph.name)
    print("Layers examined          : %d" % len(glyph.layers))
    print("Center anchor name       : %s" % CENTER_ANCHOR_NAME)
    print("Configured pairs         : %d" % len(ANCHOR_PAIRS))
    print("Positions changed        : %d" % len(changed))
    print("Already correct          : %d" % len(already_correct))
    print("Layers missing center    : %d" % len(missing_center))
    print("Missing source anchors   : %d" % len(missing_source))
    print("Missing target anchors   : %d" % len(missing_target))
    print("Errors                   : %d" % len(errors))

    if changed:
        print()
        print("-" * 80)
        print("CHANGED")
        print("-" * 80)

        for (
            layer_name,
            source_name,
            target_name,
            source_x,
            center_x,
            old_target_x,
            new_target_x,
        ) in changed:
            print(
                "%s: %s -> %s"
                % (
                    layer_name,
                    source_name,
                    target_name,
                )
            )
            print(
                "    A=%.3f, C=%.3f, B: %.3f -> %.3f"
                % (
                    source_x,
                    center_x,
                    old_target_x,
                    new_target_x,
                )
            )

    if already_correct:
        print()
        print("-" * 80)
        print("ALREADY CORRECT")
        print("-" * 80)

        for (
            layer_name,
            source_name,
            target_name,
            source_x,
            center_x,
            target_x,
        ) in already_correct:
            print(
                "%s: %s -> %s; A=%.3f, C=%.3f, B=%.3f"
                % (
                    layer_name,
                    source_name,
                    target_name,
                    source_x,
                    center_x,
                    target_x,
                )
            )

    if missing_center:
        print()
        print("-" * 80)
        print("LAYERS MISSING THE CENTER ANCHOR")
        print("-" * 80)

        for layer_name in missing_center:
            print(
                "%s: missing '%s'"
                % (
                    layer_name,
                    CENTER_ANCHOR_NAME,
                )
            )

    if missing_source:
        print()
        print("-" * 80)
        print("MISSING SOURCE ANCHORS")
        print("-" * 80)

        for layer_name, source_name, target_name in missing_source:
            print(
                "%s: missing '%s' for %s -> %s"
                % (
                    layer_name,
                    source_name,
                    source_name,
                    target_name,
                )
            )

    if missing_target:
        print()
        print("-" * 80)
        print("MISSING TARGET ANCHORS")
        print("-" * 80)

        for layer_name, source_name, target_name in missing_target:
            print(
                "%s: missing '%s' for %s -> %s"
                % (
                    layer_name,
                    target_name,
                    source_name,
                    target_name,
                )
            )

    if errors:
        print()
        print("-" * 80)
        print("ERRORS")
        print("-" * 80)

        for layer_name, source_name, target_name, error in errors:
            print(
                "%s, %s -> %s: %s"
                % (
                    layer_name,
                    source_name,
                    target_name,
                    error,
                )
            )

    print()
    print("=" * 80)
    print("DONE")
    print("=" * 80)