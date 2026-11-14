# Docked arrow recipes

Run **All Docked Arrows** in the Math Glyphs Recipe Picker to build the original family.
Individual entries, such as **LeftArrow Docked**, create their missing docked
dependencies first. Reopen the picker after updating these scripts so it reloads
the shared recipe engine.

For the arrows that use `_smart.ArrowTail`, run **All Docked Tail Arrows**
(`docked_tail_arrows_recipe.plist`). This separate batch creates 12 `.ss17`
variants using the existing `_smart.ArrowTail.docked`, through
`ArrowEnd.lft.docked` and `leftTailArrow.rgt.docked`. The supplied smart component
must already exist and is never recreated or overwritten. These recipes cover
`leftTailArrow`, `rightTailArrow`, and the single- and
two-headed arrows with tails and vertical strokes, in both directions.

Each of the 12 variants and two shared components also has an individual
**Docked** recipe. Individual recipes create missing dependencies first and
preserve existing dependencies, including when **Overwrite glyphs** is enabled.
To rebuild a shared component, select its own recipe with **Overwrite glyphs**.
The tail recipes use `docked_tail_arrow_constants.plist` and preserve every layer,
width, transform, smart value, anchor, background and MATH assembly reference
from the current original glyphs. They clear Unicode assignments on the copies.
Like the original batch, they refresh metrics on master layers only.

For the double arrows that use `DoubleArrowEnd.lft`, run **All Docked Double
Arrows** (`docked_double_arrows_recipe.plist`). It creates eight `.ss17` variants:
`leftDoubleArrow`, `rightDoubleArrow`, `leftDoubleStrokeArrow`,
`rightDoubleStrokeArrow`, `leftDoubleArrowWithVerticalStroke`,
`rightDoubleArrowWithVerticalStroke`, `leftLongDoubleArrow` and
`rightLongDoubleArrow`. The existing `DoubleArrowEnd.lft.docked` is required
and is never recreated or overwritten. The batch creates
`leftDoubleArrow.rgt.docked` only if missing. Each variant and the shared
component also has an individual **Docked** recipe, with the same preservation
and overwrite behavior as the tail recipes. Their mapping is in
`docked_double_arrow_constants.plist`.

The base `rightArrow.lft.docked` must already exist. The existing
**RightArrow Docked** recipe is retained without changes; the batch also leaves
an existing `rightArrow.ss17` alone. The family has individual recipes and
one batch recipe, covering 53 `.ss17` arrow names (including `rightArrow.ss17`)
and 29 `.docked` component names (including the existing base).

Each new recipe copies its original glyph **as it currently exists in the open
font**, including every master, intermediate layer, background, path, anchor,
component transform, alignment setting and smart value. It changes affected
component names according to `docked_arrow_constants.plist`, with corresponding
MATH assembly/variant references and metrics keys remapped. Unicode assignments
are cleared on the copies; export settings are inherited. Shared, unaffected
components keep their original names. No component is decomposed or flattened.

This mirrors the current glyphs rather than reconstructing their older recipes.
In particular, the `.FloorA`, `.FloorB` and `.FloorC` parts used by ten current
arrows are preserved. Flipped and rotated components get separate docked copies
at the same level of nesting. This includes vertical arrows that depend on
rotated horizontal parts and the two long parts that have no original recipe.

Existing original glyphs and original recipe plists are never edited by these
recipes. Missing dependencies are created; existing docked dependencies are kept
and excluded from the spacing refresh. To update an existing docked target from
its original, select its own recipe with **Overwrite glyphs** enabled. In the
batch, this updates all new docked targets, while retaining the already-working
`rightArrow.ss17`.

New copies refresh metrics on master layers only. Intermediate-layer caches are
invalidated for normal on-demand updates, avoiding the eager interpolation that
caused the earlier beachball.

## Arrow names

| Original | Docked alternate |
| --- | --- |
| `downArrowToBar` | `downArrowToBar.ss17` |
| `downBarbLeftHarpoon` | `downBarbLeftHarpoon.ss17` |
| `downBarbRightHarpoon` | `downBarbRightHarpoon.ss17` |
| `downHarpoonWithBarbLeftToBar` | `downHarpoonWithBarbLeftToBar.ss17` |
| `downHarpoonWithBarbRightToBar` | `downHarpoonWithBarbRightToBar.ss17` |
| `downTwoheadedArrow` | `downTwoheadedArrow.ss17` |
| `leftAndRightArrow` | `leftAndRightArrow.ss17` |
| `leftArrow` | `leftArrow.ss17` |
| `leftBarbDownHarpoon` | `leftBarbDownHarpoon.ss17` |
| `leftBarbUpHarpoon` | `leftBarbUpHarpoon.ss17` |
| `leftDoublePairedArrow` | `leftDoublePairedArrow.ss17` |
| `leftDoubleVerticalStrokeArrow` | `leftDoubleVerticalStrokeArrow.ss17` |
| `leftHarpoonWithBarbDownAboveRightHarpoonWithBarbDown` | `leftHarpoonWithBarbDownAboveRightHarpoonWithBarbDown.ss17` |
| `leftHarpoonWithBarbDownBelowLongDash` | `leftHarpoonWithBarbDownBelowLongDash.ss17` |
| `leftHarpoonWithBarbDownToBar` | `leftHarpoonWithBarbDownToBar.ss17` |
| `leftHarpoonWithBarbUpAboveLeftHarpoonWithBarbDown` | `leftHarpoonWithBarbUpAboveLeftHarpoonWithBarbDown.ss17` |
| `leftHarpoonWithBarbUpAboveRightHarpoonWithBarbUp` | `leftHarpoonWithBarbUpAboveRightHarpoonWithBarbUp.ss17` |
| `leftHarpoonWithBarbUpToBar` | `leftHarpoonWithBarbUpToBar.ss17` |
| `leftLongArrow` | `leftLongArrow.ss17` |
| `leftOverRightHarpoon` | `leftOverRightHarpoon.ss17` |
| `leftStrokeArrow` | `leftStrokeArrow.ss17` |
| `leftTabArrow` | `leftTabArrow.ss17` |
| `leftToBarOverRightToBarArrow` | `leftToBarOverRightToBarArrow.ss17` |
| `leftTwoHeadedArrowWithDoubleVerticalStroke` | `leftTwoHeadedArrowWithDoubleVerticalStroke.ss17` |
| `leftTwoHeadedArrowWithVerticalStroke` | `leftTwoHeadedArrowWithVerticalStroke.ss17` |
| `leftTwoheadedArrow` | `leftTwoheadedArrow.ss17` |
| `leftVerticalStrokeArrow` | `leftVerticalStrokeArrow.ss17` |
| `rightArrow` | `rightArrow.ss17` |
| `rightBarbUpHarpoon` | `rightBarbUpHarpoon.ss17` |
| `rightBarbdownHarpoon` | `rightBarbdownHarpoon.ss17` |
| `rightDoublePairedArrow` | `rightDoublePairedArrow.ss17` |
| `rightDoubleVerticalStrokeArrow` | `rightDoubleVerticalStrokeArrow.ss17` |
| `rightHarpoonWithBarbDownAboveLeftHarpoonWithBarbDown` | `rightHarpoonWithBarbDownAboveLeftHarpoonWithBarbDown.ss17` |
| `rightHarpoonWithBarbDownToBar` | `rightHarpoonWithBarbDownToBar.ss17` |
| `rightHarpoonWithBarbUpAboveLeftHarpoonWithBarbUp` | `rightHarpoonWithBarbUpAboveLeftHarpoonWithBarbUp.ss17` |
| `rightHarpoonWithBarbUpAboveRightHarpoonWithBarbDown` | `rightHarpoonWithBarbUpAboveRightHarpoonWithBarbDown.ss17` |
| `rightHarpoonWithBarbUpToBar` | `rightHarpoonWithBarbUpToBar.ss17` |
| `rightLongArrow` | `rightLongArrow.ss17` |
| `rightOverLeftArrow` | `rightOverLeftArrow.ss17` |
| `rightOverLeftHarpoon` | `rightOverLeftHarpoon.ss17` |
| `rightStrokeArrow` | `rightStrokeArrow.ss17` |
| `rightTabArrow` | `rightTabArrow.ss17` |
| `rightTwoHeadedArrowWithDoubleVerticalStroke` | `rightTwoHeadedArrowWithDoubleVerticalStroke.ss17` |
| `rightTwoHeadedArrowWithVerticalStroke` | `rightTwoHeadedArrowWithVerticalStroke.ss17` |
| `rightTwoheadedArrow` | `rightTwoheadedArrow.ss17` |
| `rightVerticalStrokeArrow` | `rightVerticalStrokeArrow.ss17` |
| `upArrow` | `upArrow.ss17` |
| `upArrowToBar` | `upArrowToBar.ss17` |
| `upBarbLeftharpoon` | `upBarbLeftharpoon.ss17` |
| `upBarbRightharpoon` | `upBarbRightharpoon.ss17` |
| `upHarpoonWithBarbLeftToBar` | `upHarpoonWithBarbLeftToBar.ss17` |
| `upHarpoonWithBarbRightToBar` | `upHarpoonWithBarbRightToBar.ss17` |
| `upTwoHeadedArrow` | `upTwoHeadedArrow.ss17` |

## Component names

| Original | Docked component |
| --- | --- |
| `downArrow.top` | `downArrow.top.docked` |
| `leftAndRightArrow.lft` | `leftAndRightArrow.lft.docked` |
| `leftAndRightArrow.rgt` | `leftAndRightArrow.rgt.docked` |
| `leftArrow.rgt` | `leftArrow.rgt.docked` |
| `leftArrow.rgt.long` | `leftArrow.rgt.long.docked` |
| `leftDoublePairedArrow.rgt` | `leftDoublePairedArrow.rgt.docked` |
| `leftHarpoonWithBarbDownAboveRightHarpoonWithBarbDown.lft` | `leftHarpoonWithBarbDownAboveRightHarpoonWithBarbDown.lft.docked` |
| `leftHarpoonWithBarbDownAboveRightHarpoonWithBarbDown.rgt` | `leftHarpoonWithBarbDownAboveRightHarpoonWithBarbDown.rgt.docked` |
| `leftHarpoonWithBarbDownBelowLongDash.rgt` | `leftHarpoonWithBarbDownBelowLongDash.rgt.docked` |
| `leftHarpoonWithBarbUpAboveLeftHarpoonWithBarbDown.rgt` | `leftHarpoonWithBarbUpAboveLeftHarpoonWithBarbDown.rgt.docked` |
| `leftHarpoonWithBarbUpAboveRightHarpoonWithBarbUp.lft` | `leftHarpoonWithBarbUpAboveRightHarpoonWithBarbUp.lft.docked` |
| `leftHarpoonWithBarbUpAboveRightHarpoonWithBarbUp.rgt` | `leftHarpoonWithBarbUpAboveRightHarpoonWithBarbUp.rgt.docked` |
| `leftOverRightHarpoon.lft` | `leftOverRightHarpoon.lft.docked` |
| `leftOverRightHarpoon.rgt` | `leftOverRightHarpoon.rgt.docked` |
| `leftToBarOverRightToBarArrow.lft` | `leftToBarOverRightToBarArrow.lft.docked` |
| `leftToBarOverRightToBarArrow.rgt` | `leftToBarOverRightToBarArrow.rgt.docked` |
| `rightArrow.lft` | `rightArrow.lft.docked` |
| `rightArrow.lft.long` | `rightArrow.lft.long.docked` |
| `rightDoublePairedArrow.lft` | `rightDoublePairedArrow.lft.docked` |
| `rightHarpoonWithBarbDownAboveLeftHarpoonWithBarbDown.lft` | `rightHarpoonWithBarbDownAboveLeftHarpoonWithBarbDown.lft.docked` |
| `rightHarpoonWithBarbDownAboveLeftHarpoonWithBarbDown.rgt` | `rightHarpoonWithBarbDownAboveLeftHarpoonWithBarbDown.rgt.docked` |
| `rightHarpoonWithBarbUpAboveLeftHarpoonWithBarbUp.lft` | `rightHarpoonWithBarbUpAboveLeftHarpoonWithBarbUp.lft.docked` |
| `rightHarpoonWithBarbUpAboveLeftHarpoonWithBarbUp.rgt` | `rightHarpoonWithBarbUpAboveLeftHarpoonWithBarbUp.rgt.docked` |
| `rightHarpoonWithBarbUpAboveRightHarpoonWithBarbDown.lft` | `rightHarpoonWithBarbUpAboveRightHarpoonWithBarbDown.lft.docked` |
| `rightOverLeftArrow.lft` | `rightOverLeftArrow.lft.docked` |
| `rightOverLeftArrow.rgt` | `rightOverLeftArrow.rgt.docked` |
| `rightOverLeftHarpoon.lft` | `rightOverLeftHarpoon.lft.docked` |
| `rightOverLeftHarpoon.rgt` | `rightOverLeftHarpoon.rgt.docked` |
| `upArrow.bot` | `upArrow.bot.docked` |

## Validation

Run the standalone tests from the project root:

```sh
python3 "Somerville Scripts/tests/test_docked_arrow_recipes.py"
python3 "Somerville Scripts/tests/test_docked_arrowtail_recipes.py"
python3 "Somerville Scripts/tests/test_docked_double_arrow_recipes.py"
```

The tests exercise the real recipe action and expansion functions outside
Glyphs, using the saved glyph layers as fixtures. They check the full dependency
graph, layer and component data, MATH references, overwrite guards, backgrounds,
and preservation of original glyph data. They do not run Glyphs' native
interpolator or validate the final rendered outlines.
