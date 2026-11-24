#!/usr/bin/env python3
"""Add CSV-driven automatic STYA/STYB mappings to a fresh Somerville math VF.

Usage (from the repository root):
    sources/venv/bin/python sources/insertavar2tables.py FONT.ttf
    sources/venv/bin/python sources/insertavar2tables.py FONT.ttf -o TEST.ttf

By default, update ~/Documents/fontoutputs/SomervilleMathVF.ttf atomically.
Read ../axis-mappings-2.csv relative to this script, not the working directory.
Expose internal width 95 as user width 88, keeping 100 and 113 fixed
and preserving the exported upper limit. Disable the source width
Axis Mappings before export. Expose MGHT as 0..100, default 50. At 0/100
select internal MGHT 360/900; at 50 select min(internal wght + 200, 900).
Interpolate linearly on either side of 50. All named instances use MGHT 50.
Preserve the other avar v1 segment maps/ranges.
CSV output columns
are internal design coordinates on Somerville's 5..1200 scale; input_opsz is
the user coordinate. Interpolate STYA/STYB linearly against INTERNAL opsz.

STYA/STYB become hidden, fully automatic axes: their own input coordinates are
cancelled, not added to the CSV targets. Correct fresh Glyphs fvar/STAT optical
size presets from internal coordinates to the CSV user coordinates, and reset
STYA/STYB named-instance inputs to defaults. Reject already converted avar v2
fonts. This is deliberately Somerville-specific, not a generic avar converter.
Rebuild the seven visible axes' STAT labels from the guide's names and values;
only Regular labels are elidable. This does not redefine fvar axis defaults.
Remove the redundant ital STAT axis and its style-link values.
Preserve existing name records and add names needed by the corrected STAT.
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
from fontTools.otlLib.builder import buildStatTable
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
WEIGHT_MIN, WEIGHT_MAX, MATH_BOOST = 360.0, 900.0, 200.0
SCALE = 16384
TOLERANCE = 3 / SCALE

# Visible-axis labels from the tables in sommerville-guide.tex. STAT's
# elidable flag describes the Regular style; it does not change fvar defaults.
STAT_LABELS = {
    'wdth': ('Width', [(88, 'SemiCondensed'), (100, 'Regular'), (113, 'SemiExpanded')]),
    'wght': ('Weight', [(360, 'SemiLight'), (400, 'Regular'), (500, 'Medium'),
                        (600, 'SemiBold'), (700, 'Bold'), (800, 'ExtraBold'), (900, 'Black')]),
    'MGHT': ('Math Weight', [(0, 'None'), (25, 'Lighter'), (50, 'Regular'),
                            (75, 'Heavier'), (100, 'Heaviest')]),
    # Needlepoint=1200 is commented out in the guide's optical-size table.
    'opsz': ('Optical Size', [(5, 'Micro'), (6, 'Minuscule'), (7, 'Miniature'),
                             (8, 'Caption'), (12, 'Regular'), (16, 'SubHeading'),
                             (21, 'Trumpet'), (32, 'Headline'), (48, 'Display'),
                             (72, 'Titling'), (96, 'Hairline')]),
    'INSL': ('Integral Slant', [(0, 'Regular'), (50, 'SemiSlanted'), (100, 'Slanted')]),
    'ARLN': ('Arrow Length', [(0, 'Shortest'), (50, 'Short'), (100, 'Regular'),
                             (150, 'Long'), (200, 'Longest')]),
    'ARHD': ('Arrow Head', [(100, 'Regular'), (150, 'Larger'), (200, 'Largest')]),
}


def update_stat_labels(font):
    """Replace visible-axis STAT labels with guide names in user coordinates."""
    if 'STAT' not in font:
        buildStatTable(font, [dict(tag=a.axisTag, name=a.axisNameID, ordering=i)
                             for i, a in enumerate(font['fvar'].axes)])
    stat = font['STAT'].table
    # Removing a design-axis record requires reindexing all retained values,
    # including format-4 records that refer to more than one axis.
    old_axes = stat.DesignAxisRecord.Axis
    retained = [(i, a) for i, a in enumerate(old_axes) if a.AxisTag != 'ital']
    indices = {old: new for new, (old, _) in enumerate(retained)}
    retained_values = []
    for value in stat.AxisValueArray.AxisValue if stat.AxisValueArray else []:
        records = value.AxisValueRecord if value.Format == 4 else [value]
        if any(record.AxisIndex not in indices for record in records):
            continue
        for record in records:
            record.AxisIndex = indices[record.AxisIndex]
        retained_values.append(value)
    stat.DesignAxisRecord.Axis = [axis for _, axis in retained]
    if stat.AxisValueArray:
        stat.AxisValueArray.AxisValue = retained_values
    names = font['name']
    ids = {}
    for name_id in sorted({r.nameID for r in names.names}):
        ids.setdefault(names.getDebugName(name_id), name_id)

    def name_id(label):
        if label not in ids:
            ids[label] = names.addName(label)
        return ids[label]

    axes = stat.DesignAxisRecord.Axis
    tags = [a.AxisTag for a in axes]
    fvar = {a.axisTag: a for a in font['fvar'].axes}
    for tag, (label, presets) in STAT_LABELS.items():
        if tag not in tags:
            axis = otTables.AxisRecord()
            axis.AxisTag = tag
            axis.AxisOrdering = max((a.AxisOrdering for a in axes), default=-1) + 1
            axes.append(axis)
            tags.append(tag)
        axes[tags.index(tag)].AxisNameID = name_id(label)
        for value, _ in presets:
            if not fvar[tag].minValue <= value <= fvar[tag].maxValue:
                raise ValueError(f'STAT preset outside {tag} range: {value}')
    values = []
    for value in stat.AxisValueArray.AxisValue if stat.AxisValueArray else []:
        affected = ([tags[r.AxisIndex] for r in value.AxisValueRecord]
                    if value.Format == 4 else [tags[value.AxisIndex]])
        if not any(tag in STAT_LABELS for tag in affected):
            values.append(value)
    for index, tag in enumerate(tags):
        if tag not in STAT_LABELS:
            continue
        for coordinate, label in STAT_LABELS[tag][1]:
            value = otTables.AxisValue()
            value.Format, value.AxisIndex = 1, index
            value.Value = coordinate
            value.ValueNameID = name_id(label)
            value.Flags = 2 if label == 'Regular' else 0
            values.append(value)
    stat.DesignAxisCount = len(axes)
    stat.AxisValueArray = otTables.AxisValueArray()
    stat.AxisValueArray.AxisValue = values
    stat.AxisValueCount = len(values)
    stat.ElidedFallbackNameID = name_id('Regular')


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
    for tag in ("wght", "MGHT"):
        if tag not in axes:
            raise ValueError(f"Missing axis {tag}")
        a = axes[tag]
        if (a.minValue, a.defaultValue, a.maxValue) != (WEIGHT_MIN, WEIGHT_MIN, WEIGHT_MAX):
            raise ValueError(f"Expected fresh internal {tag} range/default 360/360/900")
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
    math_regions, math_deltas = build_math_weight_regions()
    math_offset = len(regions)
    regions.extend(math_regions)
    deltas = []
    for tag in tags:
        values = [0] * len(regions)
        if tag in DRIVEN:
            values[:len(knots) - 1] = [
                otRound(normalized(r[f"output_{tag}"]) * SCALE) for r in rows[1:]
            ]
            offset = len(knots) - 1 + 2 * DRIVEN.index(tag)
            values[offset:offset + 2] = [-SCALE, SCALE]
        elif tag == "MGHT":
            values[math_offset:] = math_deltas
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


def build_math_weight_regions():
    """Express MGHT's two linear spans as products of axis-region scalars.

    w is post-avar1 normalized wght, m is normalized user MGHT (-1..1).
    The desired output is q(w)*(1-abs(m)) + max(m, 0), where
    q(w) = min(w + 200/540, 1). Subtract incoming m to obtain deltas.
    A region with no participating axes supplies the nonzero default offset.
    """
    boost = MATH_BOOST / (WEIGHT_MAX - WEIGHT_MIN)
    ceiling = fixed(1 - boost)
    base = otRound(boost * SCALE)
    # The last two supports sum to a ramp that plateaus at internal wght 700.
    terms = [({}, base),
             ({"wght": (0, ceiling, 1)}, SCALE - base),
             ({"wght": (ceiling, 1, 1)}, SCALE - base)]
    regions, deltas = [], []
    for support, delta in terms:
        regions.extend([support,
                        {**support, "MGHT": (-1, -1, 0)},
                        {**support, "MGHT": (0, 1, 1)}])
        deltas.extend([delta, -delta, -delta])
    # Cancel the negative half of the incoming MGHT coordinate.
    regions.append({"MGHT": (-1, -1, 0)})
    deltas.append(SCALE)
    return regions, deltas


def desired_math_weight(internal_weight, user_math_weight):
    midpoint = min(internal_weight + MATH_BOOST, WEIGHT_MAX)
    internal = piecewiseLinearMap(user_math_weight, {
        0: WEIGHT_MIN, 50: midpoint, 100: WEIGHT_MAX,
    })
    return (internal - WEIGHT_MIN) / (WEIGHT_MAX - WEIGHT_MIN)


def remap_math_weight(font, axes):
    axis = axes["MGHT"]
    axis.minValue, axis.defaultValue, axis.maxValue = 0, 50, 100
    # The old MGHT segment map describes the old user scale; v2 now supplies
    # the complete mapping into the unchanged gvar/MATH design coordinates.
    font["avar"].segments["MGHT"] = {-1.0: -1.0, 0.0: 0.0, 1.0: 1.0}
    for instance in font["fvar"].instances:
        instance.coordinates["MGHT"] = 50
    if "STAT" not in font:
        return
    stat = font["STAT"].table
    tags = [a.AxisTag for a in stat.DesignAxisRecord.Axis]
    if "MGHT" not in tags:
        return
    # Old single-axis labels describe internal coordinates and cannot be
    # inverted independently of wght. Replace those presets with Regular=50.
    values, inserted = [], False
    for value in stat.AxisValueArray.AxisValue if stat.AxisValueArray else []:
        if value.Format == 4:
            for record in value.AxisValueRecord:
                if tags[record.AxisIndex] == "MGHT":
                    record.Value = 50
        elif tags[value.AxisIndex] == "MGHT":
            if not inserted:
                regular = otTables.AxisValue()
                regular.Format, regular.AxisIndex = 1, tags.index("MGHT")
                regular.Flags, regular.ValueNameID, regular.Value = 2, 2, 50
                values.append(regular)
                inserted = True
            continue
        values.append(value)
    if stat.AxisValueArray:
        stat.AxisValueArray.AxisValue = values
        stat.AxisValueCount = len(values)


def validate_math_weight(font):
    axes = {a.axisTag: a for a in font["fvar"].axes}
    a = axes["MGHT"]
    if (a.minValue, a.defaultValue, a.maxValue) != (0, 50, 100):
        raise ValueError("Expected user MGHT range/default 0/50/100")
    a = axes["wght"]
    weight_range = (a.minValue, a.defaultValue, a.maxValue)
    weights = {WEIGHT_MIN + (WEIGHT_MAX - WEIGHT_MIN) * i / 40 for i in range(41)}
    weights.update(a.defaultValue + k * (a.maxValue - a.defaultValue)
                   for k in font["avar"].segments["wght"] if k >= 0)
    ceiling = 1 - MATH_BOOST / (WEIGHT_MAX - WEIGHT_MIN)
    user_ceiling = a.defaultValue + (a.maxValue - a.defaultValue) * piecewiseLinearMap(
        ceiling, {v: k for k, v in font["avar"].segments["wght"].items()})
    weights.update((user_ceiling - 0.01, user_ceiling, user_ceiling + 0.01))
    strengths = sorted({2.5 * i for i in range(41)} | {0.01, 49.99, 50.01, 99.99})
    for weight in sorted(weights):
        internal = WEIGHT_MIN + piecewiseLinearMap(
            normalizeValue(weight, weight_range), font["avar"].segments["wght"]
        ) * (WEIGHT_MAX - WEIGHT_MIN)
        for strength in strengths:
            actual = font.normalizeLocation({"wght": weight, "MGHT": strength}).get("MGHT", 0)
            expected = desired_math_weight(internal, strength)
            if abs(actual - expected) > TOLERANCE:
                raise ValueError(f"Invalid MGHT at wght={weight}, MGHT={strength}: {actual}, expected {expected}")
    # Missing axes must also use the new user default, including the v2 offset.
    default = font.normalizeLocation({}).get("MGHT", 0)
    if abs(default - desired_math_weight(WEIGHT_MIN, 50)) > TOLERANCE:
        raise ValueError("Missing MGHT did not select user default 50")
    for instance in font["fvar"].instances:
        if instance.coordinates["MGHT"] != 50:
            raise ValueError("Named instance has non-default user MGHT")


def remap_width(font, axes):
    """Change user coordinates without changing the outlines at design widths."""
    axis = axes.get("wdth")
    if axis is None or axis.minValue != 95 or axis.maxValue <= 100:
        raise ValueError("Expected fresh internal wdth range 95..>100; disable source width mapping")
    old_range = (axis.minValue, axis.defaultValue, axis.maxValue)
    old_segments = copy.deepcopy(font['avar'].segments['wdth'])

    def user_width(value):
        return piecewiseLinearMap(value, {95: 88, 100: 100, 113: 113})

    axis.minValue = user_width(old_range[0])
    axis.defaultValue = user_width(old_range[1])
    axis.maxValue = user_width(old_range[2])
    new_range = (axis.minValue, axis.defaultValue, axis.maxValue)
    # Include existing avar knots as well as the new slope change at 100.
    widths = {old_range[0], old_range[1], old_range[2], 100}
    for knot in old_segments:
        width = (old_range[1] + knot * (old_range[1] - old_range[0])
                 if knot < 0 else old_range[1] + knot * (old_range[2] - old_range[1]))
        widths.add(width)
    segments = {-1.0: -1.0, 0.0: 0.0, 1.0: 1.0}
    for width in widths:
        segments[fixed(normalizeValue(user_width(width), new_range))] = fixed(piecewiseLinearMap(
            normalizeValue(width, old_range), old_segments))
    font['avar'].segments['wdth'] = segments
    for instance in font['fvar'].instances:
        instance.coordinates['wdth'] = user_width(instance.coordinates['wdth'])
    if 'STAT' in font:
        stat = font['STAT'].table
        tags = [a.AxisTag for a in stat.DesignAxisRecord.Axis]
        for value in stat.AxisValueArray.AxisValue if stat.AxisValueArray else []:
            if value.Format == 4:
                for record in value.AxisValueRecord:
                    if tags[record.AxisIndex] == 'wdth':
                        record.Value = user_width(record.Value)
            elif tags[value.AxisIndex] == 'wdth':
                fields = {1: ('Value',), 2: ('NominalValue', 'RangeMinValue', 'RangeMaxValue'),
                          3: ('Value', 'LinkedValue')}[value.Format]
                for field in fields:
                    setattr(value, field, user_width(getattr(value, field)))
    return old_range, old_segments


def validate_width(font, original):
    old_range, old_segments = original
    axis = next(a for a in font['fvar'].axes if a.axisTag == 'wdth')
    if (axis.minValue, axis.maxValue) != (88, old_range[2]):
        raise ValueError("Incorrect user width range")
    for i in range(101):
        width = 95 + (old_range[2] - 95) * i / 100
        user = piecewiseLinearMap(width, {95: 88, 100: 100, 113: 113})
        expected = piecewiseLinearMap(normalizeValue(width, old_range), old_segments)
        actual = font.normalizeLocation({'wdth': user}).get('wdth', 0)
        if abs(actual - expected) > TOLERANCE:
            raise ValueError(f"Incorrect width mapping at user wdth={user}")


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
                if tag == "MGHT":
                    expected = desired_math_weight(WEIGHT_MIN, 50)
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
            original_width = remap_width(font, axes)
            remap_math_weight(font, axes)
            segments = copy.deepcopy(font['avar'].segments)
            # Check that unrelated tables, especially MATH/gvar, survive bytewise.
            untouched = {tag: font.getTableData(tag) for tag in font.keys()
                         if tag not in ('GlyphOrder', 'head', 'avar', 'fvar', 'STAT', 'name')}
            avar = build_avar(font, rows)
            remap_presets(font, rows, axes)
            update_stat_labels(font)
            font['avar'] = avar
            validate(font, rows, segments)
            validate_width(font, original_width)
            validate_math_weight(font)
            with tempfile.NamedTemporaryFile(prefix=f'.{destination.name}.',
                    suffix='.tmp', dir=destination.parent, delete=False) as temporary:
                temporary_name = temporary.name
            font.save(temporary_name, reorderTables=None)
        with TTFont(temporary_name, lazy=True) as saved:
            validate(saved, rows, segments)
            validate_width(saved, original_width)
            validate_math_weight(saved)
            for tag, data in untouched.items():
                if saved.getTableData(tag) != data:
                    raise ValueError(f"Unrelated table {tag} changed")
        os.replace(temporary_name, destination)
        temporary_name = None
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)
    print(f"Wrote {destination}: avar v2; automatic hidden STYA/STYB; corrected fvar/STAT presets.")
    print(f"Remapped user wdth 88 -> internal 95, 100 -> 100, 113 -> 113; preserved exported maximum.")
    print("Remapped user MGHT to 0..100 (default 50); all named instances use 50.")
    print("Updated visible-axis STAT names/values to match the guide; Regular labels are elidable.")
    print(f"Preserved other avar segment maps and all unrelated tables. CSV: {csv_path}")
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
