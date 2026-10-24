Fenced prescript patch validation, 24 October 2026

The old engine is the previously working glyph-only patched binary. The new
engine was built with AppleClang using CMake Release and LMT_NOOPTIMIZE=ON
(disables link-time optimization, retains ordinary -O2 optimization).

old-console.log and new-console.log: 128 matching named test cases; all 64
option-disabled cases match exactly. Enabled cases test independent corners,
single-character opposite-corner additions, multi-character delimiter-only
adjustments, nesting, an invisible left delimiter, and script-style scaling.
zero-console.log and positive-console.log: 128 cases each.
assembly-console.log: 131 cases using a modified Latin Modern test font,
including forced multi-piece parentheses, square brackets, and braces.
verify_tests.py checks the numeric results using the Python standard library.
The .ttf/.otf probe fonts have deliberately modified corner data and are test
fixtures only. They were not installed over the user's fonts.

somerville-letter-test.pdf was compiled with the new engine from the copied
letter-test source. new-engine-console.log records that successful run.
luametatex is the separately built tested binary.

make_test_font.py uses the project's instantiate_somerville module and
fontTools; make_assembly_font.py uses fontTools and the local TeX Live Latin
Modern font. Generator paths record this machine's test environment.
