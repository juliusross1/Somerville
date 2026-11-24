# Validation evidence

The installed runtime consists of Lua, Python's standard library and
`skia-pathops`. FontTools is used by the development tests and PDF audits only.
`tests/test_no_fonttools.py` actively blocks FontTools imports while loading
and running the actual helper.

Performance revision 2 is now installed. Its 34 integration, predicate and
installer tests pass; the unchanged geometry helper also passed the 22 geometry
tests below. Both isolated PDF suites pass with lazy subset conversion. The
installed v2 probe in `v2/installed/` confirms three glyphs on first use, one
additional glyph on the next document, then zero helper calls for the combined
document. Its Quartz rendering was inspected.

`performance-v1-v2/` records a fair actual-letter-test comparison: compilation
with warm OTL/TrueType caches and cold corrected CFF2 caches fell from 55.56 to
9.15 seconds. Both warm runs stayed near four seconds. All 32 embedded fonts'
outlines and PDF widths matched exactly. `v2/unit-tests.log` and
`v2/installer-independent-review.log` include the new cache and upgrade tests.

The original full-font installed audit remains in `full/installed-audit.json`;
that was run under revision 1. Current deployed-file checksums and the original
pre-patch undo baseline are recorded by `installed-status.txt` and the package's
`active-install.json`.

## Automated tests

- `geometry-tests.log`: 22 tests, including 3,788 actual exported glyph
  instances. These cover all 1,553 glyphs at default and broad nondefault
  coordinates, plus 682 further glyph/axis cases. Synthetic cases cover
  winding cancellation, nested counters, self-intersections, shared edges,
  tiny counters, fractional precision, invalid input and CLI failure behavior.
- `unit-tests.log`: original revision-1 tests covering the reversible installer, Lua support
  and sfnt/TTC detection, independent winding predicates, randomized cubics,
  and operation with FontTools imports blocked.
- `v2/unit-tests.log`: 34 tests adding lazy cache growth, duplicate-index
  redirects, partial-cache preservation, generic completion, source invalidation,
  old-cache migration, unknown-glyph rejection and reversible upgrade transactions.
- `geometry-performance.json`: font checksum, measured cold CLI time and
  helper statistics. The measured full-font batch took 2.630 seconds wall
  time, with 2.456 seconds in the helper. Repeated identical outlines are
  resolved once per batch.

## End-to-end PDF tests

`small/` uses the 55-glyph CFF2 test font. `full/` uses the 1,553-glyph
Somerville export. Each directory contains frozen fixture fonts, baseline
and patched PDFs, compile logs, geometric audits and a run summary.

The fixtures have distinct test names and a corrected CFF2 FontMatrix. The
full fixture additionally maps selected size/style variants to private-use
codepoints, solely to exercise those exact glyphs in the PDF. Original exported
fonts and Glyphs packages are not edited.

Each suite tests three axis locations, ordinary text and inline/display math.
The full fixture also exercises the base circled plus, s01, s08 and s20, their
ss16 counterparts, and the two italic D glyphs that exposed a Skia numerical
failure. Broad nondefault coordinates include the additional mathematical axes.

The checks require:

- One helper batch per cold font/axis instance; no helper calls on a warm run.
- Successful conversion with `fonts.cff.flatten` enabled.
- A fatal build and no CFF2 stream-cache entry when the helper cannot launch.
- Successful rebuilding after restoring the helper configuration.
- Successful cold CFF1/TrueType builds even with an invalid helper interpreter.
- Identical CFF1/TrueType control outlines and unchanged PDF advance-width arrays.
- Patched CFF1 filled shapes matching original interpolated CFF2 reference
  outlines at the requested coordinates.

The PDF audit reads the embedded fonts independently of the helper protocol.
Raw source curves are used for point membership: simplifying the reference
with the same boolean engine would repeat the italic D failure and hide it.
The source audit is numerical and sampled; its mismatch counts are not claims
of exact analytic equality. See each `audit.json` for the measured results.

Quartz rendering of all eight full-font test pages was inspected in
`full/patched/quartz-contact.png`. The small-font text and math pages were
also inspected through Quartz. Poppler is used as a second rendering backend.

## Reproduce

From the Somerville project directory, run the unit commands in the package
README. `tests/run_e2e.py --help` describes the isolated-tree PDF harness.
The harness creates its own formats and font caches; use a disposable scratch
directory. It never installs the patch into the main ConTeXt tree.

The geometry tests and E2E harness need FontTools from
`requirements-test.txt`. Neither FontTools nor CoreGraphics is needed by the
installed conversion path.
