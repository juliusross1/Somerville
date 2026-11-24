# CFF2 overlap conversion for ConTeXt LMTX

This local patch preserves the filled appearance of instantiated CFF2 glyphs
when ConTeXt embeds them as CFF1 in a PDF. It resolves the whole compound outline
using nonzero winding after variation interpolation, then encodes the resulting
boundaries as cubic CFF1 paths. It does not edit any font or Glyphs source.

Status: applied to `/Users/juliusross/context/tex` on 15 November 2026, with the
English format rebuilt. The installed-tree PDF audit passed. Exact backups and
the active checksums are recorded in `active-install.json`. Application details
and test evidence are under `validation/`.

The motivating example is Somerville's n-ary circled plus: overlapping bars and
a ring produced white cut-outs in macOS's Quartz PDF renderer. Decomposing
components does not resolve those overlaps.

## Scope

The patch changes two existing files in `texmf-context/tex/context/base/mkxl`:

- `font-cff.lmt`: collect interpolated CFF2 outlines during PDF stream creation,
  batch-resolve their winding, and replace changed charstrings.
- `font-shp.lmt`: use a distinct stream-cache key only for fonts whose sfnt table
  directory contains `CFF2`. Existing CFF1, TrueType and Type 1 cache keys remain
  unchanged.

Three support files are installed beside them: `font-cff-overlaps.lua`,
`font-cff-overlaps.py`, and `font-cff-overlaps-config.json`. The English format
is rebuilt so that the changed Lua code is loaded. The engine binary, math
layout, metrics, font features, and existing prescript/hinting patches are not
changed by this patch.

`original/` contains the exact local baseline; `patched/` contains the proposed
sources. `context-cff2-overlaps.patch` is the corresponding unified diff, with
paths relative to the ConTeXt `tex` directory. Use the installer rather than
applying just the diff: the support files and rebuilt format are required.

## Dependencies and behavior

The runtime helper uses Python and `skia-pathops` (tested with 0.9.2). FontTools
(tested with 4.63.0) is a development/test dependency only; it is not imported
or required by the installed patch. The
installer defaults to this project's `sources/venv/bin/python`, which already
has that dependency. Keep that environment available, or supply another Python
with `--python /absolute/path/to/python`.
Runtime dependencies are listed in `requirements.txt`; test dependencies are
listed separately in `requirements-test.txt`. CoreGraphics is not used.

One helper process handles all glyph outlines for an uncached font/axis
instance. Subsequent builds reuse ConTeXt's stream cache. A helper call is not
made for each occurrence of a character. The log reports the number of glyphs,
the number changed, and the helper's geometry-processing time. This time excludes
Python startup, JSON transfer and ConTeXt parsing.

Every proposed outline is checked with a separate, standard-library Python
point-in-path implementation against the original nonzero-filled compound path, using both fill rules
on the output. Failed candidates are retried with conditioned coordinate origins;
if no candidate passes, the build stops. These are finite numerical checks,
not a proof for every possible malformed or degenerate outline. Broad-axis tests
caught two italic D cases where Skia's own boolean checks missed a lost contour;
the independent checks reject those candidates and the conditioned retry passes.

Unchanged glyphs retain their original charstrings. Rewritten glyphs are emitted
without their previous hint masks, because those masks refer to the old segment
positions. This patch does not regenerate hints. Fractional outlines can be
rewritten to avoid retaining sub-float32 overlaps even when their topology
looks unchanged after quantization. PathOps uses float32 geometry;
changed outlines acquire its intersection-coordinate precision before the
existing CFF1 encoder's 16.16 encoding. Curves remain cubic; there is no polygon
or quadratic approximation stage. Read the validation results for the measured
effects on the fixtures.

Rewritten glyphs retain the interpolated fractional coordinates. The previous
CFF2 fast stream path rounded relative deltas to integers, so intermediate-axis
outlines may also become more accurate. Validation therefore uses the original
interpolated CFF2 outlines as its geometric reference, rather than requiring
rewritten glyphs to reproduce the old rounding.

ConTeXt must be able to launch the Python helper on a cold stream-cache build.
Conversion errors stop the build rather than silently embedding the original
overlapping outline. `CONTEXT_CFF2_OVERLAPS_PYTHON` can override the configured
interpreter. Normal builds need no new TeX commands or font features.

## Apply, inspect and undo

From the Somerville project directory:

```sh
python3 "context patch/cff2-overlaps/manage.py" apply
python3 "context patch/cff2-overlaps/manage.py" status
python3 "context patch/cff2-overlaps/manage.py" undo
```

The default tree is `/Users/juliusross/context/tex`. To test another tree:

```sh
python3 "context patch/cff2-overlaps/manage.py" apply --context-tree /path/to/context/tex
```

Only one installation is tracked at a time. The installer verifies the two
baseline source hashes, checks dependencies, saves backups and checksums, copies
the patch, and rebuilds `cont-en`. If rebuilding fails, it restores the previous
files. The active record is `active-install.json`; backups are under `backups/`.

Undo restores the exact previous source and English-format files and removes
only the support files introduced by this installation. It does not rebuild
formats, remove font caches, or touch the font source. The original cache keys
automatically become active again. If any tracked file was edited or the format
rebuilt after application, undo refuses to overwrite it; inspect the recorded
backup and reconcile those later changes first. Keep the installation record
and backups until you no longer need undo.

## Tests

```sh
sources/venv/bin/python "context patch/cff2-overlaps/test_geometry.py"
sources/venv/bin/python -m unittest discover -s "context patch/cff2-overlaps/tests" -p 'test_*.py'
```

The geometry tests exercise compound-path fill semantics and actual Somerville
outlines. The independent PDF audit compares baseline CFF2-derived nonzero-filled
regions with the patched embedded CFF1 even-odd-filled regions, checks widths,
and requires unchanged CFF1 and TrueType control outlines. End-to-end fixtures
and evidence are documented in `validation/`.

This is a local patch against the captured source versions, not a general
installer for arbitrary ConTeXt releases. Rebase and rerun the tests before
applying it to a different baseline.
