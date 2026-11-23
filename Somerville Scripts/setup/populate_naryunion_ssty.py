#MenuTitle: Populate Nary Union SSTY
# -*- coding: utf-8 -*-

"""Rotate the n-ary union size series onto STYA or STYB with one heavier sample."""

from pathlib import Path
import sys

from GlyphsApp import Glyphs

script_directory = str(Path(__file__).resolve().parent)
if script_directory not in sys.path:
    sys.path.insert(0, script_directory)

import designspace_axis_rotation as rotation


HEAVIER_MASTER = "Agate SemiCondensed Upright"
SOURCE_WEIGHT = 500
LOW_OPSZ = 5
HIGH_OPSZ = 1200
STY_MIN = 5
STY_MAX = 1200
STYLE_AXES = {1: ("STYA", "STYB"), 2: ("STYB", "STYA")}


def populate_naryunion_ssty(font, style):
    if font is None:
        raise RuntimeError("Open the Somerville math source before running this script.")
    target_axis, sibling_axis = STYLE_AXES[style]
    target_name = f"naryunion.ssty{style}"

    master = next((m for m in font.masters if m.name == HEAVIER_MASTER), None)
    if master is None:
        raise RuntimeError(f"Missing master: {HEAVIER_MASTER}")
    axes = {tag: rotation.axis_id_for_tag(font, tag) for tag in ("opsz", "wght", "STYA", "STYB")}
    if any(axis is None for axis in axes.values()):
        raise RuntimeError("The font needs opsz, wght, STYA and STYB axes.")
    coordinates = rotation.master_coordinates(font, master)
    if coordinates is None:
        raise RuntimeError(f"Could not read the coordinates of {HEAVIER_MASTER}.")
    heavier_coordinates = rotation.coordinates_with_axis_value_overrides(
        coordinates, {axes["opsz"]: LOW_OPSZ, axes["wght"]: SOURCE_WEIGHT}
    )

    pairs = [(font.glyphs["naryunion"], font.glyphs[target_name])]
    pairs.extend(
        (font.glyphs[f"naryunion.s{size:02d}"], font.glyphs[f"{target_name}.s{size:02d}"])
        for size in range(1, 21)
    )
    if any(source is None or target is None for source, target in pairs):
        raise RuntimeError(f"The n-ary union source series and SSTY{style} target series must both exist.")

    font.disableUpdateInterface()
    try:
        for source, target in pairs:
            sampling_source = rotation.prepared_sampling_source_glyph(font, source)
            try:
                stats = rotation.rotate_glyph_designspace_from_source(
                    font, source, sampling_source, target,
                    "opsz", target_axis, LOW_OPSZ, HIGH_OPSZ, STY_MAX,
                    map_source_axis_coordinates_to_target_axis=True,
                    forced_destination_axis_values={sibling_axis: STY_MIN},
                )
                if not stats["modified"] or stats["skipped"] or stats["copy_layers_skipped"]:
                    raise RuntimeError(f"Incomplete SSTY{style} rotation for {target.name}: {stats}")

                layer = target.layers[master.id]
                signature = rotation.layer_outline_signature(layer)
                result = rotation.copy_sample_to_target(
                    font, sampling_source,
                    {"coordinates": heavier_coordinates, "associated_master_id": master.id},
                    layer,
                )
                if (not signature or not result["shapes"] or result["components"]
                        or signature != rotation.layer_outline_signature(layer)):
                    raise RuntimeError(f"Incompatible weight-{SOURCE_WEIGHT} sample for {target.name}.")
                print(f"{target.name}: {HEAVIER_MASTER} sampled at internal wght={SOURCE_WEIGHT}.")
            finally:
                rotation.remove_temp_glyph(font, sampling_source)
    finally:
        font.enableUpdateInterface()

    print(f"Populated {len(pairs)} n-ary union SSTY{style} glyphs.")


if __name__ == "__main__":
    for script_style in STYLE_AXES:
        populate_naryunion_ssty(Glyphs.font, script_style)
