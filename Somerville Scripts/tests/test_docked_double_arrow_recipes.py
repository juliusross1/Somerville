"""Check double-arrow recipes with the real engine and the shared Glyphs API double."""
import copy
import plistlib
import re
import unittest

import test_docked_arrow_recipes as shared


BASE = 'DoubleArrowEnd.lft'
SUPPLIED = BASE + '.docked'
BATCH = 'docked_double_arrows_recipe.plist'
MAPPING = plistlib.loads((shared.RECIPES / 'docked_double_arrow_constants.plist').read_bytes())[
    'constants']['DockedDoubleArrowGlyphMap']
FIXTURES = {n: shared.parse_openstep(shared.glyph_file(n).read_text())
            for n in [*MAPPING, SUPPLIED]}


class DockedDoubleArrowTests(unittest.TestCase):
    def test_all_direct_and_nested_users_are_covered(self):
        refs = {}
        for path in shared.GLYPHS.glob('*.glyph'):
            text = path.read_text()
            name = re.search(r'\bglyphname = ([^;]+);', text)[1].strip('"')
            if not name.endswith(('.ss17', '.docked')):
                refs[name] = {a or b for a, b in re.findall(
                    r'\bref = (?:"([^"]+)"|([^;]+));', text)}
        found = {BASE}
        while True:
            expanded = found | {n for n, deps in refs.items() if deps & found}
            if expanded == found:
                break
            found = expanded
        self.assertEqual(found, set(MAPPING))
        self.assertEqual(sum(n.endswith('.ss17') for n in MAPPING.values()), 8)

    def test_individual_recipes_build_dependencies_and_preserve_all_layer_data(self):
        for source, target in MAPPING.items():
            if source == BASE:
                continue
            with self.subTest(source=source):
                font = shared.Font(FIXTURES)
                before = {n: g.snapshot() for n, g in font.glyphs.items()}
                actions = shared.actions(target + '_recipe.plist')
                self.assertEqual(actions[-1]['arguments']['glyph'], target)
                for action in actions[:-1]:
                    self.assertTrue(action['arguments']['onlyIfMissing'])
                for action in actions:
                    args = action['arguments']
                    self.assertNotEqual(args['glyph'], SUPPLIED)
                    made = shared.ENGINE.run_action(font, action)
                    expected = shared.remap_expected(font.glyphs[args['sourceGlyph']].snapshot(), MAPPING)
                    expected.pop('unicode', None)
                    expected['unicodes'] = []
                    self.assertEqual(made.snapshot(), expected)
                self.assertEqual(before, {n: font.glyphs[n].snapshot() for n in before})

    def test_batch_keeps_supplied_and_existing_dependency_even_with_overwrite(self):
        font = shared.Font(FIXTURES)
        shared.ENGINE.Glyphs.font = font
        result = shared.ENGINE.run_recipe(BATCH, verbose=False)
        self.assertEqual(set(result['glyphs']), set(MAPPING.values()) - {SUPPLIED})
        names = [SUPPLIED, 'leftDoubleArrow.rgt.docked']
        for n in names:
            font.glyphs[n].layers[0].data['width'] = 12345
        before = {n: font.glyphs[n].snapshot() for n in names}
        calls = {n: copy.deepcopy([l.calls for l in font.glyphs[n].layers]) for n in names}
        with self.assertRaises(shared.ENGINE.RecipeStopped):
            shared.ENGINE.run_recipe(BATCH, verbose=False)
        shared.ENGINE.run_recipe(BATCH, verbose=False, overwrite_glyphs=True)
        for n in names:
            self.assertEqual(font.glyphs[n].snapshot(), before[n])
            self.assertEqual([l.calls for l in font.glyphs[n].layers], calls[n])

    def test_missing_supplied_component_creates_nothing(self):
        font = shared.Font(FIXTURES)
        del font.glyphs[SUPPLIED]
        before = {n: g.snapshot() for n, g in font.glyphs.items()}
        with self.assertRaisesRegex(RuntimeError, 'missing docked dependency'):
            shared.ENGINE.run_action(font, shared.actions(BATCH)[0])
        self.assertEqual(before, {n: g.snapshot() for n, g in font.glyphs.items()})


if __name__ == '__main__':
    unittest.main(verbosity=2)
