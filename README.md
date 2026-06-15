**Playfair Math**

This records the steps taken to create a math font to pair with Playfair. The hope is that these notes may also help with other font pairings in the future.  Not all the steps need to be done in the order they appear here

*Step 1: Select a font to pair*

Things to consider include glyph coverage, existing italic and bold styles, and possible optical sizing. Existing mathematical glyphs, such as plus and minus, may also be helpful. Check the font license to make sure you can reuse it, and confirm that there is not already an existing math-font pairing available.  Go to Font->Name and change the name if appropriate.

*Step 2: Math Constants Table*
Install the Math OpenType plugin (version made by JR link). Go to Edit -> Edit Math Constants. The three-dot menu has a drop-down item for "Guess all Masters". It will make reasonable guesses for many constants. One exception may be DisplayOperatorMinHeight, which you can edit yourself or leave as zero and return to later.

The rulethickness will take values from the minus - glyph or underscore glyph
DisplayOperatorMinHeight will take a guess based on the integral glyph (if available)
SuperscriptShiftUp (and others) will either use the superscriptYOffset custom paramter, or information from zero.sups if the sups feature has been setup in the font.

** Accents **
Qn: What is the difference between 0302 and 02C6 for instance?
Accents need a math.ta position on them (0302,...)

*Step 3*
Change the languages to
```
languagesystem DFLT dflt;
languagesystem math dflt;
```

*Step 3: Export Instances*

Export instances at each master coordinate. It is also useful to export several intermediate instances (see next step).

*Step 4: The MathConstants Tool*
Download and use the MathConstants tool. You will need to edit `axes-config` with the coordinates of the masters and list the fonts you want to test with. Run `server.py --help` for more help. This tool will save the math constants, which you can then insert into your Glyphs file (add more detail on how to do this).

Ones to do at this point: 
Axis Height
Factions Display
Fractions Inline

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
sinf

I also disable all the .lf and .tf as I do not think these are useful in a math font.

*Step 7: Add Metrics*
It is useful to have a Math Axis metric.  You can select multiple masters to create this all at once.  It should be at the midheight of the minus glyph.  Later you may want a metric for the height of big operators, and for the height and depth of the (largest) bracket/fence, and for the height/depth of the (largest) integral operator.


*Playfair Math Todo*
Italics
Accent position (and list the unicodes) and document
Minus at various widths (need to fix this one up)
Math constants and create testing documents
Redo the existing + divide, = and many others :-(
Times at size
Brackets and sizing
Integral and sizing and split into three pieces

Longer testing document

Double integrals
Sum and sizing
Import Italics
Deal with Bold
Circle and sizing
Contour integral
Other display operators?
Sylistic set for sizing
See about ssty
lambda, Sigma, other math-latin letters to steal??
other simple math symbols and anchors (redo the current ones with anchors)


