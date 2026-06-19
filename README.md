**Playfair Math**

This records the steps taken to create a math font to pair with Playfair. The hope is that these notes may also help with other font pairings in the future.  Not all the steps need to be done in the order they appear here

*Step 1: Select a font to pair*

Things to consider include glyph coverage, existing italic and bold styles, and possible optical sizing. Existing mathematical glyphs, such as plus and minus, may also be helpful. Check the font license to make sure you can reuse it, and confirm that there is not already an existing math-font pairing available.  Go to Font->Name and change the name if appropriate.

*Step 2*
Change the languages to
```
languagesystem DFLT dflt;
languagesystem math dflt;
```

*Step 3: Remove non-mathematics letters from the font*
Remove ligatures, these are not used in a mathematics font.

The main uppercase and lowercase latin letters for a Math font are A-Z and a-z.  Accented versions of these can be removed.  Filter "Has Components >1" and select "Uppercase letters" and you will get a view of letters that can be either deleted or set not to export (some letters may be worth keeping to be used as a template for the future; those can just be set to not export)

I also disable all the .lf and .tf as I do not think these are useful in a math font.

*Step 4: Remove or disable features*
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


*Step 5: Export Instances*

Export instances at each master coordinate. It is also useful to export several intermediate instances (see next step).

*Step 6: Math Constants Table*
Install the Math OpenType plugin (version made by JR link). Go to Edit -> Edit Math Constants. The three-dot menu has a drop-down item for "Guess all Masters". It will make reasonable guesses for many constants. One exception may be DisplayOperatorMinHeight, which you can edit yourself or leave as zero and return to later.

The rulethickness will take values from the minus glyph or underscore glyph
DisplayOperatorMinHeight will take a guess based on the integral glyph (if available)
SuperscriptShiftUp (and others) will either use the superscriptYOffset custom paramter, or information from zero.sups if the sups feature has been setup in the font.

You may well have to go back to this step later as more of the font is being created.

** Step 7: Import Italics **
If you have italics in another font then you will want to import those glyphs into the math font.  The script "Import Italics" will attempt to help you with this.

** Step 8: Accents **
Mathematics typesetting uses accents, but I think we can ignore all the "combining accents". The standard list can be found in the filter.

The Glyphs3 script "Add math.ta Anchors for Combining Marks" will add math.ta anchors (it will guess the position based on either availability of _top or _bottom anchors, else pick the midpoint).   You can run this script again when further accents are created.

Test file: accenthorizontal.tex.

** Step 9: Dotless **
Dotless feature

** Step 10: Add bottom anchors **
Not strictly necessary; only used for the bold variants described in Step XX.

** Step 11: Add top anchors**
Not strictly necessary, but useful in the next step that uses "top" to determine the math.ta position.   The script Report Letter Glyphs Missing Top or Bottom Anchors will notifiy you of which letters are missing such anchors.  There is a mekkablue script that will add them at default positions, but they may then need manual adjusting.

** Step 12: Add math.ta anchors to letters**
The script "Add math.ta Anchors for Letters" will help you add math.ta anchors to your letters.  *note italic correction*.  It is a good idea if all your letters already have a "top" created for this.
Note: This script will create the math.ta anchors at cap-height (the y-position of this anchor is not used).  The y position of the math.ta anchor is not used by the math engine; the script places it somewhere reasonable.  

You may still need to adjust some of these by hand.  Test document: blah.

** Step 12: Bold **
Add an axis called "Math Weight" with code MGHT.   It is probably a good idea to have the same axis mapping as the weight axis if the font has such an axis mapping.

Add a virtual master for the Math Weight axis (so for Playfair this had position Weight = minimum (360); opsz = minimum (5); Width = minimum (94); Math Weight = maximum (900))

Create your mathbold letteres as needed.   Run the script Create or adjust math bold letters (you can apply this to just the selected glyphs or all the boldmath glyphs).

Now adjust your instances to give them a suitable MGHT value.  For Playfair MGHT is set to max(WGHT + 200,900).  Note that this means that if Weight is 900 then the boldmath is the same as the non-bold, and if Weight is close to 900 then there is little distinction.  There is no easy way around this.  One option is to not create instances at higher weights.  Another is to add a small "underline" to all the bold-math characters at high weight (see next step for how to do that)

** Step 13: Optical Sizing **
Playfair has an opz axes so optical sizing is easily done.  The script **blah** will populate any glyph that ends with .ssty.  We also needed an avar2 table for this.


*Step 13: Add Math Axis Metric*
It is useful to have a Math Axis metric.  You can select multiple masters to create this all at once.  It should be at the midheight of the minus glyph.  

Later you may want a metric for the height of big operators, and for the height and depth of the (largest) bracket/fence, and for the height/depth of the (largest) integral operator.




*Step 13: Add Glyphs!*
These can be taken in pretty much any order

**Components**

**Integrals**

**Large Operators**

**Arrows**




*Playfair Math Todo*
Bolditalics
Bracketlayers for bold
ssty (+ bracket layers)


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
other simple math symbols and anchors (redo the current ones with anchors)

