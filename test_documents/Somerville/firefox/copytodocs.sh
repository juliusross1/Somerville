#!/bin/bash

DEST="$HOME/Documents/Somerville/docs"

mkdir -p "$DEST"

cp \
  build_missing_glyph_blocker.py \
  MissingGlyphBlocker.ttf \
  PlayfairRomanVF.ttf \
  somerville-avar-compensation.js \
  somerville-font-watcher.js \
  somerville-fraction-rule-thickness.js \
  somerville-mathml.css \
  somerville-mathml.html \
  somerville-mathml.js \
  somerville-snippets.js \
  SomervilleMATH-Regular.ttf \
  SomervilleVF-withMathtable.ttf \
  SomervilleVF.ttf \
  "$DEST/"