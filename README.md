**Playfair Math**

This records the steps taken to create a math font to pair with Playfair. The hope is that these notes may also help with other font pairings in the future.  Not all the steps need to be done in the order they appear here.

My preference is to start with a text font and remove unwanted things.  The other route would be to start with a blank font and import the pieces that you need.

*Step 1: Select a font to pair*

Things to consider include glyph coverage, existing italic and bold styles, and possible optical sizing. Existing mathematical glyphs, such as plus and minus, may also be helpful. Check the font license to make sure you can reuse it, and confirm that there is not already an existing math-font pairing available.  Go to Font->Name and change the name if appropriate.

Give your font its new name.

*Step 2*
Change the languages to
```
languagesystem DFLT dflt;
languagesystem math dflt;
```

*Step 3: Remove non-mathematics letters from the font*
Remove ligatures, these are not used in a mathematics font.

The main uppercase and lowercase latin letters for a Math font are A-Z and a-z.  Accented versions of these should be removed.  One way to do this is to select all letters and make them non-exporting.  Then Filter -> Mathematics -> Latin and select those ones and make them exporting.

Check the .ssXX and .cvYY alternates of such letters as you probably want to keep those to match the text font

I also disabled all the .lf and .tf glyphs as these are not used in math (is that correct? look again at unicode-math for the features it supports)

I also replaced the Playfair figures with the .lf versions as I think that is more useful in mathematics.

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



** Step 10: Add underline anchors **
Not strictly necessary; only used for the bold variants described in Step XX.  **script needed to reuse existing bottom anchors**

** Step 11: Add top anchors**
Not strictly necessary, but useful in the next step that uses "top" to determine the math.ta position.   The script Report Letter Glyphs Missing Top or Bottom Anchors will notifiy you of which letters are missing such anchors.  There is a mekkablue script that will add them at default positions, but they may then need manual adjusting.

** Step 12: Add math.ta anchors to letters**
The script "Add math.ta Anchors for Letters" will help you add math.ta anchors to your letters.  *note italic correction*.  It is a good idea if all your letters already have a "top" created for this.
Note: This script will create the math.ta anchors at cap-height (the y-position of this anchor is not used).  The y position of the math.ta anchor is not used by the math engine; the script places it somewhere reasonable.  

You may still need to adjust some of these by hand.  Test document: blah.

** Step 12: Bold **
Add an axis called "Math Weight" with code MGHT.    Have the axis mapping be the same as that of the Weight axis.

Add a virtual master for the Math Weight axis (so for Playfair this had position Weight = minimum (360); opsz = minimum (5); Width = minimum (94); Math Weight = maximum (540))

Create your mathbold letters as needed from the filter on the left.    Run the script Create or adjust math bold letters (you can apply this to just the selected bold-math glyphs or all the boldmath glyphs).  Now do the same for bolditalic-math glyphs.

Consider using the check_math_bold_upright_completeness to see for any missing bold and bolditalics.  You may want to use this script again as you build more letters.

Now adjust your instances to give them a suitable MGHT value.  For Playfair MGHT is set to min(WGHT + 200,900).   The script set_math_weight_on_static instances does this.

The boldmath.html page will help you check if the bold has been created correctly.  The red and the black *should* be identical, but there appears to be some minor (hopefully unnoticable) differences.

**need also a latex test here**

*Step 12b Optional*
 Note that the above setup means that if Weight is 900 then the boldmath is the same as the non-bold, and if Weight is close to 900 then there is little distinction.  There is no easy way around this.  
 
 One option is to not create instances at these higher weights.  Another is to add a small "underline" to all the bold-math characters at high weight.  This is easily done by ensuring that all the bold and bolditalics have a bottom/underline anchor and then pasting the below feature into say ss10 or similar (you might want this turned on automatically at higher weights, it is a judgement call).  Adjust the below to include other bold letters as needed.  Manually adjustment of the bottom/underline anchor may be needed for some letters as appropriate.  (The reason it is useful to use underline rather than bottom is that components of glyphs may have their own bottom anchors that are not the ones that you want; this is a minor thin)

```
 @LatinBoldMath = [
    abold-math bbold-math cbold-math dbold-math
    ebold-math fbold-math gbold-math hbold-math
    ibold-math jbold-math kbold-math lbold-math
    mbold-math nbold-math obold-math pbold-math
    qbold-math rbold-math sbold-math tbold-math
    ubold-math vbold-math wbold-math xbold-math
    ybold-math zbold-math

    Abold-math Bbold-math Cbold-math Dbold-math
    Ebold-math Fbold-math Gbold-math Hbold-math
    Ibold-math Jbold-math Kbold-math Lbold-math
    Mbold-math Nbold-math Obold-math Pbold-math
    Qbold-math Rbold-math Sbold-math Tbold-math
    Ubold-math Vbold-math Wbold-math Xbold-math
    Ybold-math Zbold-math
];

@LatinBoldItalicMath = [
    abolditalic-math bbolditalic-math cbolditalic-math dbolditalic-math
    ebolditalic-math fbolditalic-math gbolditalic-math hbolditalic-math
    ibolditalic-math jbolditalic-math kbolditalic-math lbolditalic-math
    mbolditalic-math nbolditalic-math obolditalic-math pbolditalic-math
    qbolditalic-math rbolditalic-math sbolditalic-math tbolditalic-math
    ubolditalic-math vbolditalic-math wbolditalic-math xbolditalic-math
    ybolditalic-math zbolditalic-math

    Abolditalic-math Bbolditalic-math Cbolditalic-math Dbolditalic-math
    Ebolditalic-math Fbolditalic-math Gbolditalic-math Hbolditalic-math
    Ibolditalic-math Jbolditalic-math Kbolditalic-math Lbolditalic-math
    Mbolditalic-math Nbolditalic-math Obolditalic-math Pbolditalic-math
    Qbolditalic-math Rbolditalic-math Sbolditalic-math Tbolditalic-math
    Ubolditalic-math Vbolditalic-math Wbolditalic-math Xbolditalic-math
    Ybolditalic-math Zbolditalic-math
];

@AllMathUnderlineTargets = [
    @LatinBoldMath
    @LatinBoldItalicMath
];

lookup AddMathUnderline {
    sub @AllMathUnderlineTargets by @AllMathUnderlineTargets macronbelowcomb;
} AddMathUnderline;
'''

You can change macronbelowcomb to another glyph that has a _bottom anchor; make sure this glyph is category Mark and Nonspacing

** Step 13: Optical Sizing **

Playfair has an opz axes so optical sizing is easily done. 

Create an axis called STYA and one called STYB. These can be hidden axes. Create virtual masters.  Since they are hidden you do not really need an axis table for these.

 Add glyphs A.ssty1 A.ssty2 B.ssty1 B.ssty2 etc.  Select these and run the script populate_ssty.py.  

 You can repeat this step for other glyphs that you want optical sizing for, either now or later.

 Add the feature ssty and have it autogenerate

 ** there was a bug here since I did not create all the axes first; need to change this README and change the populate bold script as well to take into account of the STYA and STYB axes correctly **

 **need testing document here**

Next you need to edit your instances for this.  If the scriptsize is 70%/50% then if your instance is designed for 10pt you want to set the STYA and STYB values so that the .ssty1/ssty glyphs are designed at 7pt/5pt.

**need testing documents here**

*Step 13: Add Math Axis Metric*
It is useful to have a Math Axis metric.  You can select multiple masters to create this all at once.  It should be at the midheight of the minus glyph.  

Later you may want a metric for the height of big operators, and for the height and depth of the (largest) bracket/fence, and for the height/depth of the (largest) integral operator.




*Step 13: Add Glyphs!*
These can be taken in pretty much any order

**Components**

**Fences**

a. Make sure all the brackets are *exactly* the same height (brace, bracket, bar, parenthesis ...)

a2. Making the bracket with three "pieces" namely a top, stem and bottom is useful so you can reuse that to make the bar and the ceiling and floor.

To make larger sizes of left bracket
a. Make a smart component from the left bracket

b. On the smart component use the create high layers script

c. Adjust the high layers all by exactly the same amount. Also adjust the high layers on the other fences, also by exactly the same amount

d. (Optional): Add metrics

e. Use script to create the variants

f. take the right parenthesis.  Clear all masters.  Add the _smart.leftparenthesis components.  Flip it vertically on all masters.

There is also a script to flip vertically.  It would be good to be able to flip horizontally on all masters as once

Note: the script record the step and n for each glyph, but ideally you want to use these same values for all of the braces for pairing reasons.

**Integrals**

**Large Operators**

**Arrows**



*Mayfair Todo (16)*
Script or system to insert the constants into the glyphs file
Finish summation glyph
Parentheses
bracket, floor, ceiling need to be more visible
Center the bar, bracket, brace etc.
Do the product glyph at display sizes
Minus at various widths
Circle and sizing
Redo the existing + divide, = and many others :-(
radicals
relations
spacing/italic correction
Integrals
Union, Subset, \in
other simple math symbols and anchors (systematic system)
Arrows

Math Constants and test docs
Test ss11 feature at other fonts
italic tau
epsilon?
arrows

Greek lower
Greek upper
Extendibles
Stackers
Other accents
Other fences


Todo: Checker Script
Height of fences
Missing bolds
Missing or inconsisent vVariants or hVariants

Private glyphs
idotlessbold-math
idotlessbolditaluc-math
jdotlessbold-math
jdotlessbolditaluc-math
K operator for continued fractions
Double Struck upper case Greek
Fourier
