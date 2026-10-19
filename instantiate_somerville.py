#!/usr/bin/env python3
"""Create matching static Roman, Italic, and Math fonts.

Resolve GDEF-backed MATH variation references before fontTools instantiates
the rest of the font. This preserves variable math constants, italic
corrections, accent attachments, kerns, and assembly values in the static font.
The BASE (baseline) table is omitted by default because current Somerville
exports contain malformed baseline data. Use --keep-base to preserve it.
The input font is not modified.

Requires fontTools (tested with 4.63.0). From this directory:
    python3 instantiate_somerville.py
    python3 instantiate_somerville.py --list-instances
    python3 instantiate_somerville.py --instances "Caption Bold" INSL=100 -o CaptionBold
    python3 instantiate_somerville.py wght=700 MGHT=900 opsz=12 INSL=100 -o SomervilleBold
    python3 instantiate_somerville.py Weight=700 "Math Weight=900" "Optical Size=12"

Axes accept their case-sensitive tags or their names from the input font.
Names are case-insensitive; quote assignments containing spaces.
Current names and tags:
    Width          wdth       Weight         wght
    Math Weight    MGHT       Optical size   opsz
    ssty1          STYA       ssty2          STYB
    Arrow Length   ARLN       Arrow Head     ARHD
    Integral Slant INSL
Tags and names can be mixed, but each axis may be specified only once.

Use --list-instances to print all fvar instance names without axis values.
Use --allinstances to export every named instance in the math font's fvar table.
Use --instances "Caption Bold" to select one (names are case-insensitive).
Explicit AXIS=VALUE assignments override the selected instance's coordinates.
Instantiation warns if the corresponding Playfair instances are absent or
differ in shared axis coordinates; math coordinates remain authoritative.
Without --instances, unspecified axes use the named Regular instance. Axis overrides
are independent: changing wght does not automatically change MGHT.
Axes are read from the input font: wdth, wght, MGHT, opsz, STYA, STYB,
ARLN, ARHD, and INSL in the current SomervilleMathVF. Values are user-space
coordinates; avar remapping (including v2) is handled during instancing.
Named-instance coordinates are used exactly as stored in fvar.
PlayfairRomanVF.ttf and PlayfairItalicVF.ttf are read alongside the math input.
Both receive the resolved math wdth, wght, and opsz coordinates, including
Regular defaults for omitted axes. Each font applies its own avar mapping;
any other text-font axes (such as ital) are pinned at their defaults.

-o NAME is a path/filename prefix, not a .ttf filename.
It creates NAMERoman.ttf, NAMEItalic.ttf, and NAMEMath.ttf.
Without -o, --instances "Caption Bold" creates PlayfairRomanCaptionBold.ttf,
PlayfairItalicCaptionBold.ttf, and SomervilleMathCaptionBold.ttf.
For multiple instances with -o NAME, outputs use NAMERomanSTYLE.ttf,
NAMEItalicSTYLE.ttf, and NAMEMathSTYLE.ttf. Without either option, the prefix remains Somerville. Internal font names
are unchanged. Each font is published as soon as it is saved. Use --validate
to reopen and structurally validate each export before publishing it (off by
default). Earlier exports remain if a later export fails.
--overwrite is required if any destination exists.

Input and output paths are relative to the working directory. Use -i to
select a variable font elsewhere. Use --output-dir DIR to create and write
to a destination directory; when combined with -o, supply a filename prefix
without a directory component.
Written with ChatGPT.
"""

from contextlib import ExitStack
import argparse
import math
import os
import sys
from pathlib import Path
import tempfile

from fontTools.misc.roundTools import otRound
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables.otTables import Device, MathValueRecord
from fontTools.varLib.instancer import AxisLimits, instantiateVariableFont
from fontTools.varLib.varStore import VarStoreInstancer


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


def warn_instance_mismatch(font, path, name, math_coords, italic=False):
    """Compare stored instances before intentional command-line overrides."""
    key = name.strip().casefold()
    entries = named_instances(font)
    # Italic families conventionally append Italic, with Regular -> Italic.
    preferred = ("italic" if key == "regular" else key + " italic") if italic else key
    matches = [entry for entry in entries if preferred in entry[1]]
    if not matches and preferred != key:
        matches = [entry for entry in entries if key in entry[1]]
    if len(matches) != 1:
        reason = "no matching instance" if not matches else "multiple matching instances"
        detail = f"{reason} for {name!r}"
    else:
        label, _, coords = matches[0]
        differences = []
        for tag in ("wdth", "wght", "opsz"):
            if tag not in coords or tag not in math_coords:
                differences.append(f"{tag}: missing axis")
            elif not math.isclose(coords[tag], math_coords[tag], rel_tol=0, abs_tol=1e-5):
                differences.append(f"{tag}: Playfair={coords[tag]:g}, math={math_coords[tag]:g}")
        if not differences:
            return
        detail = f"instance {label!r} differs from math instance {name!r}: " + "; ".join(differences)
    print(f"Warning: {path.name}: {detail}. "
          "Continuing with the math coordinates plus explicit axis overrides.", file=sys.stderr)


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
    limits = AxisLimits(coordinates).limitAxesAndPopulateDefaults(font)
    location = limits.normalize(font).pinnedLocation()
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
        value = float(raw)
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


def text_coordinates(font, shared, path):
    if "fvar" not in font:
        raise ValueError(f"Input font is not variable: {path}")
    axes = {axis.axisTag: axis for axis in font["fvar"].axes}
    coords = {tag: axis.defaultValue for tag, axis in axes.items()}
    for tag in ("wdth", "wght", "opsz"):
        if tag not in axes or tag not in shared:
            raise ValueError(f"Shared axis {tag} is missing from {path} or the math font.")
        value = shared[tag]
        axis = axes[tag]
        if not axis.minValue <= value <= axis.maxValue:
            raise ValueError(f"{path.name}: {tag}={value:g} is outside "
                             f"{axis.minValue:g}..{axis.maxValue:g}.")
        coords[tag] = value
    return coords


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("axes", nargs="*", metavar="AXIS=VALUE",
                        help='Override by tag or name, e.g. wght=700 or "Math Weight=900".')
    parser.add_argument("-i", "--input", type=Path, default=Path("SomervilleMathVF.ttf"),
                        help="Input math font; Playfair variable fonts must be alongside it (default: %(default)s).")
    parser.add_argument("-o", "--output", type=Path,
                        help="Explicit prefix: NAMERoman.ttf, NAMEItalic.ttf, NAMEMath.ttf. Default with --instances: PlayfairRomanSTYLE, PlayfairItalicSTYLE, SomervilleMathSTYLE; otherwise Somerville.")
    parser.add_argument("--output-dir", type=Path, metavar="DIR",
                        help="Save fonts in DIR, creating it if needed. With this option, -o must be a filename prefix without a directory.")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--list-instances", action="store_true",
                           help="List fvar instance names only, then exit without writing fonts.")
    selection.add_argument("--instances", nargs="+", metavar="NAME",
                           help="One or more named fvar instances (case-insensitive; default: Regular). Axis overrides apply to every instance.")
    selection.add_argument("--allinstances", action="store_true",
                           help="Export every named fvar instance, using style-specific filenames. Axis overrides apply to all instances.")
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
    if args.instances is not None:
        args.axes.extend(item for item in args.instances if "=" in item)
        args.instances = [item for item in args.instances if "=" not in item]
        if not args.instances:
            parser.error("--instances requires at least one instance name")
    staged = []
    try:
        if args.list_instances:
            if args.axes:
                raise ValueError("Axis assignments cannot be combined with --list-instances.")
            with TTFont(args.input, lazy=True) as font:
                entries = named_instances(font)
                print(f"{args.input}: {len(entries)} named instances (fvar)")
                for name, _, _ in entries:
                    print(name)
            return
        if args.output is not None and args.output.suffix.lower() == ".ttf":
            raise ValueError("-o takes a prefix, not a .ttf filename; use -o Somerville.")
        if args.output_dir is not None and args.output is not None and args.output.parent != Path("."):
            raise ValueError("With --output-dir, -o must be a filename prefix without a directory.")
        inputs = [args.input.parent / "PlayfairRomanVF.ttf",
                  args.input.parent / "PlayfairItalicVF.ttf", args.input]
        requests = args.instances if args.instances is not None else ["Regular"]
        jobs = []
        with TTFont(args.input, lazy=True) as font:
            entries = named_instances(font)
            if args.allinstances:
                requests = [name for name, _, _ in entries]
                if not requests:
                    raise ValueError("Input font has no named fvar instances.")
            for requested in requests:
                shared = resolve_coordinates(font, args.axes, requested)
                canonical = next(name for name, aliases, _ in entries
                                 if requested.strip().casefold() in aliases)
                style = "".join(c for c in canonical if c.isalnum())
                if not style:
                    raise ValueError("Instance name cannot form a filename.")
                if args.output is None and (args.instances is not None or args.allinstances):
                    outputs = [Path(f"{family}{style}.ttf")
                               for family in ("PlayfairRoman", "PlayfairItalic", "SomervilleMath")]
                else:
                    prefix = args.output if args.output is not None else Path("Somerville")
                    suffix_style = style if len(requests) > 1 else ""
                    outputs = [prefix.with_name(prefix.name + suffix + suffix_style + ".ttf")
                               for suffix in ("Roman", "Italic", "Math")]
                if args.output_dir is not None:
                    outputs = [args.output_dir / output.name for output in outputs]
                jobs.append((canonical, shared, outputs))
        all_outputs = [output for _, _, outputs in jobs for output in outputs]
        if len({str(p.resolve()).casefold() for p in all_outputs}) != len(all_outputs):
            raise ValueError("Duplicate instances or colliding output filenames in this batch.")
        input_paths = {path.resolve() for path in inputs}
        for output in all_outputs:
            if output.resolve() in input_paths or any(
                output.exists() and source.exists() and os.path.samefile(output, source)
                for source in inputs
            ):
                raise ValueError(f"Output would replace an input font: {output}")
            if os.path.lexists(output) and not args.overwrite:
                raise ValueError(f"Output already exists: {output}. Use --overwrite to replace it.")
        if args.output_dir is not None:
            args.output_dir.mkdir(parents=True, exist_ok=True)
        for instance_name, shared, outputs in jobs:
            with ExitStack() as stack:
                fonts = [stack.enter_context(TTFont(path)) for path in inputs]
                for font, path in zip(fonts, inputs):
                    prepare_font(font, args.drop_base, path)
                stored = instance_coordinates(fonts[2], instance_name)
                for index in (0, 1):
                    warn_instance_mismatch(fonts[index], inputs[index], instance_name,
                                           stored, italic=index == 1)
                print(f"Selected instance: {instance_name} (explicit axis overrides applied below)")
                coordinates = [text_coordinates(fonts[0], shared, inputs[0]),
                               text_coordinates(fonts[1], shared, inputs[1]), shared]
                for font, coords, source, output in zip(fonts, coordinates, inputs, outputs):
                    print(f"{source.name}: " + " ".join(
                        f"{tag}={value:g}" for tag, value in coords.items()))
                    is_math = output == outputs[2]
                    count = instantiate_math(font, coords) if is_math or "MATH" in font else 0
                    instance = instantiateVariableFont(font, coords, inplace=True)
                    validate = validate_static_math if is_math or "MATH" in font else validate_static
                    with tempfile.NamedTemporaryFile(dir=output.parent, suffix=".ttf", delete=False) as tmp:
                        temporary = Path(tmp.name)
                    staged.append((temporary, output))
                    instance.save(temporary)
                    if args.validate:
                        with TTFont(temporary) as check:
                            validate(check)
                        print(f"Validated: {output}")
                    if is_math:
                        print(f"Resolved {count:,} MATH variation references.")
                    if args.overwrite:
                        os.replace(temporary, output)
                    else:
                        # Never replace a destination created while we were building.
                        os.link(temporary, output)
                        temporary.unlink()
                    print(f"Saved: {output}")
                    staged.pop()
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    finally:
        for temporary, _ in staged:
            temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
