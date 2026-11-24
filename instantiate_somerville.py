#!/usr/bin/env python3
r"""Create static SomervilleMath fonts and matching LuaLaTeX fontspec configurations.

Description:
  Resolve GDEF-backed MATH variation references before fontTools instantiates
  the rest of the font. This preserves math constants, italic corrections,
  accent attachments, kerns, and assembly values. The input is not modified.

  The BASE table is omitted by default because current Somerville exports
  contain malformed baseline data. Use --keep-base to retain a valid table.

Instance names:
  Names follow somerville-OPTICALSIZE[-WIDTH][-WEIGHT], as in the guide.
  Names are case-insensitive. The alias somerville selects somerville-regular.
  Legacy names such as "Caption Bold" and unprefixed names such as caption-bold
  are also accepted. Available instances and coordinates come from fvar.

  Without --instance, axis values start from the named Regular instance.
  Explicit AXIS=VALUE assignments override the selected instance's coordinates.
  For a batch, overrides apply to every instance. Stored instance coordinates
  are used exactly as recorded in fvar.

Axis values:
  Values may be numbers or case-insensitive names from the guide, for example
  Weight=Bold, "Optical Size"=Micro, or "Arrow Head"=Large (200, also Largest).
  Quote assignments containing spaces. Unknown value names are rejected.
  Tags are case-sensitive; axis names are case-insensitive. An axis may be
  specified only once, even when mixing its tag and name.

  --list-axes shows visible axes, user-space ranges, font defaults, and accepted
  value names. Hidden automatic script axes are omitted. Axes are read from
  the input font, including wdth, wght, MGHT, opsz, STYA, STYB, ARLN, ARHD,
  and INSL. Coordinates are user-space values; avar remapping, including v2,
  is applied during instancing. Independent user coordinates may therefore
  produce coupled internal values.

Output files:
  -o NAME produces SomervilleMathNAME.ttf and SomervilleNAME.fontspec. For a
  batch, each instance's style is appended to NAME. Internal font names are
  unchanged. NAME may have a directory component unless --output-dir is used.

  Without -o, --instance and --allinstances use standard filenames, such as
  SomervilleMathCaptionBold.ttf and SomervilleCaptionBold.fontspec. Axis
  overrides always require -o. An export without --instance or --allinstances
  also requires -o. Neither listing option requires -o or writes files.

  The original PlayfairRomanVF.ttf and PlayfairItalicVF.ttf must be beside the
  input math font, or supplied via --playfair-dir DIR. They are read only to
  calculate matching variable text coordinates; no static Playfair fonts are
  created. Listing axes or instances does not need the Playfair files.

  Paths are relative to the working directory. Use -i to select an input font
  elsewhere. --output-dir DIR creates and uses a destination directory; when
  combining it with -o, NAME must have no directory component.

  Keep the generated pair and the two original Playfair variable fonts together
  in the LaTeX working directory or font search path. For example, after an
  export with -o Custom, use this LuaLaTeX preamble:
    \usepackage{unicode-math}
    \setmainfont{SomervilleCustom}
  fontspec loads SomervilleCustom.fontspec automatically. It configures upright,
  italic, bold, and bold italic Playfair, and selects SomervilleMathCustom.ttf
  before the document starts. Text width and optical size match mathematics;
  bold text weight matches the effective internal MGHT coordinate, including
  weight-dependent avar v2 mappings. Each Playfair avar map is inverted to find
  the appropriate user coordinates. Playfair inputs must use avar v1 or no avar.
  Playfair axis values written to the fontspec are rounded to the nearest integer.
  Text uses the HarfBuzz renderer for variable font interpolation and lining
  figures to match the mathematics font. The standard upright, italic, and
  bold mathematics alphabet commands use the SomervilleMath glyphs.

  Both filenames are checked before exports begin. Each pair is saved after
  optional font validation. Completed exports remain if a later export fails.
  --validate reopens and structurally validates the static math font before
  publication; it is off by default. --overwrite is required if either output
  file already exists.

Examples:
  Export a named instance with its automatic filename:
    python3 instantiate_somerville.py --instance somerville-caption-bold
    Output: SomervilleMathCaptionBold.ttf and SomervilleCaptionBold.fontspec

  Export all named instances with their standard filenames:
    python3 instantiate_somerville.py --allinstances --output-dir ./static-fonts

  List the available instance names:
    python3 instantiate_somerville.py --list-instances

  List axes, ranges, and named values:
    python3 instantiate_somerville.py --list-axes

  Choose a custom output name:
    python3 instantiate_somerville.py --instance somerville-micro-black -o Custom
    Output: SomervilleMathCustom.ttf and SomervilleCustom.fontspec

  Set custom axes by tag (requires -o):
    python3 instantiate_somerville.py wght=700 MGHT=100 opsz=12 INSL=100 \
      -o CustomTwo
    Output: SomervilleMathCustomTwo.ttf and SomervilleCustomTwo.fontspec

  Set custom axes by name (requires -o):
    python3 instantiate_somerville.py Weight=700 "Math Weight"=100 \
      "Optical Size"=12 -o CustomThree
    Output: SomervilleMathCustomThree.ttf and SomervilleCustomThree.fontspec

  Override a named instance using a named axis value (requires -o):
    python3 instantiate_somerville.py --instance somerville-regular-bold \
      "Arrow Head"=Large -o CustomFour
    Output: SomervilleMathCustomFour.ttf and SomervilleCustomFour.fontspec

Requirements:
  Python 3 and fontTools (tested with fontTools 4.63.0).

Credits:
  Written with ChatGPT.
"""

import argparse
import math
import os
from pathlib import Path
import tempfile
from contextlib import ExitStack

from fontTools.misc.roundTools import otRound
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables.otTables import Device, MathValueRecord
from fontTools.varLib.instancer import AxisLimits, instantiateVariableFont
from fontTools.varLib.varStore import VarStoreInstancer


AXIS_VALUE_NAMES = {
    "wdth": {"SemiCondensed": 88, "Regular": 100, "SemiExpanded": 113},
    "wght": {"SemiLight": 360, "Regular": 400, "Medium": 500,
             "SemiBold": 600, "Bold": 700, "ExtraBold": 800, "Black": 900},
    "MGHT": {"None": 0, "Lighter": 25, "Regular": 50, "Heavier": 75, "Heaviest": 100},
    "opsz": {"Micro": 5, "Minuscule": 6, "Miniature": 7, "Caption": 8,
             "Regular": 12, "SubHeading": 16, "Trumpet": 21, "Headline": 32,
             "Display": 48, "Titling": 72, "Hairline": 96, "Needlepoint": 1200},
    "INSL": {"Regular": 0, "SemiSlanted": 50, "Slanted": 100},
    "ARLN": {"Shortest": 0, "Short": 50, "Regular": 100, "Long": 150, "Longest": 200},
    "ARHD": {"Regular": 100, "Larger": 150, "Largest": 200, "Large": 200},
}


def axis_value(tag, raw):
    """Resolve a numeric value or a guide label, retaining strict validation."""
    try:
        return float(raw)
    except ValueError:
        names = AXIS_VALUE_NAMES.get(tag, {})
        normalized = "".join(raw.casefold().split()).replace("-", "").replace("_", "")
        for name, value in names.items():
            if name.casefold() == normalized:
                return value
        choices = "a number or " + ", ".join(names) if names else "a number"
        raise ValueError(f"Unknown value {raw!r} for {tag}; use {choices}.") from None


def print_axes(font):
    """Show actual user-space ranges and names accepted for this input font."""
    if "fvar" not in font:
        raise ValueError("Input font is not variable (no fvar table).")
    for axis in font["fvar"].axes:
        if axis.flags & 1:  # Automatic script axes are hidden from users.
            continue
        name = font["name"].getDebugName(axis.axisNameID) or axis.axisTag
        print(f"\n{name} ({axis.axisTag}): {axis.minValue:g}..{axis.maxValue:g}"
              f" (font default {axis.defaultValue:g})")
        choices = {name: value for name, value in AXIS_VALUE_NAMES.get(axis.axisTag, {}).items()
                   if axis.minValue <= value <= axis.maxValue}
        if not choices:
            print("  Numeric values only.")
            continue
        width = max(map(len, choices))
        seen = {}
        for label, value in choices.items():
            alias = f" (alias of {seen[value]})" if value in seen else ""
            print(f"  {label:<{width}} = {value:g}{alias}")
            seen.setdefault(value, label)


def walk_tables(root):
    """Visit each object once, including shared MATH records."""
    seen = set()
    stack = [root]
    while stack:
        obj = stack.pop()
        if isinstance(obj, (str, bytes, int, float, type(None))):
            continue
        if id(obj) in seen:
            continue
        seen.add(id(obj))
        if isinstance(obj, (list, tuple)):
            stack.extend(obj)
        elif hasattr(obj, "__dict__"):
            yield obj
            stack.extend(vars(obj).values())


def guide_instance_name(name):
    """Use the guide's somerville-OPTICALSIZE[-WIDTH][-WEIGHT] convention."""
    return "somerville-" + "-".join(name.strip().casefold().split())


def named_instances(font):
    """Return display names, localized aliases, and full fvar coordinates."""
    if "fvar" not in font:
        raise ValueError("Input font is not variable (no fvar table).")
    defaults = {axis.axisTag: axis.defaultValue for axis in font["fvar"].axes}
    result = []
    for instance in font["fvar"].instances:
        name_id = instance.subfamilyNameID
        name = font["name"].getDebugName(name_id) or f"Unnamed instance (name ID {name_id})"
        aliases = {
            record.toUnicode().strip().casefold()
            for record in font["name"].names if record.nameID == name_id
        }
        guide_name = guide_instance_name(name)
        aliases.update((name.strip().casefold(), guide_name, guide_name.removeprefix("somerville-")))
        if guide_name == "somerville-regular":
            aliases.add("somerville")
        result.append((name, aliases, {**defaults, **instance.coordinates}))
    return result


def instance_coordinates(font, name="Regular"):
    matches = [entry for entry in named_instances(font)
               if name.strip().casefold() in entry[1]]
    if not matches:
        raise ValueError(f"No named instance {name!r}. Use --list-instances to see available names.")
    if len(matches) != 1:
        raise ValueError(f"Ambiguous instance name {name!r}: {len(matches)} matches.")
    return matches[0][2].copy()


def regular_coordinates(font):
    return instance_coordinates(font, "Regular")


def normalized_coordinates(font, coordinates):
    """Use exactly the normalization used when baking the static math font."""
    return AxisLimits(coordinates).limitAxesAndPopulateDefaults(font).normalize(font).pinnedLocation()


def inverse_segment_map(value, segments):
    """Invert a monotone avar1 map, choosing the first point on a plateau."""
    points = sorted(segments.items())
    if any(a[1] > b[1] for a, b in zip(points, points[1:])):
        raise ValueError("Playfair axis mappings must be monotone.")
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if y0 <= value <= y1:
            return x0 if y0 == y1 else x0 + (value - y0) * (x1 - x0) / (y1 - y0)
    raise ValueError(f"Cannot match internal text coordinate {value:g}.")


def matching_text_coordinates(font, location, bold=False):
    """Match design-space wdth/opsz, and wght (upright) or MGHT (bold).

    Somerville and Playfair share the underlying design scales. Their user
    coordinates can differ, notably for width, so invert each text font's avar.
    """
    if "fvar" not in font:
        raise ValueError("Playfair inputs must be variable fonts.")
    if "avar" in font and font['avar'].majorVersion != 1:
        raise ValueError("Matching Playfair text currently requires avar v1 mappings.")
    axes = {a.axisTag: a for a in font['fvar'].axes}
    coordinates = {tag: a.defaultValue for tag, a in axes.items()}
    for tag in ('wdth', 'wght', 'opsz'):
        if tag not in axes:
            raise ValueError(f"Playfair font is missing the {tag} axis.")
        source = 'MGHT' if bold and tag == 'wght' else tag
        if source not in location:
            raise ValueError(f"Math font is missing the {source} axis.")
        target = location[source]
        segments = font['avar'].segments[tag] if 'avar' in font else {-1: -1, 0: 0, 1: 1}
        normalized = inverse_segment_map(target, segments)
        a = axes[tag]
        span = a.defaultValue - a.minValue if normalized < 0 else a.maxValue - a.defaultValue
        coordinates[tag] = a.defaultValue + normalized * span
    actual = font.normalizeLocation(coordinates)
    for tag in ('wdth', 'wght', 'opsz'):
        source = 'MGHT' if bold and tag == 'wght' else tag
        if abs(actual.get(tag, 0) - location[source]) > 2 / 16384:
            raise ValueError(f"Playfair cannot match the math font's internal {source} coordinate.")
    return coordinates


def fontspec_contents(family, math_filename, text_coordinates, coordinates):
    """A standard fontspec family configuration, plus deferred math setup."""
    if any(c in family + math_filename for c in '\\{}%#[],\n\r'):
        raise ValueError("Output names contain characters that cannot be used in a fontspec configuration.")
    if any(c.isspace() for c in family):
        raise ValueError("Output names for fontspec configurations must not contain whitespace.")
    lines = [
        '% Generated by instantiate_somerville.py.',
        '% Keep this file, the math font, PlayfairRomanVF.ttf, and PlayfairItalicVF.ttf together.',
        '% LuaLaTeX preamble:',
        r'%   \usepackage{unicode-math}',
        rf'%   \setmainfont{{{family}}}',
        '% Math user coordinates: ' + ', '.join(f'{k}={v:g}' for k, v in coordinates.items()),
        rf'\defaultfontfeatures[{family}]{{',
        '  Renderer=HarfBuzz,',
        '  Numbers=Lining,',
    ]
    for shape, filename in [('Upright', 'PlayfairRomanVF.ttf'), ('Italic', 'PlayfairItalicVF.ttf'),
                            ('Bold', 'PlayfairRomanVF.ttf'), ('BoldItalic', 'PlayfairItalicVF.ttf')]:
        axes = ','.join(f'{tag}={round(value)}' for tag, value in text_coordinates[shape].items())
        lines.extend([f'  {shape}Font={{{filename}}},',
                      f'  {shape}Features={{RawAxis={{{axes}}}}},'])
    lines.extend(['}', '% Set math after fontspec has finished loading this text family.',
                  rf'\AddToHook{{begindocument/before}}[{family}]{{%',
                  r'  \unimathsetup{mathrm=sym,mathit=sym,mathbf=sym}%',
                  rf'  \setmathfont{{{math_filename}}}%', '}', ''])
    return '\n'.join(lines)


def instantiate_math(font, coordinates):
    """Bake this font's GDEF-backed MATH VariationIndex records into integers.

    Do this BEFORE ordinary instancing removes/remaps the GDEF variation store.
    Use the same normalization as the outline instancer, including avar v2.
    Ordinary pixel-size Device tables are preserved.
    """
    if "MATH" not in font:
        raise ValueError("Input font has no MATH table.")
    records = [
        obj for obj in walk_tables(font["MATH"].table)
        if isinstance(obj, MathValueRecord)
        and obj.DeviceTable is not None
        and obj.DeviceTable.DeltaFormat == 0x8000
    ]
    if not records:
        return 0
    store = getattr(font["GDEF"].table, "VarStore", None) if "GDEF" in font else None
    if store is None:
        raise ValueError("MATH has variation references but GDEF has no variation store.")
    location = normalized_coordinates(font, coordinates)
    instancer = VarStoreInstancer(store, font["fvar"].axes, location)
    for record in records:
        device = record.DeviceTable
        index = (device.StartSize << 16) | device.EndSize
        # 0xFFFFFFFF is the OpenType no-variation sentinel.
        if index != 0xFFFFFFFF:
            outer, inner = device.StartSize, device.EndSize
            if outer >= len(store.VarData) or inner >= store.VarData[outer].ItemCount:
                raise ValueError(f"MATH references an invalid variation index: {index:#x}")
        value = otRound(record.Value + instancer[index])
        if not -32768 <= value <= 32767:
            raise ValueError(f"Instantiated MATH value is outside int16 range: {value}")
        record.Value = value
        record.DeviceTable = None
    return len(records)


def validate_static(font):
    font.ensureDecompiled()
    if "fvar" in font or "gvar" in font or "avar" in font:
        raise ValueError("Output still contains variable-font tables.")


def validate_static_math(font):
    validate_static(font)
    if "MATH" not in font:
        raise ValueError("Output lost its MATH table.")
    for obj in walk_tables(font["MATH"].table):
        if isinstance(obj, Device) and obj.DeltaFormat == 0x8000:
            raise ValueError("Output MATH still contains an unresolved variation reference.")


def resolve_coordinates(font, assignments, instance_name="Regular"):
    coordinates = instance_coordinates(font, instance_name)
    axes = {axis.axisTag: axis for axis in font["fvar"].axes}
    names = {}
    labels = []
    for tag, axis in axes.items():
        name = font["name"].getDebugName(axis.axisNameID)
        labels.append(f"{tag} ({name})" if name else tag)
        if name:
            names.setdefault(name.strip().casefold(), set()).add(tag)
    supplied = set()
    for item in assignments:
        key, separator, raw = item.partition("=")
        key = key.strip()
        matches = {key} if key in axes else names.get(key.casefold(), set())
        if not separator or not matches:
            raise ValueError(f"Invalid axis assignment {item!r}; axes: {', '.join(labels)}")
        if len(matches) != 1:
            raise ValueError(f"Ambiguous axis name {key!r}; use a tag: {', '.join(sorted(matches))}")
        tag = next(iter(matches))
        if tag in supplied:
            raise ValueError(f"Axis {tag} was specified twice.")
        supplied.add(tag)
        value = axis_value(tag, raw)
        axis = axes[tag]
        if not math.isfinite(value) or not axis.minValue <= value <= axis.maxValue:
            raise ValueError(f"{tag} must be between {axis.minValue:g} and {axis.maxValue:g}.")
        coordinates[tag] = value
    for tag, value in coordinates.items():
        axis = axes[tag]
        if not math.isfinite(value) or not axis.minValue <= value <= axis.maxValue:
            raise ValueError(f"{tag} must be between {axis.minValue:g} and {axis.maxValue:g}.")
    return coordinates


def prepare_font(font, drop_base, path):
    if drop_base and "BASE" in font:
        del font["BASE"]
        print(f"Dropped BASE: {path.name}")
    for tag in font.keys():
        if tag == "GlyphOrder":
            continue
        try:
            table = font[tag]
            if hasattr(table, "ensureDecompiled"):
                table.ensureDecompiled()
        except Exception as exc:
            hint = " Use --drop-base to omit this table." if tag == "BASE" else ""
            raise ValueError(f"Cannot decode {path} {tag} table: {exc}.{hint}") from exc


def main():
    description, _, details = __doc__.strip().partition("\n\n")
    parser = argparse.ArgumentParser(
        description=description,
        epilog=details,
        usage="%(prog)s [OPTIONS] [AXIS=VALUE ...]",
        formatter_class=lambda prog: argparse.RawDescriptionHelpFormatter(
            prog, width=88, max_help_position=30),
    )
    parser.add_argument("axes", nargs="*", metavar="AXIS=VALUE",
                        help='Override an axis by tag or name, using a number or label (e.g. wght=700 or "Arrow Head"=Large).')
    parser.add_argument("-i", "--input", type=Path, metavar="FONT", default=Path("SomervilleMathVF.ttf"),
                        help="Input variable math font (default: %(default)s).")
    parser.add_argument("-o", "--output", type=Path, metavar="NAME",
                        help="Output name: SomervilleMathNAME.ttf and SomervilleNAME.fontspec. Required for axis overrides or when no instance selection is given.")
    parser.add_argument("--playfair-dir", type=Path, metavar="DIR",
                        help="Read the original Playfair variable fonts from DIR (default: beside the input math font).")
    parser.add_argument("--output-dir", type=Path, metavar="DIR",
                        help="Save font/configuration pairs in DIR, creating it if needed. With this option, -o must have no directory component.")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--list-axes", action="store_true",
                           help="List visible axis ranges and accepted value names, then exit without writing fonts.")
    selection.add_argument("--list-instances", action="store_true",
                           help="List guide-style instance names only, then exit without writing fonts.")
    selection.add_argument("--instance", nargs="+", metavar="NAME",
                           help="Select named instances (case-insensitive). Axis overrides apply to every instance.")
    selection.add_argument("--allinstances", action="store_true",
                           help="Export every named fvar instance. Uses standard filenames unless -o is given; axis overrides require -o.")
    parser.add_argument("--validate", action="store_true",
                        help="Reopen and structurally validate each saved font before publishing it (default: off).")
    parser.add_argument("--overwrite", action="store_true",
                        help="Allow replacing an existing output file (default: refuse).")
    base_options = parser.add_mutually_exclusive_group()
    base_options.add_argument("--drop-base", action="store_true", default=True,
                              help="Omit the BASE table (default).")
    base_options.add_argument("--keep-base", action="store_false", dest="drop_base",
                              help="Preserve the BASE table; it must be valid.")
    args = parser.parse_args()
    # nargs='+' also consumes trailing AXIS=VALUE tokens; retain that familiar syntax.
    if args.instance is not None:
        args.axes.extend(item for item in args.instance if "=" in item)
        args.instance = [item for item in args.instance if "=" not in item]
        if not args.instance:
            parser.error("--instance requires at least one instance name")
    staged = []
    try:
        if args.list_axes:
            if args.axes:
                raise ValueError("Axis assignments cannot be combined with --list-axes.")
            with TTFont(args.input, lazy=True) as font:
                print(f"{args.input}: axis ranges (user coordinates)")
                print_axes(font)
            return
        if args.list_instances:
            if args.axes:
                raise ValueError("Axis assignments cannot be combined with --list-instances.")
            with TTFont(args.input, lazy=True) as font:
                entries = named_instances(font)
                print(f"{args.input}: {len(entries)} named instances (fvar)")
                for name, _, _ in entries:
                    print(guide_instance_name(name))
            return
        if args.output is None and (args.axes or (args.instance is None and not args.allinstances)):
            raise ValueError("-o is required unless --instance or --allinstances is supplied without axis overrides.")
        if args.output is not None and args.output.suffix.lower() == ".ttf":
            raise ValueError("-o takes a name, not a .ttf filename; use -o Custom.")
        if args.output_dir is not None and args.output is not None and args.output.parent != Path("."):
            raise ValueError("With --output-dir, -o must be a name without a directory.")
        requests = args.instance if args.instance is not None else ["somerville-regular"]
        playfair_dir = args.playfair_dir if args.playfair_dir is not None else args.input.parent
        text_paths = {'Roman': playfair_dir / 'PlayfairRomanVF.ttf',
                      'Italic': playfair_dir / 'PlayfairItalicVF.ttf'}
        jobs = []
        with ExitStack() as stack:
            font = stack.enter_context(TTFont(args.input, lazy=True))
            text_fonts = {key: stack.enter_context(TTFont(path, lazy=True)) for key, path in text_paths.items()}
            entries = named_instances(font)
            if args.allinstances:
                requests = [name for name, _, _ in entries]
                if not requests:
                    raise ValueError("Input font has no named fvar instances.")
            for requested in requests:
                coordinates = resolve_coordinates(font, args.axes, requested)
                canonical = next(name for name, aliases, _ in entries
                                 if requested.strip().casefold() in aliases)
                style = "".join(c for c in canonical if c.isalnum())
                if not style:
                    raise ValueError("Instance name cannot form a filename.")
                if args.output is None:
                    output = Path(f"SomervilleMath{style}.ttf")
                    family = f"Somerville{style}"
                else:
                    prefix = args.output
                    suffix_style = style if len(requests) > 1 else ""
                    family = 'Somerville' + prefix.name + suffix_style
                    output = prefix.with_name('SomervilleMath' + prefix.name + suffix_style + '.ttf')
                if args.output_dir is not None:
                    output = args.output_dir / output.name
                setup = output.with_name(family + '.fontspec')
                location = normalized_coordinates(font, coordinates)
                text_axes = {
                    'Upright': matching_text_coordinates(text_fonts['Roman'], location),
                    'Italic': matching_text_coordinates(text_fonts['Italic'], location),
                    'Bold': matching_text_coordinates(text_fonts['Roman'], location, bold=True),
                    'BoldItalic': matching_text_coordinates(text_fonts['Italic'], location, bold=True),
                }
                contents = fontspec_contents(family, output.name, text_axes, coordinates)
                jobs.append((canonical, coordinates, output, setup, contents))
        all_outputs = [path for _, _, output, setup, _ in jobs for path in (output, setup)]
        if len({str(p.resolve()).casefold() for p in all_outputs}) != len(all_outputs):
            raise ValueError("Duplicate instances or colliding output filenames in this batch.")
        for output in all_outputs:
            inputs = [args.input, *text_paths.values()]
            if any(output.resolve() == source.resolve() or (
                output.exists() and os.path.samefile(output, source)
            ) for source in inputs):
                raise ValueError(f"Output would replace an input font: {output}")
            if os.path.lexists(output) and not args.overwrite:
                raise ValueError(f"Output already exists: {output}. Use --overwrite to replace it.")
        if args.output_dir is not None:
            args.output_dir.mkdir(parents=True, exist_ok=True)
        for instance_name, coordinates, output, setup, contents in jobs:
            with TTFont(args.input) as font:
                prepare_font(font, args.drop_base, args.input)
                print(f"Selected instance: {guide_instance_name(instance_name)} (explicit axis overrides applied below)")
                print(f"{args.input.name}: " + " ".join(
                    f"{tag}={value:g}" for tag, value in coordinates.items()))
                count = instantiate_math(font, coordinates)
                instance = instantiateVariableFont(font, coordinates, inplace=True)
                with tempfile.NamedTemporaryFile(dir=output.parent, suffix=".ttf", delete=False) as tmp:
                    temporary = Path(tmp.name)
                staged.append((temporary, output))
                instance.save(temporary)
                with tempfile.NamedTemporaryFile(dir=setup.parent, suffix='.fontspec',
                                                 mode='w', encoding='utf-8', delete=False) as tmp:
                    temporary_setup = Path(tmp.name)
                    staged.append((temporary_setup, setup))
                    tmp.write(contents)
                if args.validate:
                    with TTFont(temporary) as check:
                        validate_static_math(check)
                    print(f"Validated: {output}")
                print(f"Resolved {count:,} MATH variation references.")
                published = []
                try:
                    for temporary_path, destination in ((temporary, output), (temporary_setup, setup)):
                        if args.overwrite:
                            os.replace(temporary_path, destination)
                        else:
                            # Never replace a destination created while building.
                            os.link(temporary_path, destination)
                            published.append(destination)
                            temporary_path.unlink()
                except OSError:
                    # Roll back a newly published pair if its second file failed.
                    for destination in published:
                        destination.unlink(missing_ok=True)
                    raise
                print(f"Saved: {output}")
                print(f"Saved: {setup}")
                del staged[-2:]
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    finally:
        for temporary, _ in staged:
            temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
