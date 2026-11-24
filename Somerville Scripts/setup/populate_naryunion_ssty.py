#MenuTitle: Populate Nary Union and Intersection SSTY
# -*- coding: utf-8 -*-

"""Populate round and square union/intersection SSTY series with heavier Agate samples."""

from pathlib import Path
import sys

from GlyphsApp import Glyphs

script_directory = str(Path(__file__).resolve().parent)
if script_directory not in sys.path:
    sys.path.insert(0, script_directory)

import designspace_axis_rotation as rotation


HEAVIER_MASTERS = (
    "Agate SemiCondensed Upright",
    "Agate SemiExpanded Upright",
)
SOURCE_WEIGHTS = {1: 450, 2: 500}
SOURCE_GLYPHS = (
    "naryunion",
    "naryintersection",
    "nArySquareUnionOperator",
    "nArySquareIntersectionOperator",
)
LOW_OPSZ = 5
HIGH_OPSZ = 1200
STY_MIN = 5
STY_MAX = 1200
STYLE_AXES = {1: ("STYA", "STYB"), 2: ("STYB", "STYA")}


def populate_naryunion_ssty(font, style):
    if font is None:
        raise RuntimeError("Open the Somerville math source before running this script.")
    target_axis, sibling_axis = STYLE_AXES[style]
    source_weight = SOURCE_WEIGHTS[style]

    axes = {tag: rotation.axis_id_for_tag(font, tag) for tag in ("opsz", "wght", "STYA", "STYB")}
    if any(axis is None for axis in axes.values()):
        raise RuntimeError("The font needs opsz, wght, STYA and STYB axes.")
    heavier_samples = []
    for master_name in HEAVIER_MASTERS:
        master = next((m for m in font.masters if m.name == master_name), None)
        if master is None:
            raise RuntimeError(f"Missing master: {master_name}")
        coordinates = rotation.master_coordinates(font, master)
        if coordinates is None:
            raise RuntimeError(f"Could not read the coordinates of {master_name}.")
        heavier_coordinates = rotation.coordinates_with_axis_value_overrides(
            coordinates, {axes["opsz"]: LOW_OPSZ, axes["wght"]: source_weight}
        )
        heavier_samples.append((master, heavier_coordinates))

    pairs = []
    for base_name in SOURCE_GLYPHS:
        target_name = f"{base_name}.ssty{style}"
        pairs.append((font.glyphs[base_name], font.glyphs[target_name]))
        pairs.extend(
            (font.glyphs[f"{base_name}.s{size:02d}"], font.glyphs[f"{target_name}.s{size:02d}"])
            for size in range(1, 21)
        )
    if any(source is None or target is None for source, target in pairs):
        raise RuntimeError(f"All union/intersection source series and SSTY{style} target series must exist.")

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

                for master, heavier_coordinates in heavier_samples:
                    layer = target.layers[master.id]
                    signature = rotation.layer_outline_signature(layer)
                    result = rotation.copy_sample_to_target(
                        font, sampling_source,
                        {"coordinates": heavier_coordinates, "associated_master_id": master.id},
                        layer,
                    )
                    if (not signature or not result["shapes"] or result["components"]
                            or signature != rotation.layer_outline_signature(layer)):
                        raise RuntimeError(f"Incompatible weight-{source_weight} sample for {target.name} ({master.name}).")
                    print(f"{target.name}: {master.name} sampled at internal wght={source_weight}.")
            finally:
                rotation.remove_temp_glyph(font, sampling_source)
    finally:
        font.enableUpdateInterface()

    print(f"Populated {len(pairs)} union/intersection SSTY{style} glyphs.")


if __name__ == "__main__":
    for script_style in STYLE_AXES:
        populate_naryunion_ssty(Glyphs.font, script_style)
