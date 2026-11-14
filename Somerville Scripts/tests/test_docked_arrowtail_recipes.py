"""Validate tail-arrow recipes with the real engine and the shared Glyphs API double.

Run with: python3 "Somerville Scripts/tests/test_docked_arrowtail_recipes.py"
"""
import copy
import plistlib
import re
import unittest

import test_docked_arrow_recipes as shared


RECIPES = shared.RECIPES
BASE = '_smart.ArrowTail'
SUPPLIED = BASE + '.docked'
EXCLUDED_ORIGINALS = {'leftDoubleArrowTail', 'rightDoubleArrowTail'}
BATCH = 'docked_tail_arrows_recipe.plist'
MAPPING = plistlib.loads((RECIPES / 'docked_tail_arrow_constants.plist').read_bytes())[
    'constants']['DockedTailArrowGlyphMap']
FIXTURES = {name: shared.parse_openstep(shared.glyph_file(name).read_text())
            for name in [*MAPPING, SUPPLIED]}
ENGINE = shared.ENGINE


class DockedTailArrowTests(unittest.TestCase):
    def setUp(self):
        self.font = shared.Font(FIXTURES)

    def test_mapping_covers_all_direct_and_nested_tail_users(self):
        refs = {}
        for path in shared.GLYPHS.glob('*.glyph'):
            text = path.read_text()
            name = re.search(r'\bglyphname = ([^;]+);', text)[1].strip('"')
            if not name.endswith(('.ss17', '.docked')):
                refs[name] = {a or b for a, b in re.findall(
                    r'\bref = (?:"([^"]+)"|([^;]+));', text)}
        found = {BASE}
        while True:
            expanded = found | {name for name, deps in refs.items() if deps & found}
            if expanded == found:
                break
            found = expanded
        self.assertEqual(found - EXCLUDED_ORIGINALS, set(MAPPING))
        self.assertEqual(sum(name.endswith('.ss17') for name in MAPPING.values()), 12)
        self.assertEqual(len(MAPPING), 15)
        for name in EXCLUDED_ORIGINALS | shared.EXCLUDED_ORIGINALS:
            self.assertFalse((RECIPES / (name + '.ss17_recipe.plist')).exists())
            self.assertFalse(shared.glyph_file(name + '.ss17').exists())

    def test_batch_preserves_layers_metadata_and_supplied_component(self):
        originals = {name: glyph.snapshot() for name, glyph in self.font.glyphs.items()}
        for action in shared.actions(BATCH):
            args = action['arguments']
            self.assertNotEqual(args['glyph'], SUPPLIED)
            self.assertTrue(set(args['componentReplacements'].values()) <= set(self.font.glyphs))
            target = ENGINE.run_action(self.font, action)
            source = self.font.glyphs[args['sourceGlyph']]
            expected = shared.remap_expected(source.snapshot(), MAPPING)
            expected.pop('unicode', None)
            expected['unicodes'] = []
            self.assertEqual(target.snapshot(), expected, target.name)
        self.assertEqual(set(self.font.glyphs) - set(originals), set(MAPPING.values()) - {SUPPLIED})
        self.assertEqual(originals, {name: self.font.glyphs[name].snapshot() for name in originals})

    def test_individual_recipes_build_dependencies_and_reach_new_tail(self):
        for source, target in MAPPING.items():
            if source == BASE:
                continue
            with self.subTest(source=source):
                font = shared.Font(FIXTURES)
                actions = shared.actions(target + '_recipe.plist')
                self.assertEqual(actions[-1]['arguments']['glyph'], target)
                for action in actions[:-1]:
                    self.assertTrue(action['arguments']['onlyIfMissing'])
                for action in actions:
                    ENGINE.run_action(font, action)

                def descendants(name):
                    if name == SUPPLIED:
                        return {name}
                    if name not in font.glyphs:
                        return set()
                    children = {c.componentName for layer in font.glyphs[name].layers
                                for c in layer.shapes if isinstance(c, shared.GSComponent)}
                    return children | set().union(*(descendants(c) for c in children))

                used = descendants(target)
                self.assertIn(SUPPLIED, used)
                self.assertNotIn(BASE, used)

    def test_missing_supplied_tail_fails_before_creating_any_glyph(self):
        del self.font.glyphs[SUPPLIED]
        originals = {name: glyph.snapshot() for name, glyph in self.font.glyphs.items()}
        with self.assertRaisesRegex(RuntimeError, 'missing docked dependency'):
            ENGINE.run_action(self.font, shared.actions(BATCH)[0])
        self.assertEqual(originals, {name: glyph.snapshot() for name, glyph in self.font.glyphs.items()})

    def test_existing_shared_components_survive_overwrite_and_spacing_refresh(self):
        ENGINE.Glyphs.font = self.font
        result = ENGINE.run_recipe(BATCH, verbose=False)
        self.assertEqual(len(result['glyphs']), 14)
        names = ['ArrowEnd.lft.docked', 'leftTailArrow.rgt.docked', SUPPLIED]
        for name in names:
            self.font.glyphs[name].layers[0].data['width'] = 12345
        snapshots = {name: self.font.glyphs[name].snapshot() for name in names}
        calls = {name: copy.deepcopy([layer.calls for layer in self.font.glyphs[name].layers])
                 for name in names}
        ENGINE.run_recipe(BATCH, verbose=False, overwrite_glyphs=True)
        for name in names:
            self.assertEqual(self.font.glyphs[name].snapshot(), snapshots[name])
            self.assertEqual([layer.calls for layer in self.font.glyphs[name].layers], calls[name])

    def test_variant_overwrite_guard(self):
        actions = shared.actions('rightTwoHeadedArrowWithTail.ss17_recipe.plist')
        for action in actions:
            ENGINE.run_action(self.font, action)
        target = self.font.glyphs['rightTwoHeadedArrowWithTail.ss17']
        self.assertEqual(target.productionName, target.name)
        target.layers[0].data['width'] = 12345
        target.productionName = 'staleProductionName'
        before = target.snapshot()
        with self.assertRaises(ENGINE.RecipeStopped):
            ENGINE.run_action(self.font, actions[-1])
        self.assertEqual(target.snapshot(), before)
        ENGINE.run_action(self.font, actions[-1], overwrite_glyphs=True)
        self.assertNotEqual(target.layers[0].data['width'], 12345)
        self.assertEqual(target.productionName, target.name)


if __name__ == '__main__':
    unittest.main(verbosity=2)
