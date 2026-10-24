#!/bin/zsh
source "$HOME/.zprofile"
set -e

glyphs export \
  --plugins "$HOME/Developer/Glyphs-MATH-Plugin/MATHPlugin.glyphsPlugin" \
  --script "$HOME/Developer/Glyphs-MATH-Plugin/glyphs-cli-bootstrap.py" \
  --config "$HOME/Documents/Somerville/sources/somerville-vf-export.json" \
  --format tt \
  --output "$HOME/Documents/fontoutputs"

cd "$HOME/Documents/Somerville/test_documents/Somerville/context"
#context somerville-letter-test.tex
#open -a Skim somerville-letter-test.pdf

 context somerville-sample.tex
 open -a Skim somerville-sample.pdf