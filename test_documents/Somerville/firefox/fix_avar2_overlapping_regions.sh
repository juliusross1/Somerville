#!/usr/bin/env bash

set -euo pipefail

script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
if [[ -n "${PYTHON:-}" ]]; then
    python_bin="$PYTHON"
else
    repo_dir="$script_dir"
    while [[ "$repo_dir" != "/" && ! -x "$repo_dir/sources/venv/bin/python" ]]; do
        repo_dir="$(dirname -- "$repo_dir")"
    done

    if [[ ! -x "$repo_dir/sources/venv/bin/python" ]]; then
        echo "Could not find sources/venv/bin/python in this directory or any parent." >&2
        echo "Set PYTHON to a Python interpreter containing FontTools." >&2
        exit 1
    fi

    python_bin="$repo_dir/sources/venv/bin/python"
fi

show_help() {
    cat <<'EOF'
Usage:
  fix_avar2_overlapping_regions.sh [INPUT.ttf [OUTPUT.ttf]]
  fix_avar2_overlapping_regions.sh -h | --help

Fix the overlapping variation regions in Somerville's avar 2.0 table.

The script converts the full-range supports emitted by Glyphs into local
supports bounded by adjacent mapping points. It repairs these independent
mappings:

  opsz  -> opsz, STYA, STYB
  wght  -> MGHT

For mappings that remap their own driver axis, currently opsz, the script
reconstructs the complete ordinary avar segment map from Glyphs' avar2 point
data for compatibility with renderers that depend on it. It moves the avar2
supports into post-segment-map coordinates and converts the self-axis deltas
into residual corrections, preventing double mapping in renderers with full
avar2 support.

Other axes are removed from each region's conditions, and deltas affecting
outputs outside the corresponding mapping are cleared.

The required ordinary STYA/STYB mappings at -1 are restored to -1 -> -1.
Invalid values there cause Firefox to discard the entire avar table. All
ordinary segment maps are checked before the repaired font is saved.

Arguments:
  INPUT.ttf   Font to repair. Defaults to:
              ~/Documents/fontoutputs/SomervilleVF.ttf

  OUTPUT.ttf  Destination font. If omitted, INPUT.ttf is overwritten safely
              using a temporary file followed by an atomic replacement.

Environment:
  PYTHON      Python interpreter containing FontTools. Defaults to the
              repository's sources/venv/bin/python.

Examples:
  # Repair the default SomervilleVF.ttf in place:
  fix_avar2_overlapping_regions.sh

  # Repair a specified font in place:
  fix_avar2_overlapping_regions.sh path/to/SomervilleVF.ttf

  # Preserve the input and write a separate output:
  fix_avar2_overlapping_regions.sh input.ttf output-fixed.ttf
EOF
}

case "${1:-}" in
    -h|--help)
        show_help
        exit 0
        ;;
esac

input_font="${1:-$HOME/Documents/Somerville/fonts/Somerville/SomervilleMATHVF.ttf}"
output_font="${2:-$input_font}"

if [[ ! -f "$input_font" ]]; then
    echo "Input font not found: $input_font" >&2
    exit 1
fi

"$python_bin" - "$input_font" "$output_font" <<'PY'
from pathlib import Path
import os
import sys
import tempfile

from fontTools.ttLib import TTFont


input_path = Path(sys.argv[1]).expanduser().resolve()
output_path = Path(sys.argv[2]).expanduser().resolve()

font = TTFont(input_path)
if "avar" not in font:
    raise SystemExit("The font has no avar table.")

avar = font["avar"]
if (avar.majorVersion, avar.minorVersion) != (2, 0):
    raise SystemExit(
        "Expected avar version 2.0, found %i.%i."
        % (avar.majorVersion, avar.minorVersion)
    )

var_store = getattr(avar.table, "VarStore", None)
if var_store is None:
    raise SystemExit("The avar 2.0 table has no variation store.")

axis_tags = [axis.axisTag for axis in font["fvar"].axes]
mapping_groups = {
    "opsz": {"opsz", "STYA", "STYB"},
    "wght": {"MGHT"},
}
for driver_tag, output_tags in mapping_groups.items():
    missing = ({driver_tag} | output_tags) - set(axis_tags)
    if missing:
        raise SystemExit("Missing required axis or axes: %s" % ", ".join(sorted(missing)))

# Keep ordinary segment maps for compatibility. A self-mapped avar2 driver is
# converted below so its regions and deltas operate in the coordinate space
# after the ordinary map.
self_mapped_drivers = {
    driver_tag
    for driver_tag, output_tags in mapping_groups.items()
    if driver_tag in output_tags
}
for driver_tag in sorted(self_mapped_drivers):
    if avar.segments.get(driver_tag) is None:
        raise SystemExit("The avar table has no segment map for %s." % driver_tag)


def map_segment(segment_map, value):
    """Piecewise-linearly map one normalized coordinate through avar v1."""
    points = sorted(segment_map.items())
    if value <= points[0][0]:
        return points[0][1]
    if value >= points[-1][0]:
        return points[-1][1]
    for (start_from, start_to), (end_from, end_to) in zip(points, points[1:]):
        if value <= end_from:
            if value == start_from or end_from == start_from:
                return start_to
            progress = (value - start_from) / (end_from - start_from)
            return start_to + progress * (end_to - start_to)
    raise AssertionError("unreachable segment-map coordinate")

regions = var_store.VarRegionList.Region
if len(regions) < 2:
    raise SystemExit("Not enough avar2 regions to repair.")

# Assign a region to a driver when that driver's support is non-neutral.
# Glyphs writes the default-point support as (0, 0, 1), so checking the full
# tuple rather than only PeakCoord correctly keeps it in its driver group.
region_groups = {}
for driver_tag in mapping_groups:
    driver_index = axis_tags.index(driver_tag)
    region_groups[driver_tag] = [
        region_index
        for region_index, region in enumerate(regions)
        if (
            region.VarRegionAxis[driver_index].StartCoord,
            region.VarRegionAxis[driver_index].PeakCoord,
            region.VarRegionAxis[driver_index].EndCoord,
        )
        != (0, 0, 0)
    ]

claimed_regions = {}
for driver_tag, region_indices in region_groups.items():
    for region_index in region_indices:
        previous = claimed_regions.get(region_index)
        if previous is not None:
            raise SystemExit(
                "Region %i is driven by both %s and %s; refusing to guess."
                % (region_index, previous, driver_tag)
            )
        claimed_regions[region_index] = driver_tag

unclaimed = sorted(set(range(len(regions))) - set(claimed_regions))
if unclaimed:
    raise SystemExit(
        "Region(s) have no recognized driver: %s."
        % ", ".join(str(index) for index in unclaimed)
    )

# Turn each driver's full-range supports into independent local hats.
group_peaks = {}
group_mapped_peaks = {}
group_ordered_regions = {}
group_needs_repair = {}
for driver_tag, region_indices in region_groups.items():
    driver_index = axis_tags.index(driver_tag)
    ordered = sorted(
        region_indices,
        key=lambda index: regions[index].VarRegionAxis[driver_index].PeakCoord,
    )
    peaks = [regions[index].VarRegionAxis[driver_index].PeakCoord for index in ordered]
    group_ordered_regions[driver_tag] = ordered
    if len(set(peaks)) != len(peaks):
        raise SystemExit(
            "%s region peaks are not unique; refusing to guess." % driver_tag
        )
    if peaks[0] != 0 or peaks[-1] != 1:
        raise SystemExit(
            "Expected normalized %s endpoints 0 and 1, found %g and %g."
            % (driver_tag, peaks[0], peaks[-1])
        )
    group_peaks[driver_tag] = peaks
    group_needs_repair[driver_tag] = all(
        regions[region_index].VarRegionAxis[driver_index].StartCoord == 0
        and regions[region_index].VarRegionAxis[driver_index].EndCoord == 1
        for region_index in ordered
    )
    if driver_tag in self_mapped_drivers:
        if group_needs_repair[driver_tag]:
            output_axis_index = axis_tags.index(driver_tag)
            var_idx_map = getattr(avar.table, "VarIdxMap", None)
            if var_idx_map is None or len(var_idx_map.mapping) != len(axis_tags):
                raise SystemExit("Unexpected or missing avar2 VarIdxMap.")
            var_idx = int(var_idx_map.mapping[output_axis_index])
            major = var_idx >> 16
            minor = var_idx & 0xFFFF
            try:
                self_item = var_store.VarData[major].Item[minor]
                self_region_indices = var_store.VarData[major].VarRegionIndex
            except (IndexError, AttributeError):
                raise SystemExit(
                    "Invalid VariationIndex for output axis %s." % driver_tag
                )
            self_columns = {
                region_index: column
                for column, region_index in enumerate(self_region_indices)
            }
            reconstructed_map = {-1.0: -1.0, 0.0: 0.0, 1.0: 1.0}
            for region_index, peak in zip(ordered, peaks):
                if region_index not in self_columns:
                    raise SystemExit(
                        "The %s region %i is missing from its VarData."
                        % (driver_tag, region_index)
                    )
                target = peak + self_item[self_columns[region_index]] / 16384
                reconstructed_map[peak] = round(target * 16384) / 16384
            avar.segments[driver_tag] = reconstructed_map
        segment_map = avar.segments[driver_tag]
        mapped_peaks = [
            round(map_segment(segment_map, peak) * 16384) / 16384
            for peak in peaks
        ]
        if len(set(mapped_peaks)) != len(mapped_peaks):
            raise SystemExit(
                "%s peaks collide after the ordinary segment map; refusing to guess."
                % driver_tag
            )
    else:
        mapped_peaks = peaks
    group_mapped_peaks[driver_tag] = mapped_peaks
    if not group_needs_repair[driver_tag]:
        continue

    for position, region_index in enumerate(ordered):
        region = regions[region_index]
        driver = region.VarRegionAxis[driver_index]
        driver.PeakCoord = mapped_peaks[position]
        driver.StartCoord = mapped_peaks[position - 1] if position else 0
        driver.EndCoord = mapped_peaks[position + 1] if position + 1 < len(mapped_peaks) else 1
        for axis_index, support in enumerate(region.VarRegionAxis):
            if axis_index == driver_index:
                continue
            support.StartCoord = 0
            support.PeakCoord = 0
            support.EndCoord = 0

# VarIdxMap maps each output axis to a VariationIndex. Somerville currently
# uses one VarData block, but decode the full VariationIndex so failures remain
# explicit if that changes. Clear Glyphs-generated cross-group deltas, e.g.
# wght deltas in the wght->MGHT group or MGHT deltas in the opsz group.
var_idx_map = getattr(avar.table, "VarIdxMap", None)
if var_idx_map is None or len(var_idx_map.mapping) != len(axis_tags):
    raise SystemExit("Unexpected or missing avar2 VarIdxMap.")

variation_items = {}
for output_axis_index, output_tag in enumerate(axis_tags):
    var_idx = int(var_idx_map.mapping[output_axis_index])
    major = var_idx >> 16
    minor = var_idx & 0xFFFF
    try:
        item = var_store.VarData[major].Item[minor]
        region_indices = var_store.VarData[major].VarRegionIndex
    except (IndexError, AttributeError):
        raise SystemExit("Invalid VariationIndex for output axis %s." % output_tag)
    variation_items[output_tag] = (item, region_indices)
    for column, region_index in enumerate(region_indices):
        driver_tag = claimed_regions.get(region_index)
        if driver_tag and output_tag not in mapping_groups[driver_tag]:
            item[column] = 0

# Glyphs' self-axis deltas are relative to the original normalized driver
# coordinate: target - original. Since avar2 runs after the ordinary segment
# map, retain that map and convert each delta to target - mapped. The supports
# above were moved to the same mapped coordinates, so both Firefox's ordinary
# mapping and a full avar2 implementation reach the intended target.
for driver_tag in self_mapped_drivers:
    if not group_needs_repair[driver_tag]:
        continue
    driver_index = axis_tags.index(driver_tag)
    ordered = group_ordered_regions[driver_tag]
    item, region_indices = variation_items[driver_tag]
    columns = {region_index: column for column, region_index in enumerate(region_indices)}
    for region_index, original_peak, mapped_peak in zip(
        ordered, group_peaks[driver_tag], group_mapped_peaks[driver_tag]
    ):
        if region_index not in columns:
            raise SystemExit(
                "The %s region %i is missing from its VarData."
                % (driver_tag, region_index)
            )
        item[columns[region_index]] += round((original_peak - mapped_peak) * 16384)

# A support peaking at zero is a constant default contribution in an
# ItemVariationStore; it does not taper like an ordinary local hat. Glyphs
# stores complete deltas at later points, so subtract each group's default
# delta from its non-default deltas to turn them into residuals. This is a
# no-op for the opsz group (its default deltas are zero) and is essential for
# the nonzero default MGHT delta in the wght group.
for driver_tag, output_tags in mapping_groups.items():
    if not group_needs_repair[driver_tag]:
        continue
    driver_index = axis_tags.index(driver_tag)
    ordered = sorted(
        region_groups[driver_tag],
        key=lambda index: regions[index].VarRegionAxis[driver_index].PeakCoord,
    )
    default_region = ordered[0]
    for output_tag in output_tags:
        item, region_indices = variation_items[output_tag]
        columns = {region_index: column for column, region_index in enumerate(region_indices)}
        if default_region not in columns:
            raise SystemExit(
                "The %s default region is missing from %s's VarData."
                % (driver_tag, output_tag)
            )
        default_delta = item[columns[default_region]]
        if not default_delta:
            continue
        for region_index in ordered[1:]:
            if region_index not in columns:
                raise SystemExit(
                    "The %s region %i is missing from %s's VarData."
                    % (driver_tag, region_index, output_tag)
                )
            item[columns[region_index]] -= default_delta

# Glyphs can emit a positive output at -1 for these script axes. This breaks
# both the required endpoint and monotonic ordering, so OTS drops all of avar.
# Repair the ordinary map only; retain the avar2 cross-axis deltas above.
repaired_endpoints = []
for tag in ("STYA", "STYB"):
    segment_map = avar.segments[tag]
    if segment_map.get(-1.0) != -1.0:
        segment_map[-1.0] = -1.0
        repaired_endpoints.append(tag)

# Match the ordinary-map checks in Firefox's font sanitizer. Refuse to save
# other malformed mappings rather than silently write a font it will reject.
for tag, segment_map in avar.segments.items():
    if not segment_map:
        continue
    if any(segment_map.get(value) != value for value in (-1.0, 0.0, 1.0)):
        raise SystemExit("Missing required -1, 0 or 1 mapping for %s." % tag)
    points = sorted(segment_map.items())
    if any(not (-1 <= source <= 1 and -1 <= target <= 1) for source, target in points):
        raise SystemExit("Axis value map coordinate out of range for %s." % tag)
    if any(right[1] < left[1] for left, right in zip(points, points[1:])):
        raise SystemExit("Axis value map out of order for %s." % tag)

output_path.parent.mkdir(parents=True, exist_ok=True)
if input_path == output_path:
    temporary = tempfile.NamedTemporaryFile(
        prefix=output_path.stem + "-avar2-",
        suffix=output_path.suffix,
        dir=output_path.parent,
        delete=False,
    )
    temporary_path = Path(temporary.name)
    temporary.close()
    try:
        font.save(temporary_path)
        os.replace(temporary_path, output_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
else:
    font.save(output_path)

print("Repaired avar2 regions: %i" % len(regions))
if repaired_endpoints:
    print("Restored -1 -> -1 segment mappings: %s" % ", ".join(repaired_endpoints))
print("Reconstructed ordinary self-axis maps; converted avar2 deltas to residuals.")
for driver_tag in mapping_groups:
    print(
        "%s -> %s; peaks: %s"
        % (
            driver_tag,
            ", ".join(sorted(mapping_groups[driver_tag])),
            ", ".join("%g" % peak for peak in group_peaks[driver_tag]),
        )
        + ("" if group_needs_repair[driver_tag] else " (already localized)")
    )
print("Wrote: %s" % output_path)
PY
