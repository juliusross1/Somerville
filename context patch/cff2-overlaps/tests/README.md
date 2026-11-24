# Integration checks

Run with a Python containing `fonttools` and `skia-pathops`. FontTools is a
validation dependency: the runtime helper itself needs only Python and
`skia-pathops`.

The runner copies the input ConTeXt tree to a new scratch directory, builds its
own formats and caches, and never installs anything in the input tree. It
constructs fixture copies of the supplied font; the supplied font is read only.

From the Somerville project directory:

```sh
sources/venv/bin/python 'context patch/cff2-overlaps/tests/run_e2e.py' \
  --tree /Users/juliusross/context/tex \
  --scratch /tmp/somerville-cff2-reproduction \
  --output 'context patch/cff2-overlaps/validation/reproduction' \
  --source /Users/juliusross/Documents/fontoutputs/SomervilleMathVF.otf
```

The scratch directory must not exist. To rerun after changing only the helper,
use the same arguments with `--resume --refresh-helper`. That clears only CFF2
stream entries in the disposable clone, copies the helper again, and repeats the
cold, warm, flattening, failure, recovery and control checks. Without
`--refresh-helper`, `--resume` retains an already completed cold run and resumes
the audits.

## Coverage

* Actual embedded CFF1 outlines at default, intermediate and extreme locations.
  The full fixture's intermediate location varies all nine axes, with values
  clamped to the font's declared ranges.
* A, U, V and the n-ary circled plus in ordinary text; inline and display math.
* In the full font, explicit fixture-only private Unicode mappings exercise
  base, s01, s08 and s20 circled-plus glyphs and their ss16 counterparts, plus
  italic D and bold italic D. These mappings avoid ambiguity in math variant
  size numbering and do not alter any design source or production font.
* Each fixture is also exported locally as CFF1 and TrueType. Their embedded
  glyph contours must remain byte-for-byte equivalent as recorded operations.
  All PDF advance-width arrays must match the baseline.
* Original CFF2 outlines are independently interpolated using FontTools, including
  axis mapping. Their original double-coordinate cubic paths are compared with
  the embedded CFF1 using a standalone ray-winding predicate: nonzero fill on the
  reference, even-odd fill on the embedded font, on a 96 by 96 grid per glyph.
  Neither a Skia boolean operation nor Skia point classification is used for this
  final comparison. Fixture glyph IDs are matched to an explicit expected list.
* Three cold helper calls for the three actually used font instances; only
  requested glyphs are converted. No helper calls for a warm cache.
* `fonts.cff.flatten` enabled with cold font names.
* A missing helper interpreter must give a nonzero exit and leave no CFF2 stream
  cache entry; a subsequent correctly configured run must succeed.
* Cold CFF1 and TrueType fonts must work with a deliberately missing helper
  interpreter, proving the dependency is confined to CFF2.
* Incremental documents request U, then V, then UV at one location. The helper
  must receive only `.notdef` and U, then only V, then nothing. Previously
  corrected U/V outlines must remain unchanged. A generic font-stream consumer
  must then fill only missing glyphs and receive a complete font; a subsequent
  partial consumer must use that full cache without a helper call.
* When rerunning in a clone that has genuine complete v1 stream caches, those
  caches are saved before the cold test and restored for a v1-to-v2 promotion
  test. Promotion must require no helper call and must pass the same PDF audit.
  A fresh clone has no v1 cache; mocked cache tests cover promotion in that case.

`run-summary.json` records the helper hash, call counts and result. Numeric
reports are in `audit.json`, `flatten-audit.json` and `recovery-audit.json`.
Incremental and promotion checks have separate `incremental-audit.json` and,
when applicable, `v1-promotion-audit.json` reports. `final-v2-source-check.json`
records a final warm run and hashes after the final source guards were copied.
The PDFs and individual logs remain in `baseline/` and `patched/`. A
`failure-negative.console.log` documents the expected failure; `failure.pdf`
and `recovery.console.log` are the subsequent successful recovery.

The generated TeX files use relative `../fixtures/` paths, so they can also be
rerun from their own `baseline` or `patched` directories. Visual PDF rendering is
an additional check; it is not part of the runtime patch or a runtime dependency.
