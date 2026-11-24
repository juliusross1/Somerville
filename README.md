# Somerville

## About
Somerville is an experimental variable mathematics font based on [Playfair](xxx.forthehearts.net).

**Note that Somerville is not meant to be usable as a math font for actual documents because...**  
- The font is very incomplete; in particular there are very few greek letters
- There are lots and lots of things that have not been done, and other bugs

This is an experiment with a variable math font.  Variable math is not an opentype sepcification (but [hopefully may be one day](https://github.com/harfbuzz/boring-expansion-spec/issues/136)).

The goal here was to explore.  In addition to this experimental font we have
- Notes on how this font was made [Creation.md](Creation.md)
- Some AI-created Glyphs scripts that were used to make this font, and could be used in the future

The idea behind the above glyph scrips is that many mathematical glyphs can be created automatically (or semiautomatically) from a small number of core component glyphs, which makes organizing and maintaining easier and could be used to assit creation of math companion fonts in the future.

## Features
There are some features in Somerville that are not present in any existing math font I am aware of:
- It is a variable font with 3 axes; weight, width, optical size
- Like many math fonts, Somerville has size variants for integrals and brackets.  But Somerville also has many size variants for big operators such as summation, product, radical, coproduct, times, oplus, otimes, odot. 
- You can make the mathematics bold letters heavier or lighter (Math Weight axis)
- Horizontal arrows have additional variation (Arrow Length,  Arrow Head).  
- Integrals have addition variation (Integral Slant axis).

## Guide


## Sample Documents

## Building a naryunion proof

Run `sources/build.sh --bigoperators-only` to export a reduced proofing font before
the usual axis conversion, ConTeXt build, and Skim preview. The separate
`sources/naryunion_prefilter.py` runs inside the Glyphs CLI and only changes its
in-memory font; it never saves the source package. It retains the source's
exporting letters and numerals, `= + −`, round union/intersection and their n-ary forms,
the n-ary square union/intersection, all their size and ss15 variants, recursive
components, and space/.notdef where present. Small square union/intersection
are retained if present in the source (currently they are absent). Other numbers and symbols are
removed from the CLI's in-memory font before variable export, so Glyphs avoids
preparing their outlines. They are never removed from the source package.
Documents testing those glyphs will show missing characters or fallbacks.
Feature substitutions referring to omitted glyphs are removed; unsupported
complex features are disabled for this proofing mode. Running `sources/build.sh`
without the option follows the normal export path.
The letter test disables math expansion because its default vector assumes
omitted symbols exist. This also allows direct editor builds with a reduced font.

For an even smaller variable proof, use `sources/build.sh --union-only`. It also
excludes letters, retaining only the union family, its components, and font
infrastructure. Other math in the sample will be missing or use fallbacks.
Both subset modes preserve all masters and variable axes, and keep autohinting.
After axis conversion, `sources/fix_variable_font_bounds.py` expands the generated
TTF's `head` bounding box to enclose variable outlines. This prevents ConTeXt/PDF
clipping of wide instances (notably the largest union), without changing glyph
outlines, advances, or variation data. The calculation includes sparse gvar
deltas and component transforms; it does not modify the Glyphs source.

Filter checks: `sources/venv/bin/python -m unittest discover -s sources -p test_naryunion_prefilter.py`.


## About the Name
[Mary Somerville](https://en.wikipedia.org/wiki/Mary_Somerville) was a Scottish mathematician.


Batch instantiation validates all requested names before generating fonts. An unknown name stops the command with an error and no output fonts are published. Axis overrides apply to every selected instance. For multiple instances, `-o NAME` produces `SomervilleMathNAMESTYLE.ttf` and `SomervilleNAMESTYLE.fontspec`. Without `-o`, `--allinstances` uses the standard instance names.

Use `--output-dir DIR` to save the generated fonts in a directory, which is created if needed. It works with individual instances, batches, and `--allinstances`. When combining it with `-o`, use a name without a directory, for example `--output-dir ./static-fonts -o Custom`.

Output validation is optional: add `--validate` to reopen and check each saved font before publishing it. Each export receives its final filename immediately after saving (and validation, if enabled). Completed exports remain if a later export fails. Input checks, MATH variation resolution, and overwrite protection always apply.
