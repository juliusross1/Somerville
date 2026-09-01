#!/usr/bin/env bash

set -euo pipefail

script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
repo_dir="$(CDPATH= cd -- "$script_dir/.." && pwd)"

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

Other axes are removed from each region's conditions, and deltas affecting
outputs outside the corresponding mapping are cleared.

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

input_font="${1:-$HOME/Documents/fontoutputs/SomervilleVF.ttf}"
output_font="${2:-$input_font}"
python_bin="${PYTHON:-$repo_dir/sources/venv/bin/python}"

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
group_needs_repair = {}
for driver_tag, region_indices in region_groups.items():
    driver_index = axis_tags.index(driver_tag)
    ordered = sorted(
        region_indices,
        key=lambda index: regions[index].VarRegionAxis[driver_index].PeakCoord,
    )
    peaks = [regions[index].VarRegionAxis[driver_index].PeakCoord for index in ordered]
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

    if not group_needs_repair[driver_tag]:
        continue

    for position, region_index in enumerate(ordered):
        region = regions[region_index]
        driver = region.VarRegionAxis[driver_index]
        driver.StartCoord = peaks[position - 1] if position else 0
        driver.EndCoord = peaks[position + 1] if position + 1 < len(peaks) else 1
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
