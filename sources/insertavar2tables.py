#!/usr/bin/env python3
"""Add CSV-driven automatic STYA/STYB mappings to a fresh Somerville math VF.

Usage (from the repository root):
    sources/venv/bin/python sources/insertavar2tables.py FONT.ttf
    sources/venv/bin/python sources/insertavar2tables.py FONT.ttf -o TEST.ttf

By default, update ~/Documents/fontoutputs/SomervilleMathVF.ttf atomically.
Read ../axis-mappings-2.csv relative to this script, not the working directory.
Keep the existing avar v1 segment maps and all axis ranges. CSV output columns
are internal design coordinates on Somerville's 5..1200 scale; input_opsz is
the user coordinate. Interpolate STYA/STYB linearly against INTERNAL opsz.

STYA/STYB become hidden, fully automatic axes: their own input coordinates are
cancelled, not added to the CSV targets. Correct fresh Glyphs fvar/STAT optical
size presets from internal coordinates to the CSV user coordinates, and reset
STYA/STYB named-instance inputs to defaults. Reject already converted avar v2
fonts. This is deliberately Somerville-specific, not a generic avar converter.
Inspired by ~/Documents/Pennstander/insertavartables.py.
"""

from __future__ import annotations

import argparse
import copy
import csv
import math
import os
import tempfile
from pathlib import Path

from fontTools.misc.fixedTools import floatToFixedToFloat
from fontTools.misc.roundTools import otRound
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables import otTables
from fontTools.varLib.builder import buildVarData, buildVarRegionList, buildVarStore
from fontTools.varLib.models import normalizeValue, piecewiseLinearMap
from fontTools.varLib.varStore import VarStoreInstancer


DEFAULT_FONT = Path.home() / "Documents/fontoutputs/SomervilleMathVF.ttf"
DEFAULT_CSV = Path(__file__).resolve().parent.parent / "axis-mappings-2.csv"
COLUMNS = ("input_opsz", "output_opsz", "output_STYA", "output_STYB")
DRIVEN = ("STYA", "STYB")
DESIGN_MIN, DESIGN_MAX = 5.0, 1200.0
SCALE = 16384
TOLERANCE = 3 / SCALE


def normalized(value):
    return (value - DESIGN_MIN) / (DESIGN_MAX - DESIGN_MIN)


def fixed(value):
    return floatToFixedToFloat(value, 14)


def load_rows(path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(COLUMNS):
            raise ValueError(f"CSV columns must be {','.join(COLUMNS)}")
        rows = []
        for number, record in enumerate(reader, 2):
            try:
                row = {key: float(record[key]) for key in COLUMNS}
            except (TypeError, ValueError) as error:
                raise ValueError(f"Invalid coordinate on CSV line {number}") from error
            if None in record or not all(math.isfinite(v) for v in row.values()):
                raise ValueError(f"Invalid CSV line {number}")
            rows.append(row)
    if len(rows) < 2:
        raise ValueError("CSV needs at least two rows")
    for key in ("input_opsz", "output_opsz"):
        values = [r[key] for r in rows]
        if any(a >= b for a, b in zip(values, values[1:])):
            raise ValueError(f"{key} must be strictly increasing")
        if (values[0], values[-1]) != (DESIGN_MIN, DESIGN_MAX):
            raise ValueError(f"{key} must cover {DESIGN_MIN}..{DESIGN_MAX}")
    for tag in DRIVEN:
        values = [r[f"output_{tag}"] for r in rows]
        if values[0] != DESIGN_MIN or any(not DESIGN_MIN <= v <= DESIGN_MAX for v in values):
            raise ValueError(f"output_{tag} must start at 5 and remain within 5..1200")
    knots = [fixed(normalized(r["output_opsz"])) for r in rows]
    if len(set(knots)) != len(knots):
        raise ValueError("CSV optical-size knots collide at F2DOT14 precision")
    return rows


def check_input(font):
    if "fvar" not in font or "avar" not in font:
        raise ValueError("Expected a fresh variable font with fvar and avar v1")
    if font["avar"].majorVersion != 1:
        raise ValueError("Expected avar v1; re-export before running this script again")
    axes = {a.axisTag: a for a in font["fvar"].axes}
    for tag in ("opsz", *DRIVEN):
        if tag not in axes:
            raise ValueError(f"Missing axis {tag}")
        a = axes[tag]
        if (a.minValue, a.defaultValue, a.maxValue) != (5, 5, 1200):
            raise ValueError(f"Expected {tag} range/default 5/5/1200")
    if "DSIG" in font:
        raise ValueError("Signed font: modifying it would invalidate DSIG")
    return axes


def build_avar(font, rows):
    tags = [a.axisTag for a in font["fvar"].axes]
    knots = [fixed(normalized(r["output_opsz"])) for r in rows]
    # Local triangular supports reproduce a piecewise-linear function. The
    # zero/default sample needs no region because both outputs are zero there.
    regions = [
        {"opsz": (knots[i - 1], knots[i], knots[i + 1] if i + 1 < len(knots) else 1.0)}
        for i in range(1, len(knots))
    ]
    # Cancel each driven axis's incoming post-avar1 coordinate over both signs.
    # Thus even an application explicitly supplying STYA/STYB cannot add them
    # a second time. These supports are independent of opsz and the other axis.
    for tag in DRIVEN:
        regions.extend([{tag: (0, 1, 1)}, {tag: (-1, -1, 0)}])
    deltas = []
    for tag in tags:
        values = [0] * len(regions)
        if tag in DRIVEN:
            values[:len(knots) - 1] = [
                otRound(normalized(r[f"output_{tag}"]) * SCALE) for r in rows[1:]
            ]
            offset = len(knots) - 1 + 2 * DRIVEN.index(tag)
            values[offset:offset + 2] = [-SCALE, SCALE]
        deltas.append(values)
    avar = newTable("avar")
    avar.majorVersion, avar.minorVersion = 2, 0
    avar.segments = copy.deepcopy(font["avar"].segments)
    avar.table = otTables.avar()
    avar.table.Reserved = 0
    mapping = otTables.DeltaSetIndexMap()
    mapping.Format = 0
    mapping.mapping = list(range(len(tags)))
    avar.table.VarIdxMap = mapping
    avar.table.VarStore = buildVarStore(
        buildVarRegionList(regions, tags),
        [buildVarData(list(range(len(regions))), deltas, optimize=False)],
    )
    return avar


def remap_presets(font, rows, axes):
    lookup = {r["output_opsz"]: r["input_opsz"] for r in rows}

    def user_opsz(value):
        if value not in lookup:
            raise ValueError(f"Preset internal opsz={value} is not in the CSV")
        return lookup[value]

    for instance in font["fvar"].instances:
        instance.coordinates["opsz"] = user_opsz(instance.coordinates["opsz"])
        for tag in DRIVEN:
            instance.coordinates[tag] = axes[tag].defaultValue
    for tag in DRIVEN:
        axes[tag].flags |= 1  # Hidden axes still exist in fvar and variation data.

    # STAT also uses USER coordinates. Preserve all labels/flags and other axes.
    # Accept the format-1 optical labels used by the fresh Somerville export;
    # fail explicitly rather than incorrectly rewriting unknown range formats.
    if "STAT" in font:
        stat = font["STAT"].table
        tags = [a.AxisTag for a in stat.DesignAxisRecord.Axis]
        for value in stat.AxisValueArray.AxisValue if stat.AxisValueArray else []:
            if value.Format == 4:
                for record in value.AxisValueRecord:
                    if tags[record.AxisIndex] == "opsz":
                        record.Value = user_opsz(record.Value)
            elif tags[value.AxisIndex] == "opsz":
                if value.Format != 1:
                    raise ValueError("Only format-1 optical-size STAT labels are supported")
                value.Value = user_opsz(value.Value)


def desired(rows, tag, internal_opsz):
    return normalized(piecewiseLinearMap(internal_opsz, {
        r["output_opsz"]: r[f"output_{tag}"] for r in rows
    }))


def validate(font, rows, original_segments):
    if font["avar"].majorVersion != 2 or font["avar"].segments != original_segments:
        raise ValueError("avar version or original segment maps were not preserved")
    axes = font["fvar"].axes
    tags = [a.axisTag for a in axes]
    knots = [r["output_opsz"] for r in rows]
    samples = sorted(set(knots + [5 + 1195 * i / 100 for i in range(101)]))
    # Evaluate v2 directly in POST-avar1 space: the CSV output_opsz values are
    # internal coordinates. Check exact knots, between-knots, and cancellation.
    for optical in samples:
        for a, b in ((0, 0), (1, 1), (0.37, 0.81), (-1, -0.5)):
            location = {"opsz": fixed(normalized(optical)), "STYA": a, "STYB": b}
            store = VarStoreInstancer(font["avar"].table.VarStore, axes, location)
            for index, tag in enumerate(tags):
                before = location.get(tag, 0)
                result = (otRound(before * SCALE) + otRound(store[index])) / SCALE
                expected = desired(rows, tag, optical) if tag in DRIVEN else before
                if abs(result - expected) > TOLERANCE:
                    raise ValueError(f"Invalid mapping at internal opsz={optical}: {tag}={result}, expected {expected}")
    for axis in axes:
        if axis.axisTag in DRIVEN and not axis.flags & 1:
            raise ValueError(f"{axis.axisTag} is not hidden")
    for instance in font["fvar"].instances:
        coordinates = instance.coordinates
        for axis in axes:
            v = coordinates[axis.axisTag]
            if not axis.minValue <= v <= axis.maxValue:
                raise ValueError(f"Named instance outside {axis.axisTag} range")
            if axis.axisTag in DRIVEN and v != axis.defaultValue:
                raise ValueError("Named instance has non-default driven-axis input")
        mapped = font.normalizeLocation(coordinates)
        a = next(a for a in axes if a.axisTag == "opsz")
        optical = piecewiseLinearMap(normalizeValue(coordinates['opsz'],
            (a.minValue, a.defaultValue, a.maxValue)), original_segments['opsz'])
        for tag in DRIVEN:
            expected = desired(rows, tag, 5 + optical * 1195)
            if abs(mapped.get(tag, 0) - expected) > TOLERANCE:
                raise ValueError("Named-instance automatic axis validation failed")


def insert_avar2_tables(font_path=DEFAULT_FONT, csv_path=DEFAULT_CSV, output=None):
    font_path, csv_path = Path(font_path).expanduser(), Path(csv_path).expanduser()
    destination = Path(output).expanduser() if output else font_path
    rows = load_rows(csv_path)
    temporary_name = None
    try:
        with TTFont(font_path, lazy=True, recalcTimestamp=False) as font:
            axes = check_input(font)
            segments = copy.deepcopy(font['avar'].segments)
            # Check that unrelated tables, especially MATH/gvar, survive bytewise.
            untouched = {tag: font.getTableData(tag) for tag in font.keys()
                         if tag not in ('GlyphOrder', 'head', 'avar', 'fvar', 'STAT')}
            avar = build_avar(font, rows)
            remap_presets(font, rows, axes)
            font['avar'] = avar
            validate(font, rows, segments)
            with tempfile.NamedTemporaryFile(prefix=f'.{destination.name}.',
                    suffix='.tmp', dir=destination.parent, delete=False) as temporary:
                temporary_name = temporary.name
            font.save(temporary_name, reorderTables=None)
        with TTFont(temporary_name, lazy=True) as saved:
            validate(saved, rows, segments)
            for tag, data in untouched.items():
                if saved.getTableData(tag) != data:
                    raise ValueError(f"Unrelated table {tag} changed")
        os.replace(temporary_name, destination)
        temporary_name = None
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)
    print(f"Wrote {destination}: avar v2; automatic hidden STYA/STYB; corrected fvar/STAT presets.")
    print(f"Preserved existing avar segment maps and all unrelated tables. CSV: {csv_path}")
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('font_path', nargs='?', type=Path, default=DEFAULT_FONT)
    parser.add_argument('--csv', type=Path, default=DEFAULT_CSV, help='CSV mapping file')
    parser.add_argument('-o', '--output', type=Path, help='Write a separate font instead of updating input')
    args = parser.parse_args()
    try:
        insert_avar2_tables(args.font_path, args.csv, args.output)
    except (ValueError, OSError) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == '__main__':
    main()
