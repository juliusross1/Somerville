Todo: 
= MathML tests
= DoubleArrow Tails
= Go through the smart component settings of ArrowHead, Harpoon, DoubleArrow Head for consistency and design choices
= Look over all lengths again (script to test this)
Notes: I think that the total width of the Arrow can be a little longer on semiexpanded and a little less long on semicondensed
= Strokes and minimal lengths (again).  Recipes for the anchors
= Test/fix Assemblies
= Retest building all the arrow and fix up documentation

# Mathematical Arrow Notes

We will describe here a system used in to create a large number of mathematical arrows from a small number of so-called "composed components".  The composed components require designing by hand, and the system expects certain properties of these composed components, with more properties expected if you want to include more complicated features.

## Features Supported within this system:
- Ensuring that groups of horizontal arrows have the same length and that groups of vertical arrows have the same height
- Horizontal and Vertical Math Assembly
- An ARLN axis that controls the length of horizontal arrows, with different minimum lengths for groups of arrows
- An ARHT axis that controls the height of horizontal arrows
- An ARHD axis that controls the size of the arrow head
- An ARTL axis that controls the size of the arrow tails

## Horizontal Components

Each horizontal arrow consists of three components left/middle/right and a possible "stroke". The left and right components are eiher a "Head" or an "End".  So for example in \rightarrow these are end/middle/head and for \leftarrow these are head/middle/end.

![alt text](horizontalcomponents.png)

## Horizontal Heads and Ends

Heads and Ends are divided into two sets called "Short" and "Long".  All the "Short" Heads and Ends are expected to have the same width, and all the Long Heads and Long Ends are expected to have the same width within a given master. So, for instance, if there is a Black Master then all the Long Heads and all the Long Ends should have the same width in this master.   These widths need to be recorded in the constants file (see below).

Tip: if there is not to be an ARLN axis and/or you do not need as much control over the final width of arrows you can set the "Long" and "Short" to the same value for simplicity.

### Short Heads 
rightArrow.rgt
harpoonrightup.rgt
rightDoubleArrow.rgt
Arrowend.rgt

### Long Heads
twoheadrightarrow.rgt
rightTabHarpoonUpArrow.rgt
rightTabArrow.rgt
rightTabHarpoonUpArrow.rgt

### Short Ends
rightArrow.lft
FrombarArrowEnd.lft
FrombarDoubleArrowEnd.lft

### Long Ends
ArrowEnd.lft
?DoubleArrowEnd.lft
ArrowEnd.lft
needs #exit anchor

## Composed Components

The composed components are those that need to be designed directly, all point from left-to-right.   All composed Head components should have LSB=0.  The RSB is a design choice that gives sidebearings to the arrow.   All composed End components should have RSB=0 and LSB as a design choice.  

The following components need to be composed.

### Smart Components

#### (optional) _smart.ArrowHead.top
LSB=0
RSB by design
Possible smart axis: weight, height
Useful to design so the weight=low have the same RSB and all weight=high have the same RSB
This glyph is flattened in the weight axis
#exit/#entry in the same place so that they align correctly in _smart.Arrow

#### _smart.ArrowHead
This can either be designed directly, or generated using two copies of _smart.Arrow.top with the second flipped in the y-direction to ensure symmetry
NOTES

#### _smart.Arrow.mid
This will be the horizontal bar of the horizontal arrows.  RSB=LSB=0.  It should have a "width" axis with a large range that agrees with its size in units (so a layer with width=30 should have width=30 for all masters and a layer with width=1000 should have width=1000).  Has #entry/#exit anchors on the border of the boundingbox, center aligned vertically.  Should be non-exporting.

It needs the following anchors
#entry
#exit
center
stroke
stroke_tail_head
stroke_tail_doublehead
stroke_doubletail_head
stroke_doubletail_doublehead
stroke_head_tail
stroke_doublehead_tail
stroke_head_doubletail
stroke_doublehead_doubletail
The stroke ones can be centrally placed for now (see Section ?? for what these are used for).


#### _smart.DoubleArrow.mid
Similar to _smart.Arrow.mid this will be the double horizontal bars of the double horiztonal arrows.  LSB=RSB=0.  As the _smart.Arrow.mid it should have a width axis setup in the same way.   Has #entry/#exit anchors on the border of the boundingbox, center aligned vertically.   Should be non-exporting.

### Ends

#### _smart.ArrowEnd
This will be part of the tail of \rightArrow.  Should be non-exporting.  For design where most arrows do not have visible tails this could be just a bar, and you could use _smart.Arrow.mid for this.  For arrows with tails this should be designed.

#### ArrowEnd.lft 
This will be the End of rightArrow and (similar arrows). 
Consists of components _smart.ArrowEnd and _smart.Arrow.mid.   The internal axis of _smart.Arrow.mid should be set so this glyph has the desired width as described in Section ??.  RSB=0

#### DoubleArrowEnd.lft 
This will be the tail of \DoubleRightArrow and similar.   RSB=0.   

#### ArrowEnd.lft
This will be designed for arrows that have a visible tail.  For designes where most arrows do not have visible tails there will be a visible tail here.  For designs where most arrows have tails this will be a "double tail".  Can use components _smart.ArrowEnd and Arrow.mid if it is helpful.  RSB=0.

### FrombarComponents
Glyphs: FrombarArrowEnd.lft  

FrombarDoubleArrowEnd.lft

Design of the tails of FrombarArrow and FromDobuleArrow.  RSB=0.   LSB by design, but likely to be similar to each other.

### ArrowHeads
Glyphs: _smart.ArrowHead.top,_smart.ArrowHead,ArrowHead.rgt,
DoubleArrowHead.rgt
DoubleArrowHead (adjusted Smart component from ArrowHead)
harpoonrightup.rgt
/twoheadrightarrow.rgt/

CHECK: Have a missed a component here?

**fixme** The others in the list are only used as components of these two and can be ommitted.    The _smart.ArrowHead.top can be the top half of the arrow, and the _smart.ArrowHead two copies of this one flipped in the y-direction to preserve symmetry.  Optional smart axes are width and height to enable variation of the arrows (and so that it can be reused for both ArrowHead and DoubleArrowHead.rgt).  

_smart.Arrowhead.top has identially placed #exit/#entry for placement in _smart.ArrowHead.   It also has %exit for placement of the bar in tab arrows such as rightTabHarpoonUpArrow.rgt and rightTabArrow.rgt.

rightDoubleArrow.rgt/rightTabHarpoonUpArrow.rgt/rightTabArrow.rgt
These can be semi-generated from the previous components and consist of a relevant head and a smart.Arrow.mid component so that their width is correct as described in Section ??.

### Others

#### Arrowend.rgt
This is a horiztonal bar with a right sidebar (LSB=0).  Used for glyphs such as ??

#### _ArrowTab

### _ArrowVerticalStroke, _ArrowDoubleVerticalStroke, _ArrowStroke
TBD if we actually use there

## Constants

## Generated Components

### Generated Mid-Components
Because the Heads and Ends have different widths, the system here uses different middle components to allow more control over the total width of the arrows.  There are recipes to create the following:

/Arrow.mid.LongLong
/Arrow.mid.ShortLong
/Arrow.mid.ShortShort

which will ensure all arrows have the same width.  (the width of these can then be adjusted if something else is desired).

For instance, any arrow with a "Short Head and Long Tail" or "Long Head and Short Tail" uses Arrow.mid.ShortLong as its middle component.  These can be non-exporting.

### Other Generated Componenets

The following components can now be generated from the above using recipes and are used in the arrows and the assemblies.  They can be set to non-exporting if math assembly is not used:

| Glyph | Glyph | Glyph |
|:------|:------|:------|
| `leftArrow.lft` | `leftArrow.rgt` | `leftTailArrow.rgt` |
| `leftFrombarArrow.rgt` | `leftTabArrow.lft` | `leftTabHarpoonDownArrow.lft` |
| `leftTabHarpoonUpArrow.lft` | `rightTabHarpoonDownArrow.rgt` | `leftDoubleArrow.lft` |
| `leftDoubleArrow.rgt` | `leftFrombarDoubleArrow.rgt` | `twoheadleftarrow.lft` |
| `leftHarpoonWithBarbDownBelowLongDash.rgt` | `leftHarpoonWithBarbUpAboveLeftHarpoonWithBarbDown.rgt` | `leftHarpoonWithBarbUpAboveLongDash.rgt` |
| `leftHarpoonWithBarbUpAboveRightHarpoonWithBarbUp.rgt` | `rightHarpoonWithBarbDownAboveLeftHarpoonWithBarbDown.rgt` | `rightHarpoonWithBarbDownBelowLongDash.rgt` |
| `rightHarpoonWithBarbUpAboveLeftHarpoonWithBarbUp.rgt` | `rightHarpoonWithBarbUpAboveLongDash.rgt` | `rightHarpoonWithBarbUpAboveRightHarpoonWithBarbDown.rgt` |
| `harpoonrightdown.rgt` | `leftToBarOverRightToBarArrow.rgt` | `leftOverRightHarpoon.rgt` |
| `rightOverLeftHarpoon.rgt` | `rightOverLeftArrow.rgt` | `leftAndRightArrow.rgt` |
| `rightDoublePairedArrow.rgt` | `leftDoublePairedArrow.rgt` | `leftHarpoonWithBarbDownAboveRightHarpoonWithBarbDown.rgt` |
| `leftArrowWithDottedStem.lft` | `leftHarpoonWithBarbDownBelowLongDash.lft` | `leftHarpoonWithBarbUpAboveLeftHarpoonWithBarbDown.lft` |
| `leftHarpoonWithBarbUpAboveLongDash.lft` | `leftHarpoonWithBarbUpAboveRightHarpoonWithBarbUp.lft` | `rightHarpoonWithBarbDownAboveLeftHarpoonWithBarbDown.lft` |
| `rightHarpoonWithBarbDownBelowLongDash.lft` | `rightHarpoonWithBarbUpAboveLeftHarpoonWithBarbUp.lft` | `harpoonrightup.lft` |
| `leftToBarOverRightToBarArrow.lft` | `leftOverRightHarpoon.lft` | `rightOverLeftHarpoon.lft` |
| `rightOverLeftArrow.lft` | `leftAndRightArrow.lft` | `rightDoublePairedArrow.lft` |
| `leftDoublePairedArrow.lft` | `leftHarpoonWithBarbDownAboveRightHarpoonWithBarbDown.lft` | `rightHarpoonWithBarbUpAboveLongDash.lft` |
| `rightHarpoonWithBarbUpAboveRightHarpoonWithBarbDown.lft` | | |



### List of Horizontal Arrows

These arrows can now be generated

| Glyph | Glyph | Glyph |
|:------|:------|:------|
| `leftArrow` | `rightArrow` | `leftRightArrow` |
| `leftTailArrow` | `rightTailArrow` | `rightArrowWithTailWithVerticalStroke` |
| `rightArrowWithTailWithDoubleVerticalStroke` | `leftArrowTail` | `rightArrowTail` |
| `leftDoubleArrowTail` | `rightDoubleArrowTail` | `leftArrowWithTailWithDoubleVerticalStroke` |
| `leftTwoheadedArrow` | `rightTwoheadedArrow` | `rightTwoHeadedArrowWithVerticalStroke` |
| `rightTwoHeadedArrowWithDoubleVerticalStroke` | `rightTwoHeadedArrowWithTail` | `rightTwoHeadedArrowWithTailWithVerticalStroke` |
| `rightTwoHeadedArrowWithTailWithDoubleVerticalStroke` | `leftTwoHeadedArrowWithVerticalStroke` | `leftTwoHeadedArrowWithTailWithDoubleVerticalStroke` |
| `leftTwoHeadedArrowWithTail` | `leftBarbUpHarpoon` | `leftBarbDownHarpoon` |
| `rightBarbUpHarpoon` | `rightBarbdownHarpoon` | `leftBarbUpRightBarbDownHarpoon` |
| `leftBarbDownRightBarbUpHarpoon` | `leftBarbUpRightBarbUpHarpoon` | `leftBarbDownRightBarbDownHarpoon` |
| `leftHarpoonWithBarbUpToBar` | `rightHarpoonWithBarbUpToBar` | `leftHarpoonWithBarbDownToBar` |
| `rightHarpoonWithBarbDownToBar` | `leftTabArrow` | `rightTabArrow` |
| `leftFrombarArrow` | `rightFrombarArrow` | `leftLongFromBarArrow` |
| `rightLongFromBarArrow` | `leftLongDoubleFromBarArrow` | `rightLongDoubleFromBarArrow` |
| `rightTwoHeadedArrowFromBar` | `leftDoubleArrowFromBar` | `rightDoubleArrowFromBar` |
| `leftHarpoonWithBarbUpFromBar` | `rightHarpoonWithBarbUpFromBar` | `leftHarpoonWithBarbDownFromBar` |
| `rightHarpoonWithBarbDownFromBar` | `leftToBarOverRightToBarArrow` | `rightOverLeftArrow` |
| `leftAndRightArrow` | `leftDoublePairedArrow` | `rightDoublePairedArrow` |
| `leftOverRightHarpoon` | `rightOverLeftHarpoon` | `leftHarpoonWithBarbUpAboveLeftHarpoonWithBarbDown` |
| `rightHarpoonWithBarbUpAboveRightHarpoonWithBarbDown` | `leftHarpoonWithBarbUpAboveRightHarpoonWithBarbUp` | `leftHarpoonWithBarbDownAboveRightHarpoonWithBarbDown` |
| `rightHarpoonWithBarbUpAboveLeftHarpoonWithBarbUp` | `rightHarpoonWithBarbDownAboveLeftHarpoonWithBarbDown` | `leftHarpoonWithBarbUpAboveLongDash` |
| `leftHarpoonWithBarbDownBelowLongDash` | `rightHarpoonWithBarbUpAboveLongDash` | `rightHarpoonWithBarbDownBelowLongDash` |
| `leftDoubleStrokeArrow` | `leftRightDoubleStrokeArrow` | `rightDoubleStrokeArrow` |
| `leftDoubleArrow` | `rightDoubleArrow` | `leftRightDoubleArrow` |
| `leftDoubleVerticalStrokeArrow` | `rightDoubleVerticalStrokeArrow` | `leftLongDoubleArrow` |
| `rightLongDoubleArrow` | `leftRightLongDoubleArrow` | `leftDoubleArrowWithVerticalStroke` |
| `rightDoubleArrowWithVerticalStroke` | `leftRightDoubleArrowWithVerticalStroke` | `leftLongArrow` |
| `rightLongArrow` | `leftRightLongArrow` | `leftRightStrokeArrow` |
| `leftVerticalStrokeArrow` | `rightVerticalStrokeArrow` | `leftRightVerticalStrokeArrow` |
| `leftStrokeArrow` | `rightStrokeArrow` | |

## Strokes
_smart.Arrow.mid has 9 anchors for the different strokes one some of the arrows.  The first is called "stroke" at the center of the glyph.  The next 4 are
stroke_tail_head
stroke_tail_doublehead
stroke_doubletail_head
stroke_doubletail_doublehead
So "stroke_tail_head" is the position of a stroke for an arrow with a simple single tail and single head (e.g. \rightArrow), where as stroke_doubletail_doublehead (e.g. blah).  Position these as needed.  

The script called "Reflect Paired Anchors around Center Anchors" means you need only place the first 1-5 of them, and the last 4 will be place symmetrically around the center axis.

Note: The naming here is poor as Mayfair has a notion of "doubletail" but it is really "tail".  

TIP: If you are not using the ARLN axis you may find these can all be centrally positioned on the smallest width size of _smart.Arrow.mid; and that adjustments are only needed at large sizes.



## ARLN axis
This is optional and allows a variable axis for the default width of the arrows.  It also allows for different groups of arrows to have different minimum widths.

Give the font an axis called ARLN.  For this discussion we will set the default=100 and give a virtual master at ARNL=200.  Set the masters to ARNL=200 and the exports to the default of ARNL=100.

New use the script "Adjust Arrow.mid components in a smart way" on each of the .mid components.  Use only "Create A layer" leaving the "Create B layer" unchecked.  The value A=0 and Component width=0.   This will create an intermediate layer for each master at ARLN=0 and component width =0 ***FIXME; this is wrong and we had a way for the other middle components do to this correctly.  i.e. there is a piecewise linear thing here but I have forgotten which script I used for that**

Now look at the font.  The ARLN should scale the arrows down to a minimum size, and the arrows should all remain the same size for each point on the axis.

To enact different minimum widths for different groups of axes use the apply_arln_floors.py script which uses the Blocks in ARLN_floor.plist.  This last plist can likely be kept as it is with differnt "Floor" values used for different design.


## ARHD axis

## ARTL axis

## Assemblies