#!/opt/homebrew/opt/fonttools/libexec/bin/python
"""Repair avar2 data exported incorrectly by Glyphs.

Some Glyphs 4 exports put the desired mapped normalized coordinates directly in
the avar2 ItemVariationStore.  The OpenType avar2 table instead requires
interpolation coefficients for *deltas* from the incoming normalized
coordinates.  Since the variation regions overlap, using the mapped values as
coefficients makes their contributions accumulate and the axes race to their
maximum.

This script treats each existing non-neutral region's stored value as the
desired output at that region's peak, converts it to a delta, and solves for
the coefficients required by the existing variation regions.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.varLib.models import supportScalar


F2DOT14_SCALE = 1 << 14


def solve(matrix: list[list[float]], values: list[float]) -> list[float]:
    """Solve a square linear system using Gaussian elimination with pivoting."""
    n = len(values)
    augmented = [row[:] + [value] for row, value in zip(matrix, values)]

    for column in range(n):
        pivot = max(range(column, n), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            raise ValueError("avar2 variation regions form a singular system")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]

        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(n):
            if row == column:
                continue
            factor = augmented[row][column]
            if factor:
                augmented[row] = [
                    left - factor * right
                    for left, right in zip(augmented[row], augmented[column])
                ]

    return [augmented[row][-1] for row in range(n)]


def region_support(region, axis_tags: list[str]) -> dict[str, tuple[float, float, float]]:
    return {
        tag: (axis.StartCoord, axis.PeakCoord, axis.EndCoord)
        for tag, axis in zip(axis_tags, region.VarRegionAxis)
        if axis.PeakCoord != 0
    }


def peak_location(support: dict[str, tuple[float, float, float]]) -> dict[str, float]:
    return {tag: limits[1] for tag, limits in support.items()}


def repair(font: TTFont, verbose: bool = False) -> int:
    if "avar" not in font or font["avar"].table.Version < 0x00020000:
        raise ValueError("font has no avar version 2 table")
    if "fvar" not in font:
        raise ValueError("font has no fvar table")

    avar = font["avar"].table
    store = avar.VarStore
    axis_tags = [axis.axisTag for axis in font["fvar"].axes]
    regions = store.VarRegionList.Region
    supports = [region_support(region, axis_tags) for region in regions]
    changed = 0

    # VarIdxMap maps each output axis to an ItemVariationStore variation index.
    axis_variation_indices = avar.VarIdxMap.mapping

    # This Glyphs failure has a strong signature: evaluating its coefficients
    # at the region peaks produces normalized coordinates far outside the
    # designspace. Refuse to reinterpret a table that does not have that
    # signature; in particular, this makes a second run on a repaired font safe.
    suspicious = False
    for axis_index, variation_index in enumerate(axis_variation_indices):
        if variation_index == 0xFFFFFFFF:
            continue
        item_outer = variation_index >> 16
        item_inner = variation_index & 0xFFFF
        var_data = store.VarData[item_outer]
        item = var_data.Item[item_inner]
        target_axis = axis_tags[axis_index]
        for region_index in var_data.VarRegionIndex:
            support = supports[region_index]
            if not support:
                continue
            location = peak_location(support)
            mapped = location.get(target_axis, 0.0)
            for coefficient, contributing_region in zip(
                item, var_data.VarRegionIndex
            ):
                mapped += (
                    supportScalar(location, supports[contributing_region])
                    * coefficient
                    / F2DOT14_SCALE
                )
            if mapped < -1.05 or mapped > 1.05:
                suspicious = True
                break
        if suspicious:
            break
    if not suspicious:
        raise ValueError(
            "avar2 does not have the out-of-range accumulation signature; "
            "it may already be repaired"
        )

    for outer_index, var_data in enumerate(store.VarData):
        region_indices = list(var_data.VarRegionIndex)
        active_columns = [
            column for column, region_index in enumerate(region_indices)
            if supports[region_index]
        ]
        if not active_columns:
            continue

        locations = [
            peak_location(supports[region_indices[column]])
            for column in active_columns
        ]
        matrix = [
            [
                supportScalar(location, supports[region_indices[column]])
                for column in active_columns
            ]
            for location in locations
        ]

        for axis_index, variation_index in enumerate(axis_variation_indices):
            if variation_index == 0xFFFFFFFF:
                continue
            item_outer = variation_index >> 16
            item_inner = variation_index & 0xFFFF
            if item_outer != outer_index:
                continue

            item = var_data.Item[item_inner]
            target_axis = axis_tags[axis_index]
            desired_deltas = []
            old_values = []
            for location, column in zip(locations, active_columns):
                desired_output = item[column] / F2DOT14_SCALE
                incoming = location.get(target_axis, 0.0)
                desired_deltas.append(desired_output - incoming)
                old_values.append(item[column])

            coefficients = solve(matrix, desired_deltas)
            new_values = [round(value * F2DOT14_SCALE) for value in coefficients]
            for column, value in zip(active_columns, new_values):
                if not -32768 <= value <= 32767:
                    raise ValueError(
                        f"coefficient {value} for {target_axis} exceeds int16 range"
                    )
                item[column] = value
            # A neutral region is a constant contribution. Glyphs emits zero at
            # the default, which is already the correct avar2 delta.
            for column, region_index in enumerate(region_indices):
                if not supports[region_index]:
                    item[column] = 0

            if old_values != new_values:
                changed += 1
                if verbose:
                    print(f"{target_axis}: {old_values} -> {new_values}")

    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Glyphs-exported variable TTF/OTF")
    parser.add_argument("output", type=Path, nargs="?", help="repaired output font")
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="replace the input and save the original alongside it as .avar2-bak",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if args.in_place and args.output:
        parser.error("OUTPUT and --in-place cannot be used together")
    if not args.in_place and not args.output:
        parser.error("provide OUTPUT or use --in-place")

    output = args.input if args.in_place else args.output
    assert output is not None
    font = TTFont(args.input)
    changed = repair(font, args.verbose)
    if not changed:
        print("No avar2 axis records required repair.")
        return 0

    if args.in_place:
        backup = args.input.with_suffix(args.input.suffix + ".avar2-bak")
        shutil.copy2(args.input, backup)
        print(f"Backup: {backup}")
    output.parent.mkdir(parents=True, exist_ok=True)
    font.save(output, reorderTables=False)
    print(f"Repaired {changed} avar2 axis records: {output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
