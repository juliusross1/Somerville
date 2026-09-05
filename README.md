# Somerville

## About
Somerville is an experimental variable Math font based on [Playfair](xxx.forthehearts.net).

****Note that Somerville is not meant to be usable as a math font for actual documents**  for at least the following reasons
- Variable math fonts are not supported, but [hopefully may be one day](https://github.com/harfbuzz/boring-expansion-spec/issues/136)
- The font is very incomplete; in particular there are very few greek letters

One option to experiment with Somerville as a math font is to use the static instances in the /fonts directory (but at the cost of losing some of the variable features).   

The variable font [MayfairVF-withMATHtable.ttf](https://github.com/juliusross1/Somerville/tree/main/test_documents/Somerville/firefox) has an artifical static MATH table which fools luaLaTeX, Firefox and Typst enough so that math is rendered (although there are limitations).   ConTeXt does not do well with SomervilleVF.ttf, even as a text font (I am not sure if ConTeXt supports avar2 and even then I think there are other issues).

On good days the following [test site](https://juliusross1.github.io/Somerville/somerville-mathml.html) shows something.  Use the arrow keys (left/right and up/down) to explore.

The goal here was to explore and in addition to this experimental font we have
- Notes on how this font was made [Creation.md](Creation.md)
- A simple tool for editing the math constants in a variable font
- Some AI-created Glyphs scripts that were used to make this font, and could be used in the future

The idea behind the above glyph scrips is that many mathematical glyphs can be created automatically (or semiautomatically) from a small number of core glyphs, which makes organizing, maintaining easier and could be used to assit creation of (variable) math compantion fonts in the future.

## Features
There are some features in Somerville that are not present in any existing math font I am aware of:
- It is a variable font with 3 axes; weight, width, optical size
- Like many math fonts, Somerville has size variants for integrals and brackets.  But Somerville also has many size variants for big operators such as summation, product, radical, coproduct, times, oplus, otimes, odot. 
- Horizontal arrows have additional variation (length, arrow head size)
- Integrals have addition variation (slant)

## About the Name
[Mary Somerville](https://en.wikipedia.org/wiki/Mary_Somerville) was a Scottish mathematician.

