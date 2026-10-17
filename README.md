# Somerville

## About
Somerville is an experimental variable mathematics font based on [Playfair](xxx.forthehearts.net).

**Note that Somerville is not meant to be usable as a math font for actual documents because...**  
- The font is very incomplete; in particular there are very few greek letters
- There are lots and lots of things that have not been done, and other bugs

This is an experiment with a variable math font.  Variable math is not an opentype sepcification (but [hopefully may be one day](https://github.com/harfbuzz/boring-expansion-spec/issues/136)).

The goal here was to explore.  In addition to this experimental font we have
- Notes on how this font was made [Creation.md](Creation.md)
- A simple tool for editing the math constants in a variable font (to be uploaded)
- Some AI-created Glyphs scripts that were used to make this font, and could be used in the future

The idea behind the above glyph scrips is that many mathematical glyphs can be created automatically (or semiautomatically) from a small number of core component glyphs, which makes organizing and maintaining easier and could be used to assit creation of math companion fonts in the future.

## Features

See the [Somerville sample] document to see some of the features, along with a description of the axes.

There are some features in Somerville that are not present in any existing math font I am aware of:
- It is a variable font with 3 axes; weight, width, optical size
- Like many math fonts, Somerville has size variants for integrals and brackets.  But Somerville also has many size variants for big operators such as summation, product, radical, coproduct, times, oplus, otimes, odot.   See the test page.
- You can make the bold letters more bold (Math Weight axis)
- Horizontal arrows have additional variation (Arrow Length axis,  Arrow Head Axis).  
- Integrals have addition variation (Integral Slant axis).

See the [test site](https://juliusross1.github.io/Somerville/somerville-mathml.html) for a demonstration.  

## Use in ConTeXt
 Variable math is supported in the most recent versions of ConTeXt.
 
```
\unexpanded\def\setupSomerville#1#2{%
  \definefontfeature[#2-math-axes]
    [axis={#1},goodies=somerville]%
  \definefontfeature[#2-text-axes][default]
    [axis={#1}]%
  \starttypescript[serif][#2-text]
    \definefontsynonym[Serif]
      [file:PlayfairRomanVF.ttf]
      [features=#2-text-axes]
    \definefontsynonym[SerifItalic]
      [file:PlayfairItalicVF.ttf]
      [features=#2-text-axes]
  \stoptypescript
  \starttypescript[math][#2]
    \definefontsynonym[MathRoman]
      [file:SomervilleMathVF.ttf]
      [features={math\mathsizesuffix,mathextra,#2-math-axes}]
  \stoptypescript
  \definetypeface[#2][rm][serif][#2-text][default]%
  \definetypeface[#2][mm][math][#2][default]%
}

% Valid ranges:
% Width: 95..113, Weight:360..900,Math Weight:0..100,Arrow Length:100..200,
% Arrow Head: 100..200, Integral Slant:0..100

\setupSomerville
  {Width=100,Weight=400,Optical Size=12,Math Weight=660,Arrow Length=200,Arrow Head=100,integral slant=0}
  {somerville-variable-math} 
\setupbodyfont[somerville-variable-math,12pt]

\starttext
Here is some text {a^2+b^2=c^2} and a formula
\startformula
\int_0^1 f(x) dx =0
\stopformula
```

## Use in other systems (e.g. LuaLaTeX)
To use SomerVille in other typesetting systems, create static fonts with the script below (requires fontTools). Place `SomervilleMathVF.ttf`, `PlayfairRomanVF.ttf`, and `PlayfairItalicVF.ttf` in the same input folder:

```sh
python3 instantiate_somerville.py "Weight=700" "Math Weight=900" \
"Optical Size=12" "Arrow Head=200" "Arrow Length=150" -o Somerville
```

which will create `SomervilleRoman.ttf`, `SomervilleItalic.ttf`, and `SomervilleMath.ttf`.   In LuaLaTeX this can be used as follows:

```
\documentclass{article}
\usepackage{unicode-math}

\setmathfont{SomervilleMath.ttf}
\setmainfont{SomervilleRoman.ttf}[ItalicFont=SomervilleItalic.ttf]
%% Bold and BoldItalics are not done just yet **fixme**
\setmathfont{SomervilleMath.ttf}

\begin{document}

Here is some text \emph{and some emphasized text}:

Inline mathematics: $a^2+b^2=c^2$, $e^{i\pi}+1=0$,
$h'(x)$, $u''(x)$, $x_{i_j}^{n+1}$, and $\sqrt{1+x^2}$.

\[
  x=\frac{-b\pm\sqrt{b^2-4ac}}{2a},
  \qquad
  \frac{1}{1+\frac{1}{1+x}},
  \qquad
  \sqrt[3]{1+\sqrt{1+x^2}}.
\]

\end{document}
```


## About the Name
[Mary Somerville](https://en.wikipedia.org/wiki/Mary_Somerville) was a Scottish mathematician.

