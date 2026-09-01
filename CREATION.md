# Somerville

The purpose of this document is to record the steps that were taken to create a mathematics font to pair with Playfair [https://github.com/clauseggers/Playfair] designed by Claus Eggers Sørensen. Rather than being considered a "manual," it should be viewed somewhere between an opinion piece and a diary, written in the hope that such a record is of help to others who may want to do something similar. Certainly many of the steps here could be done differently, or better, and a different font may require different steps or different choices.

The document proceeds step-by-step. Not all of these steps necessarily need to be taken in this order, but some thought has gone into what makes more sense as an earlier step than a later step. Moreover, some of the test documents that accompany this process were made under the assumption that earlier steps have been completed.

## Software Choice

The following software was used during this process:

For designing the font:

- Glyphs 3 https://glyphsapp.com/

And these are the Glyphs plugins:

- OpenType Math (essential)
- Show Stem Thickness
- LightTable
- mekkablue scripts

## Script Writing

Alongside this process are various Glyphs3 scripts.  Some were hand written, and some written by ChatGPT 5.5.

## Testing Documents

Part of this process was to create some reusable and consistent testing documents for a mathematics font, about which we will say more below.  For testing the following softwares were used

- ConTeXt
- Skim pdf reader
- Various web browsers

### Automatic ConTeXt generation
?What to say here?

## References
- [Building OpenType Math Fonts](https://github.com/notofonts/math/blob/main/documentation/building-math-fonts/index.md)
- unicode math and unicode-math symbols

More advanced/technical
- ConTeXt documentation
- Appendix G
- Appendix G Illustrated
- MathML specification
- Microsoft document about Cambria

## Getting Started

### Step 1: Select a Font to Pair

I chose Playfair as it is a beautiful open-source font that is distinct from the existing mathematics fonts available. It has three variable axes (weight, width, optical size) and I wanted to use this as an excuse to explore optical sizing.   It also has both upright and italics, the latter being useful since mathematics expects italic latin letters.  Playfair is  a very "precise font" (with the horizontal strokes going down to 1 unit at maximal optical sizing). Also available were some basic mathematics glyphs (plus, minus, divide, integral, radical) available.

My preference is to start with an existing font file and remove pieces rather than starting with a blank project and importing things. The reason is that this way I find myself stumbling across aspects of the existing font that I might not otherwise notice.

So make a copy of the `.glyphs` or `.glyphspackage` and change Font -> Info -> Family Name. Add a new author name if appropriate. If there is a variable instance in Font -> Info -> Exports, you may want to change that name as well.

### Step 2: Change Language System

Change Font Info -> Features -> LanguageSystems to:

```
languagesystem DFLT dflt;
languagesystem math dflt;
```

### Step 3: Remove Non-Mathematics Letters from the Font

Many glyphs in a text font have no place in a mathematics font. You can either remove these glyphs entirely or set them to non-exporting (I prefer the latter, at least initially). The main Latin uppercase and lowercase letters for a math font are A-Z and a-z, and all accented versions of these should be removed or set to non-exporting. One way to do this is to select all letters and make them non-exporting. Then use Filter -> Mathematics -> Latin, select those glyphs, and make them exporting.

Check the `.ssXX` and `.cvYY` alternates of such letters, as you want to keep those in the mathematics font to match the text font.

I also replaced the Playfair figures with the lining figures (`.lf`) versions, as they are more useful for a mathematics font. The original figures, as well as the tabular figures, were removed.

### Step 4: Math Constants Table

Glyphs has a [MathOpenType plugin](https://github.com/Nagwa-Limited-Community/Glyphs-MATH-Plugin) created by Khaled Hosny and it is also available in the Plugins directory from Glyphs 3. I made some small changes for a version that can be found *here*.

Go to Edit -> Edit Math Constants. The three-dot menu has a drop-down item for "Guess all Masters." It will make reasonable guesses for nearly all the constants.

The RuleThickness will take values from the minus glyph or underscore glyph. DisplayOperatorMinHeight will take a guess based on the integral glyph (if available). SuperscriptShiftUp (and others) will either use the `superscriptYOffset` custom parameter, or information from the ``sups`` feature has been set up in the font.

You should expect to return to these constants as the font develops. Getting the FractionRuleThickness right is particularly important early in development, as many other aspects of the font stem from this quantity.

### Step 5: Remove or Disable Features

Many font features do not make sense in a math font and can be removed or made inactive. The following can be safely removed or made inactive.  Others may need "updating" before the font can be exported if you have removed glyphs.

For Somerville the following features were removed or disabled (Font Info->Features)

- ccmp
- locl
- subs
- sups
- numr
- dnom
- frac
- afrc
- kern
- mark
- mkmk
- sinf
- orfn
- lnum
- pnum
- tnum
- onum
- c2sc
- case
- smcp
- dlig
- liga

Moreover I removed nearly all the classes as they were no longer in use (I kept Uppercase and Lowercase, but I am not sure they are used anywhere for a math font or if they really make sense):

### Step 5: Import Italics

Playfair has an italics font, which was used to import various math-italic glyphs. Thankfully they had the same master setup as the upright which made importing easier.  At this stage we should also import `idotless` and `jdotless` from the italics font. For this process we have the script ``Somerville Scripts->setup->Import Math Italic Glyphs From Source``

#### Note to self:

Think about what happens here with italics that have brackets or alternate layers; this might need further testing in the script.


### Step 6: Export Instances

Export instances at each master. It is also useful to export several intermediate instances (these can be useful in the next step).

### Step 7: Adjust the Math Constants

#### Note: This section needs finishing

Discuss the Math Constants tool.

The SuperscriptShiftUpCramped seems to behave differently in MathML in Chrome than in LuaLaTeX. In Chrome there seems to be some minimum value that is being taken here that is not present in LuaLaTeX.

SuperscriptBaselineDropMax is not behaving in MathML Core in the same way as the help file suggests it should.

### Step 8: Dotless

Add the `dtls` feature in Font Info -> Features.

Somerville had this for the `dtls` feature at this stage:

```
sub i by idotless;
sub j by jdotless;
sub iitalic-math by idotlessitalic-math;
sub jitalic-math by jdotlessitalic-math;
```

More dotless features can be added as the font developts.

### Step 9: Accents

Many mathematics typesetting systems use the combining accents (that is, those that end in `.comb`)., but I imagine it does not do any harm to leave the non-combining ones in as well 

Mathematics accents benefit from having a `math.ta` anchor. Use ``Somerville Scripts -> setup -> Insert math.ta Anchors for Math Accents``. It will add `math.ta` to an internal list of.anchors (it will guess the position based on either the availability of `_top` or `_bottom` anchors, or else pick the midpoint). You can run this script again if and when further accents are created.

#### Test File

`accenthorizontal.tex`.

#### Note

### Step 10: Add Top Anchors

Not strictly necessary, but useful in the next step that uses "top" to determine the `math.ta` position. The script ``Somerville Scripts->report->Report Mathematical Letters Missing Top or Bottom Anchors``  will report which letters are missing such anchors. There is a mekkablue script that will add them at default positions, but they may then need manual adjusting.

### Step 11: Add math.ta Anchors to Letters

Letters benefit from having a `math.ta` anchor (otherwise typesetting systems will typically put accents at the midpoint of the bounding box). Note that the y-position of any `math.ta` anchor is never used, so they can be placed anywhere.

The script ``Somerville Scripts->setup->Insert or adjust math.ta Anchors for Mathematical Letters`` will help you add `math.ta` anchors to your letters. The script asks for italic correction that can be obtained from Font -> Info of the italic font; this is used only to help better guess the position of the anchors for the italic letters. Once run, these anchors may need manual adjusting.

#### Test Documents

### Step 12: Add Axes

#### Bold 
There are various ways in which one can use the weight axis in an efficient way to obtain the mathematics bold letters. This is the one that I used also in Pennstander that I think works well and gives good flexibility. If and when new OpenType features become supported for mathematics fonts, there may be a more efficient way to do this.

In Font Info, add an axis called "Math Weight" with code `MGHT`.   Since Playfair has a math axis mapping I made the math weight follow this same mapping.

#### Optical Sizing
Somerville has optical sizing as an axis already. But there is an additional optical sizing for the superscripts and subscripts that applies just for mathematics. Thankfully we can use the optical sizing axis for this additional optical sizing. If the font does not have optical sizing, you might be able to do something similar with the weight axis (but the script below would need changing).

Create one new axis called `STYA` and one called `STYB`. These can eventually be hidden axes, but you might want to keep them unhidden during development.

Since these axes are hidden you do not need an axis mapping table for these.

#### Bold virtual masters

Then add a virtual master for the Math Weight axis (so for Somerville this had position Weight = minimum (360); opsz = minimum (5);SSYA=5, SSTYB=5, Width = minimum (94); Math Weight = maximum (900)).

#### STYA and STYB virtual masters

 Create virtual masters for each of them. The first was created at `wght=360`, `opsz=5`, `wdth=94`, `MGHT=360`, `STYA=1200`, `STYB=5`, and the second at `wght=360`, `opsz=5`, `wdth=94`, `MGHT=360`, `STYA=5`, `STYB=1200`.


### Step 12: Bold

Create your math bold letters as needed (you can use the Custom Filter). The script ``Somerville Scripts->setup->Create bold letters``  will allow you to create just the selected bold-math glyphs or all the bold-math glyphs. Now do the same for bolditalic-math glyphs.

Here is what this script is doing:  Suppose you are asking it to create the glyph `Abold-math`. It copies masters (and bracket layers if present) from the `A` glyph in such a way as to "collapse" the weight axis so that varying the weight has no effect at all.  Moreover it copies these layers so that the math weight axis does have an effect (so that at the highest math weight this glyph is bold). This is a kind of "rotation" in design space, and I am surprised I could not find it already in use.  

You can also consider using the script ``Somerville scripts->reports-> Report math bold completeness`` to check for any missing bold and bold italics. You may want to use this script again as you build more letters.

Now adjust your instances to give them a suitable `MGHT` value.  The script ``Somerville ->Script-> Set Math Weight on Static Instances`` did this for all the instances.  The UI of this script asks for the maximum weight (for Somerville it is 900) and the adjustment for bold (chosen to be 200).  Then the MWGT is set to `min(WGHT + 200,900)` for each of the instances.   

#### Test Documents

The `boldmath.html` page will help you check if the bold has been created correctly. The red and the black *should* be identical; the tiny differences, I expect, are some kind of rounding errors.

#### Note

A LaTeX test is also needed here.

### Step 12b: Bold letters at high weight (very optional)

The above way of managing the bold letters means that if Weight is 900 then the only natural choice of Math Weight is also 900 and then the regular and bold letters will look identical (and even if Weight is close to 900 they will be nearly identical). I do not see an easy way around this.

One option is to not create instances at these higher weights. Another is to add a small "underline" to all the bold-math characters at high weight. This is easily done by ensuring that all the bold and bold italics have a bottom/underline anchor and then pasting the feature below into, say, `ss10` or similar (you might want this turned on automatically at higher weights; it is a judgement call). Adjust the below to include other bold letters as needed. Manual adjustment of the bottom/underline anchor may be needed for some letters as appropriate. (The reason it is useful to use underline rather than bottom is that components of glyphs may have their own bottom anchors that are not the ones that you want.)

A simple version of this would be the following
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
```

You can change `macronbelowcomb` to another glyph that has a `_bottom` anchor; make sure this glyph is category Mark and Nonspacing.


A more complicated one is this one that has different widths for different letters.  Even that is not perfect.  **FIXME**


### Step 13: Optical Sizing

Add glyphs `A.ssty1`, `A.ssty2`, `B.ssty1`, `B.ssty2`, etc. Select these and run the script ``Somerville Scripts->setup->Create SSTY glyphs''.

You can repeat this step for other glyphs that you want optical sizing for, either now or later.  Many existing math fonts have ssty variants for the letters and main mathematics glyphs (e.g. plus, minus). 

 It is a design choice how many such glyphs to include, but this script allows the possibility to have ssty variants for all mathematics glyphs.   My observation is that with this system you may as well have any ssty variants for glyphs that are "light" enough for it to be noticable (e.g. whitesquare does benefit from an ssty, where as blacksquare does not).

One thing to think about is how math variants and math extendibles act with .ssty.  This is not done automatically by the script so unusualy behaviour may happen if you add ssty variants for such glyphs (e.g. integrals, bigoplus etc).   One wonders if ssty for these are really necessary (e.g. should we ever have ``\[ 2^{\bigoplus_{i=1}^n a_i}]) \]" ?

Add the feature Font Info -> `ssty` and have it autogenerate.

Next you need to edit your instances for this. If the script size is 70%/50%, then if your instance is designed for 10pt you want to set the `STYA` and `STYB` values so that the `.ssty1`/`.ssty2` glyphs are designed at 7pt/5pt. This took a little effort, and I need to go back to it.

*** Test document***

#### Note

***** Important FIXME needed ******* There is an annoying a bug here since I did not create all the axes first; I need to change the ``populate bold script`` to property take into account the `STYA` and `STYB` axes correctly.

#### Test Documents

A testing document is needed here.

### Step 14: Add Math Axis Metric

It is useful to have a Math Axis metric. Font Info -> Masters. You can select multiple masters to create this all at once. It should be the same as that of the MathConstant Math Axis.

Other metrics can also be useful. Somerville has them for the big operators, the height and depth of the largest bracket/fence, and the height/depth of the largest integrals.


### Step 14: Add Glyphs

These can be done in pretty much any order. We will discuss various design choices made for Somerville and some of the scripts we developed for these in the sections below.


*Glyphs*


**Components**
_smart.circle (height)
Really this was silly and what we had were 2 ellipses centered for each master.  There were some further constraints, for instance if you want it to be a circle at width=100 (which is annoying linear alegebra; maybe a bracket layer here is more sensible).   This was tricky and I am still not sure I got it right
Things to check: center position; anchors align with the center; symmetry

_smart.plus
(height,width)
Design choices: the plus was thinner at small sizes; the smallest one (plus.circle) even more so done with scaling.  Not you cannot scale and change the smart axis else you do not get linear interpolation (it is quadratic)
Things to check: that the plus touches the circle perfectly

Could I create a testing document for this glyph?

_smart.times (can be _smart.plus rotated by 45).  Is this a component or a glyph?
Design choices: the plus was thinner at small sizes; the smallest one (plus.circle) even more so done with scaling
Things to check: that the times touches the circle perfectly


**Integrals**

Design or use your existing integral
1. Cut it into 5 pieces.  The script cut at y-value can help.  You want a middle piece so you can swap it out later for other kinds of integrals, and the two vertical pieces can be extenders.

2. Add high layers using the script.

3. Design the high layers. For an integral horizontal stem This could be easy if you only need to stretch the extenders.  For a slanted one you will need to design more.   I adjusted the height of the integrals to match the height of the largest size of the large operators.

4. Add a center anchor, top and bottom.  Make the center align with the math-axis on all layers. 

5. (Optional) Make the top and serif their own components (there is a Glyph3 bug here and if you do that you need to reset the smart settings for the components)

6. The high integrals need to be a little wider to compensate optically

** for double integral**
create _smart.dblIntegral
add _smart.integral twice
adjust the #exit and #entry for _smart.integral as needed
make higher layers for _smart.dblIntegral.   Adjust the heights 0 for the small, 100 for the max
create dblIntegral and add _smart.dblIntegral as a component
create the height variants from the script
Things to check: exit/entry for semicondensed and semiexpanded; math.ic should inherit.  Test against integral and tripleintegral


***For contourIntegral***
create _smart.contourIntegral
Add _smart.integral Add _smart.circle
Script for High layers
Adjust sizing of the components as desired as well as the scaling (both can be adjusted!)
Create contourIntegral
Add _smart.contourIntegral
Script: Create size variants
Think about the sidebearings as these are not right from these components!
Think about math.ic (I want this inherited from the component I think so need to adjust the script)

Design comments: The circle needs to be a little larger at high sizes to compensate optically.  With the way things are I can adjust "scale" which also changes the thickness and then "height" to change the size.  The semiexpanded ones are the same height as the semicondensed (as are the letters)  I did a lot of adjusting by hand; not sure if that means that my _smart.circle is not designed correctly.



**Big Operators**


** for product **
Usual build process (no need to describe)
Stems slightly thicker at height
**todo: return to the serifs at high**

** for plus**


****For bigdot***
Create _smart.operator.circled
Add _smart.circle component.  Then add bullet component
Then run Script -> Create High Layers
Adjust height on the high layers.  The smallest one should be the size you want for the inline; the highest is the one for the largest display operator (so the non high layers got 5 for the circle and the high layers got 85) and the percentage scaling (both directions) for the bullet operator
Design choices: The dot in the middile is smaller at small sizes.  Even smaller for the smallest one.   Elongated slightly at expanded else it hides the expandion of the outer circle.

Create operator.circled
Add _smart.circle component
Set to the desired height (likely 0)
Run variant script.

***For oplus:***
Decompose oplus after running script to make the plus lighter by changing the "scale"
%%Make _smart.oplus as a smart component with height %using _smart.plus and _smart.circle.  Adjust %theheights of _smart.plus and _smart.circle as %appropriate
%Use _smart.oplus to make oplus and nAryOplus
%Make vertical size variants from nAryOplus


** For bigtimes
I got into a bit of a mess here because we can change many things
_smart.times (scale, thinness at base for each non-thin master)
nAryTimes: thinness for each master
Then the variants copy the nAryTimes values
!!!Need to think about this before proceeding!!!!

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

Notes: doublebar and triplebar need slightly narrower bars (scaling) else they look too heavy
Notes: Spacing in the expanded between the bars looks good and is done in the base glyph.

Test document: 
mathfonttester
varianttester??


**Arrows**

(see Arrows.md)

I decided to make all the arrows from components consisting of a "tail" "middle" and "head".  The naming convention is arrowname.lft,  arrowname.mid, arrowname.rgt.  Exceptions are made, in particular when reusing components.  The .mid pieces are smart that have a width axis (so that the total width of the arrow can be adjusted).   The left-to-right arrows are considered primary.  #exit/#entry anchors helped.  Putting a short .mid component on the .lft and .rhg is useful for extendibles as some typesetting systems take into account the sidebearings of the components.  with this sytem creating extendibles is immediate (it was decided that all overlaps should be 30 units which was set to be the smallest value of the .mid).

Somewhat painful is to make double arrows, e.g. two right arrows on top of each other as you need to adjust 3 glyphs.  The script **blah** helps with this, but some manual adjustment is needed

Design choice: semiexpanded arrows have expanded heads and tails.  This is consistent with the expansion of text for vertical arrows, but not for horizontal arrows.   But I think we want our vertical arrows to be rotations of the horizontal ones, so there was a compromise to be made here.  Playfair made the same compromise.

Design choice: Not all the arrows have the same base width.  SemiExpanded ones are longer than the semicondensed ones.  This is true for vertical and horizontal.  Again this is not really consistent with the text expansion so need to think about this more perhaps.

Design Choice: Playfair arrows had beautiful double tails.  One of these tails were kept on all arrows, with the double tail kept for double tail.  I imagine somebody will one day ask for a stylstic set without the tails.

Design Choice: Black Micro arrows were made skightly thicker, consistent with our choice on minus,plus (and not consistent with Playfair)

Design choice: Horizontal arrows align on the math axis Vertical arrows do not need assembly data (but we could easily add it).  They align to the baseline.  Some are all but that is fine.  If need be we can consider shrinking tails for some of them.

Design Choice: Frombar has serifs (or do these have a different name)? from the bar to the arrow stem.  That was not as easy as I had hoped, but thank goodness for components!



======
Recipes needed
= ??? Equals from minus??
= ??? dot then minus and minus then dot as an intermediate for the colon equals (is there a better way?)
= Fences Recipes
= _smart.circledoperator and _smart.oplus from components
= Bigdot recipe (I did this manually from smart_circledoperator)
= Bigplus recipe (I did this manually from smart_oplus)


*Somerville Todo (16)*
=== Fix bold vs ssty (did I even write the script for this?)
=== Instances
=== Remove the non exporting glyphs
===== Arrows
Go back and deal with the minimum widths of the different arrows
=== Arrowheads
=== Create times at sizes;  fix this mess
=== Return to bigodot, bigoplus, bigotimes (+testing pages)
=== Variable Integral
=== Look back at weight of summation (started)
=== primes
=== spacing of double and triple bar (?)
=== improve ceiling, floor, bracket
=== ??Variation of naryoperatorsize
=== Center the bar, bracket, brace etc (these might be OK)
=== relations recipes (in fact need to revisit the entire recipe system)
=== Other accents
=== Union, Subset, \in
=== may need to think more about sidebearings of _smart.circle as I just did this roughly
=== Product glyph serifs at high
=== sym glyph so can do many more relations
=== bold underlines (script?)
=== spacing/italic correction
=== slash at sizes


Longer run
===? Testing tool to also support looking at instances
===? Latex system in my testing tool
=== over/underbraces
=== extended plus,minus, equv etc
=== italic correction on large parenthesis
=== more fences
=== corner kerns
=== extended integral serifs
=== \mathbb R,N,Z
=== list the most useful missing glyphs
=== wideaccents

----------------------------------------------
Testing stuff
== Get a better lualatex test file for the math constants
== Go through the help file again and compare his recommendations with my choices
===Have some "constants" in the recipes
===Have a system of spotting 'stale' recipes
italic tau
epsilon?


Change the anchors on the marks to they are in Glyphsdata.xml
Do the large operator K
Greek lower
Greek upper
Extendibles?
Stackers
Other fences


Todo: Checker Script
== Height of fences
== Missing bolds
== Missing or inconsisent vVariants or hVariants

Private glyphs
idotlessbold-math
idotlessbolditaluc-math
jdotlessbold-math
jdotlessbolditaluc-math
K operator for continued fractions
Double Struck upper case Greek
Missing display nary operators
Easter Egg
Fourier


======= Future testing areas
======= Showcases
======= Integrals
======= Radicals
======= Big Operators
======= BIG Operators
======= Fences
======= Alphabets
======= Fractions
======= Accents
======= Arrows
======= Individual operators
======= Individual relations
======= Individual relations
======= Super and subscripts
======= etc. etc.
======= Stress tests (from other places)

