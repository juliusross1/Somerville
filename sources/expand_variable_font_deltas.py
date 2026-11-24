"""Work around ConTeXt's sparse gvar interpolation by writing explicit deltas.

Only the exported font is changed. IUP reconstructs omitted point deltas from
the default outlines; explicit values are rounded to TrueType's integer units.
Composite tuples are left alone because their omitted offsets mean zero.
"""
import os
from pathlib import Path
import sys
import tempfile
from time import perf_counter

from fontTools.misc.roundTools import otRound
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables.DefaultTable import DefaultTable
from fontTools.varLib.iup import iup_delta


def expand_deltas(path):
    started = perf_counter()
    path = Path(path)
    count = 0
    with TTFont(path, recalcBBoxes=False, recalcTimestamp=False) as font:
        if "gvar" not in font or "glyf" not in font:
            raise ValueError("Expected a variable TrueType font: " + str(path))
        original = {tag: font.reader[tag] for tag in font.reader.tables
                    if tag not in {"head", "gvar"}}
        glyf = font["glyf"]
        for name, variations in font["gvar"].variations.items():
            if glyf[name].isComposite():
                continue
            coordinates = controls = None
            for variation in variations:
                if not any(delta is None for delta in variation.coordinates):
                    continue
                if coordinates is None:
                    coordinates, controls = glyf._getCoordinatesAndControls(
                        name, font["hmtx"].metrics)
                variation.coordinates = [
                    (otRound(x), otRound(y)) for x, y in iup_delta(
                        variation.coordinates, coordinates, controls.endPts)
                ]
                count += 1
        if count:
            # Compile while fvar/glyf still expose their structured data, then
            # preserve every other table byte-for-byte (apart from checksum).
            tables = dict(original, gvar=font["gvar"].compile(font))
            for tag, data in tables.items():
                table = DefaultTable(tag)
                table.data = data
                font[tag] = table
            fd, temporary = tempfile.mkstemp(
                prefix=path.stem + "-deltas-", suffix=".ttf", dir=path.parent)
            os.close(fd)
            try:
                font.save(temporary, reorderTables=None)
                with TTFont(temporary, lazy=True) as checked:
                    for tag, data in original.items():
                        if checked.reader[tag] != data:
                            raise ValueError("Unexpected change to table: " + tag)
                os.replace(temporary, path)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
    print("Expanded %i sparse variation tuples; %.3f seconds." % (
        count, perf_counter() - started))
    return count


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: expand_variable_font_deltas.py EXPORTED_FONT.ttf")
    expand_deltas(sys.argv[1])
