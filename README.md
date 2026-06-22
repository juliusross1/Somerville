**Playfair Math**

This records the steps taken to create a math font to pair with Playfair. The hope is that these notes may also help with other font pairings in the future.  Not all the steps need to be done in the order they appear here.

My preference is to start with a text font and remove unwanted things.  The other route would be to start with a blank font and import the pieces that you need.

*Step 1: Select a font to pair*

Things to consider include glyph coverage, existing italic and bold styles, and possible optical sizing. Existing mathematical glyphs, such as plus and minus, may also be helpful. Check the font license to make sure you can reuse it, and confirm that there is not already an existing math-font pairing available.  Go to Font->Name and change the name if appropriate.

Give your font its new name (if appropriate)

*Step 2*
Change the languages to
```
languagesystem DFLT dflt;
languagesystem math dflt;
```

*Step 3: Remove non-mathematics letters from the font*
Remove ligatures, these are not used in a mathematics font.

The main uppercase and lowercase latin letters for a Math font are A-Z and a-z.  Accented versions of these should be removed.  One way to do this is to use a Smart Filter "Has Components >1" and select "Uppercase letters" and you will get a view of letters that can be either deleted or set not to export (some letters may be worth keeping to be used as a template for the future; those can just be set to not export)

Keep the .ssXX and .cvYY alternates of such letters as you probably want to keep those to match the text font

I also disabled all the .lf and .tf glyphs as these are not used in math (is that correct? look again at unicode-math for the features it supports)

*Step 4: Remove or disable features*
Many font features do not make sense in a math font and can be removed or made non-active.  The following can be safely removed/made inactive:

Maybe keep
Uppercase/lowercase

Remove
All other classes
ccmp
locl
subs
sups
numr
dnom
frac
afrc
kern
mark
mkmk
sinf
orfn
lnum
pnum
tnum
onum
c2sc
case
smcp
dlig
liga


*Step 5: Export Instances*

Export instances at each master coordinate. It is also useful to export several intermediate instances (see next step).

*Step 6: Math Constants Table*
Install the Math OpenType plugin (version made by JR link). Go to Edit -> Edit Math Constants. The three-dot menu has a drop-down item for "Guess all Masters". It will make reasonable guesses for many constants. 

One exception may be DisplayOperatorMinHeight, which you can edit yourself or leave as zero and return to later. **Todo: have this make gusses for thse and the skewedfraction constants*

The rulethickness will take values from the minus glyph or underscore glyph
DisplayOperatorMinHeight will take a guess based on the integral glyph (if available)
SuperscriptShiftUp (and others) will either use the superscriptYOffset custom paramter, or information from zero.sups if the sups feature has been setup in the font.

You should expect to go back to these constants as you develop your font.

** Step 7: Import Italics **
If you have italics in another font then you will want to import those glyphs into the math font.  The script "Import Italics" will attempt to help you with this.  If your font has them, import also idotless and jdotless from your italics font.
There is a case here to consider, namely if the source glyph has bracket or alternate layers.

** Step 9: Dotless **
Add the dtls feature
Here is mine at this stage
``sub i by idotless;
sub j by jdotless;
sub iitalic-math by idotlessitalic-math;
sub jitalic-math by jdotlessitalic-math;``

** Step 8: Accents **
The filter will show you the accents.  Many typesetting system use the non-combining accents, but I imagine it does not do any harm to leave the combining onese in as well.

The Glyphs3 script "Add math.ta Anchors for Combining Marks" will add math.ta anchors (it will guess the position based on either availability of _top or _bottom anchors, else pick the midpoint).   You can run this script again when further accents are created.

Test file: accenthorizontal.tex.



** Step 10: Add bottom anchors **
Not strictly necessary; only used for the bold variants described in Step XX.

** Step 11: Add top anchors**
Not strictly necessary, but useful in the next step that uses "top" to determine the math.ta position.   The script Report Letter Glyphs Missing Top or Bottom Anchors will notifiy you of which letters are missing such anchors.  There is a mekkablue script that will add them at default positions, but they may then need manual adjusting.

** Step 12: Add math.ta anchors to letters**
The script "Add math.ta Anchors for Letters" will help you add math.ta anchors to your letters.  *note italic correction*.  It is a good idea if all your letters already have a "top" created for this.
Note: This script will create the math.ta anchors at cap-height (the y-position of this anchor is not used).  The y position of the math.ta anchor is not used by the math engine; the script places it somewhere reasonable.  

You may still need to adjust some of these by hand.  Test document: blah.

** Step 12: Bold **
Add an axis called "Math Weight" with code MGHT.    Here I found a glitch with corner components that had width/height intermediate layers that was avoided by setting the minimum MGHT axis value to be 0.  This was then fixed with the axis mapping so the external coordinates were the same as that of wght

Add a virtual master for the Math Weight axis (so for Playfair this had position Weight = minimum (360); opsz = minimum (5); Width = minimum (94); Math Weight = maximum (540))

Create your mathbold lettere as needed from the filter on the left.    Run the script Create or adjust math bold letters (you can apply this to just the selected bold-math glyphs or all the boldmath glyphs).  Now do the same for bolditalic-math glyphs.

Consider using the check_math_bold_upright_completeness to see for any missing bold and bolditalics.  You may want to use this script again as you build more letters.

Now adjust your instances to give them a suitable MGHT value.  For Playfair MGHT is set to min(WGHT + 200,900).   The script set_math_weight_on_static instances does this.

 Note that this means that if Weight is 900 then the boldmath is the same as the non-bold, and if Weight is close to 900 then there is little distinction.  There is no easy way around this.  One option is to not create instances at these higher weights.  Another is to add a small "underline" to all the bold-math characters at high weight (see next step for how to do that)

** Need testing files here **


** Step 13: Optical Sizing **
Playfair has an opz axes so optical sizing is easily done.  The script **blah** will populate any glyph that ends with .ssty.  

Again you need to edit your instances for this.  If the scriptsize is 70%/50% then if your instance is designed for 10pt you want to set the STYA and STYB values so that the .ssty1/ssty glyphs are designed at 7pt/5pt.


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
Go back to a version of the glyphs file from 8pm on Saturday
Look at h and yitalic
Fix VF exporting
Test instance exporting and overlap

Add all bold and bolditalics of the glyphs that you have
Design a test document for this (perhaps buy fontproofer?)

Then do the script for ssty for the Latin Letters and
Design a test document for this

Fix issue with mathopentype plugin versions!
Then...
Minus at various widths (need to fix this one up)
Math constants and create testing documents
Redo the existing + divide, = and many others :-(
Times at size
Brackets and sizing
Integral and sizing and split into three pieces

Longer testing document

Double integrals
Sum and sizing
Deal with Bold (progress!)
Circle and sizing
Contour integral
Other display operators?
Sylistic set for sizing
See about ssty
other simple math symbols and anchors (redo the current ones with anchors)

