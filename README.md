**Playfair Math**

This records the steps taken to create a math font to pair with Playfair. The hope is that these notes may also help with other font pairings in the future.  Not all the steps need to be done in the order they appear here

*Step 1: Select a font to pair*

Things to consider include glyph coverage, existing italic and bold styles, and possible optical sizing. Existing mathematical glyphs, such as plus and minus, may also be helpful. Check the font license to make sure you can reuse it, and confirm that there is not already an existing math-font pairing available.  Go to Font->Name and change the name if appropriate.


*Step 2: Math Constants Table*
Install the Math OpenType plugin (version made by JR link). Go to Edit -> Edit Math Constants. The three-dot menu has a drop-down item for "Guess all Masters". It will make reasonable guesses for many constants. One exception may be DisplayOperatorMinHeight, which you can edit yourself or leave as zero and return to later.

Change the languages to
```
languagesystem DFLT dflt;
languagesystem math dflt;
```

*Step 3: Export Instances*

Export instances at each master coordinate. It is also useful to export several intermediate instances.

*Step 4: The MathConstants Tool*
Download and use the MathConstants tool. You will need to edit `axes-config` with the coordinates of the masters and list the fonts you want to test with. Run `server.py --help` for more help. This tool will save the math constants, which you can then insert into your Glyphs file (add more detail on how to do this).

*Step 5: Remove non-mathematics letters from the font*
Remove ligatures, these are not used in a mathematics font.

The main uppercase and lowercase latin letters for a Math font are A-Z and a-z.  Accented versions of these can be removed.  Filter "Has Components >1" and select "Uppercase letters" and you will get a view of letters that can be either deleted or set not to export (some letters may be worth keeping to be used as a template for the future; those can just be set to not export)

*Step 6: Remove or disable features*
Many font features do not make sense in a math font and can be removed or made non-active.  The following can be safely removed:

cpsp
liga
c2sc

Not sure, but I disabled
sups
subs
numr
dnom
frac

I also disable all the .lf and .tf as I do not think these are useful in a math font.


*Playfair Math Todo*
Understand what the issue is with git
Remove glyphs
Math constants and create testing documents
Minus at various widths
Glyphs3 AI plugin
Redo the existing + divide and perhaps some other glyphs
Plus at size (see how much this is used)
Times at size
Brackets and sizing
Integral and sizing and split into three pieces
Double integrals
Sum and sizing
Import Italics
Deal with Bold
Circle and sizing
Contour integral
Other display operators?
Sylistic set for sizing
Variable math font tool again (fixed weight)
See about ssty
lambda, Sigma, other math-latin letters to steal??
other simple math symbols and anchors (redo the current ones with anchors)


