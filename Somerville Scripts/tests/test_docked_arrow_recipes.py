"""Exercise the real recipe engine with saved glyph data and a small Glyphs API double.

This checks data preservation and dependency ordering, not native interpolation.
Run with: python3 "Somerville Scripts/tests/test_docked_arrow_recipes.py"
"""
import ast
import copy
import math
from pathlib import Path
import plistlib
import re
from types import ModuleType, SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]
RECIPES = ROOT / 'Somerville Scripts/recipes'
GLYPHS = ROOT / 'sources/SomervilleMath.glyphspackage/glyphs'
MAPPING = plistlib.loads((RECIPES / 'docked_arrow_constants.plist').read_bytes())['constants']['DockedArrowGlyphMap']
EXCLUDED_ORIGINALS = {'leftArrowTail', 'rightArrowTail'}


def parse_openstep(text):
    tokens = iter(re.findall(r'"(?:\\.|[^"\\])*"|[{}()=;,]|[^\s{}()=;,]+', text))
    current = next(tokens)

    def advance():
        nonlocal current
        current = next(tokens, None)

    def value():
        token = current
        advance()
        if token == '{':
            result = {}
            while current != '}':
                key = value()
                assert current == '='
                advance()
                result[key] = value()
                assert current == ';'
                advance()
            advance()
            return result
        if token == '(':
            result = []
            while current != ')':
                result.append(value())
                if current == ',':
                    advance()
            advance()
            return result
        if token.startswith('"'):
            return token[1:-1]
        try:
            return int(token)
        except ValueError:
            try:
                return float(token)
            except ValueError:
                return token

    result = value()
    assert current is None
    return result


def glyph_file(name):
    return GLYPHS / (re.sub('[A-Z]', lambda m: m[0] + '_', name) + '.glyph')


class GSComponent:
    def __init__(self, data):
        self.data = data
        self.reset_on_rename = False

    @property
    def componentName(self):
        return self.data['ref']

    @componentName.setter
    def componentName(self, name):
        self.data['ref'] = name
        if self.reset_on_rename:
            self.data.update(transform=(1, 0, 0, 1, 0, 0), alignment=1)

    @property
    def transform(self):
        if 'transform' in self.data:
            return self.data['transform']
        sx, sy = self.data.get('scale', (1, 1))
        radians = math.radians(self.data.get('angle', 0))
        x, y = self.data.get('pos', (0, 0))
        return (sx * math.cos(radians), sx * math.sin(radians),
                -sy * math.sin(radians), sy * math.cos(radians), x, y)

    @transform.setter
    def transform(self, value):
        self.data['transform'] = tuple(value)

    @property
    def alignment(self):
        return self.data.get('alignment', 0)

    @alignment.setter
    def alignment(self, value):
        self.data['alignment'] = value

    def baseGlyphsHasChanged(self):
        pass


class GSPath:
    def __init__(self, data):
        self.data = data


def dictionary_property(key, default=None):
    return property(lambda obj: obj.data.get(key, default),
                    lambda obj, val: obj.data.__setitem__(key, val))


class Layer:
    leftMetricsKey = dictionary_property('metricLeft')
    rightMetricsKey = dictionary_property('metricRight')
    widthMetricsKey = dictionary_property('metricWidth')
    name = dictionary_property('name', '')
    layerId = dictionary_property('layerId')
    associatedMasterId = dictionary_property('associatedMasterId')

    def __init__(self, data):
        self.data = data
        self.userData = data.setdefault('userData', {})
        self.shapes = [(GSComponent(s) if 'ref' in s else GSPath(s)) for s in data.get('shapes', [])]
        self.anchors = data.get('anchors', [])
        self.background = Layer(data['background']) if 'background' in data else None
        self.hasBackground = self.background is not None
        self.calls = []

    @property
    def isMasterLayer(self):
        return not self.associatedMasterId or self.associatedMasterId == self.layerId

    def stopUpdates(self):
        pass

    def enableFutureUpdates(self):
        pass

    def setNeedUpdateShapes(self):
        self.calls.append('shapes')

    def setNeedsAlignment(self):
        self.calls.append('alignment-dirty')

    def setNeedUpdateMetrics(self):
        self.calls.append('metrics-dirty')

    def doAlignComponents(self):
        self.calls.append('align')

    def updateMetrics(self):
        self.calls.append('metrics')

    @property
    def LSB(self):
        self.calls.append('LSB')
        return 0

    @property
    def RSB(self):
        self.calls.append('RSB')
        return 0


class Glyph:
    name = dictionary_property('glyphname')
    productionName = dictionary_property('production')
    export = dictionary_property('export', True)
    color = dictionary_property('color')
    category = dictionary_property('category')
    subCategory = dictionary_property('subCategory')
    script = dictionary_property('script')
    leftMetricsKey = dictionary_property('metricLeft')
    rightMetricsKey = dictionary_property('metricRight')
    widthMetricsKey = dictionary_property('metricWidth')

    def __init__(self, data):
        self.data = copy.deepcopy(data)
        self.layers = [Layer(d) for d in self.data.pop('layers', [])]
        self.userData = self.data.setdefault('userData', {})
        self.parent = None

    @property
    def unicodes(self):
        return self.data.get('unicodes', [self.data['unicode']] if 'unicode' in self.data else [])

    @unicodes.setter
    def unicodes(self, value):
        self.data.pop('unicode', None)
        self.data['unicodes'] = list(value)

    def snapshot(self):
        return copy.deepcopy(dict(self.data, layers=[l.data for l in self.layers], userData=self.userData))

    def copyWithOptions_(self, options):
        assert options == 63
        result = Glyph(self.snapshot())
        for old, new in zip(self.layers, result.layers):
            for old_shape, new_shape in zip(old.shapes, new.shapes):
                if isinstance(old_shape, GSComponent):
                    new_shape.reset_on_rename = old_shape.reset_on_rename
        return result


class GSGlyphReference:
    def __init__(self, glyph):
        self.glyph = glyph


class GlyphList(dict):
    def append(self, glyph):
        self[glyph.name] = glyph


class Font:
    def __init__(self, fixtures):
        self.glyphs = GlyphList({n: Glyph(d) for n, d in fixtures.items()})
        for glyph in self.glyphs.values():
            glyph.parent = self

    def disableUpdateInterface(self):
        pass

    def enableUpdateInterface(self):
        pass


def load_engine():
    path = RECIPES / 'math_glyphs_recipe_lib.py'
    tree = ast.parse(path.read_text())
    tree.body = [n for n in tree.body if not (
        isinstance(n, ast.ImportFrom) and n.module in ('GlyphsApp', 'AppKit', 'Foundation'))]
    module = ModuleType('recipe_engine_under_test')
    module.__file__ = str(path)
    module.__dict__.update(Glyphs=SimpleNamespace(font=None), GSGlyph=Glyph,
                           GSComponent=GSComponent, GSGlyphReference=GSGlyphReference)
    exec(compile(tree, str(path), 'exec'), module.__dict__)
    return module


ENGINE = load_engine()
FIXTURES = {n: parse_openstep(glyph_file(n).read_text()) for n in [*MAPPING, 'rightArrow.lft.docked']}


def actions(filename):
    return ENGINE.expanded_actions_from_recipe(filename)[3]


def remap_expected(data, mapping):
    """Independent expectation: references and metric expressions, no geometry changes."""
    if isinstance(data, dict):
        return {key: remap_expected(val, mapping) for key, val in data.items()}
    if isinstance(data, list):
        return [remap_expected(val, mapping) for val in data]
    if isinstance(data, str):
        words = re.split(r'([^A-Za-z0-9_.]+)', data)
        return ''.join(mapping.get(word, word) for word in words)
    return data


class DockedArrowTests(unittest.TestCase):
    def setUp(self):
        self.font = Font(FIXTURES)

    def test_mapping_covers_every_original_descendant(self):
        refs = {}
        for path in GLYPHS.glob('*.glyph'):
            text = path.read_text()
            match = re.search(r'\bglyphname = (?P<name>[^;]+);', text)
            if match:
                name = match['name'].strip('"')
                if '.ss17' not in name and '.docked' not in name:
                    refs[name] = {a or b for a, b in re.findall(r'\bref = (?:"([^"]+)"|([^;]+));', text)}
        found = {'rightArrow.lft'}
        while True:
            expanded = found | {n for n, dependencies in refs.items() if found & dependencies}
            if found == expanded:
                break
            found = expanded
        self.assertEqual(found - EXCLUDED_ORIGINALS, set(MAPPING))
        self.assertEqual(len(MAPPING), 82)
        self.assertEqual(sum(n.endswith('.ss17') for n in MAPPING.values()), 53)

    def test_batch_preserves_every_layer_and_original(self):
        original = {n: g.snapshot() for n, g in self.font.glyphs.items()}
        batch = actions('docked_arrows_recipe.plist')
        self.assertEqual(len(batch), 81)
        made = set()
        for action in batch:
            args = action['arguments']
            self.assertTrue(set(args['componentReplacements'].values()) <= set(self.font.glyphs))
            ENGINE.run_action(self.font, action)
            made.add(args['glyph'])
            source, target = self.font.glyphs[args['sourceGlyph']], self.font.glyphs[args['glyph']]
            expected = remap_expected(source.snapshot(), MAPPING)
            expected.pop('unicode', None)
            expected['unicodes'] = []
            self.assertEqual(target.snapshot(), expected, args['glyph'])
        self.assertEqual(made, set(MAPPING.values()) - {'rightArrow.lft.docked'})
        self.assertEqual(original, {n: self.font.glyphs[n].snapshot() for n in original})

    def test_every_individual_recipe_builds_its_dependencies(self):
        for source, target in MAPPING.items():
            if source in ('rightArrow.lft', 'rightArrow'):
                continue
            with self.subTest(source=source):
                font = Font(FIXTURES)
                recipe_actions = actions(target + '_recipe.plist')
                self.assertEqual(recipe_actions[-1]['arguments']['glyph'], target)
                for action in recipe_actions:
                    ENGINE.run_action(font, action)
                self.assertIn(target, font.glyphs)
                for action in recipe_actions[:-1]:
                    self.assertTrue(action['arguments']['onlyIfMissing'])

    def test_overwrite_guard_and_kept_dependency(self):
        action = actions('leftArrow.rgt.docked_recipe.plist')[-1]
        target = ENGINE.run_action(self.font, action)
        target.layers[0].data['width'] = 12345
        before = target.snapshot()
        with self.assertRaises(ENGINE.RecipeStopped):
            ENGINE.run_action(self.font, action)
        self.assertEqual(target.snapshot(), before)
        kept = copy.deepcopy(action)
        kept['arguments']['onlyIfMissing'] = True
        self.assertIs(ENGINE.run_action(self.font, kept, overwrite_glyphs=True), target)
        self.assertEqual(target.snapshot(), before)
        ENGINE.run_action(self.font, action, overwrite_glyphs=True)
        self.assertNotEqual(target.layers[0].data['width'], 12345)

    def test_missing_dependency_fails_without_creating_target(self):
        del self.font.glyphs['rightArrow.lft.docked']
        action = actions('leftArrow.rgt.docked_recipe.plist')[-1]
        with self.assertRaisesRegex(RuntimeError, 'missing docked dependency'):
            ENGINE.run_action(self.font, action)
        self.assertNotIn('leftArrow.rgt.docked', self.font.glyphs)

    def test_backgrounds_native_references_and_metric_name_boundaries(self):
        source = self.font.glyphs['leftArrow.rgt']
        source.leftMetricsKey = '=rightArrow.lft.long+10'
        source.rightMetricsKey = '=rightArrow.lft+5'
        background = Layer({'shapes': [{'ref': 'rightArrow.lft', 'pos': [10, 20]}], 'width': 25})
        source.layers[0].background = background
        source.layers[0].hasBackground = True
        source.layers[0].data['background'] = background.data
        source.userData['native'] = [GSGlyphReference(source), GSGlyphReference(self.font.glyphs['rightArrow.lft'])]
        action = actions('leftArrow.rgt.docked_recipe.plist')[-1]
        target = ENGINE.run_action(self.font, action)
        self.assertEqual(target.leftMetricsKey, '=rightArrow.lft.long.docked+10')
        self.assertEqual(target.rightMetricsKey, '=rightArrow.lft.docked+5')
        self.assertEqual(target.layers[0].background.shapes[0].componentName, 'rightArrow.lft.docked')
        references = target.userData['native']
        self.assertIs(references[0].glyph, target)
        self.assertIs(references[1].glyph, self.font.glyphs['rightArrow.lft.docked'])
        self.assertEqual(source.layers[0].background.shapes[0].componentName, 'rightArrow.lft')
        overwritten = ENGINE.run_action(self.font, action, overwrite_glyphs=True)
        self.assertIs(overwritten, target)
        self.assertIs(overwritten.userData['native'][0].glyph, target)

    def test_transform_and_alignment_survive_a_resetting_name_setter(self):
        source = self.font.glyphs['leftArrow.rgt']
        component = source.layers[0].shapes[0]
        component.data['transform'] = (-1, 0, 0, 1, 450, 25)
        component.data['alignment'] = -1
        component.reset_on_rename = True
        target = ENGINE.run_action(self.font, actions('leftArrow.rgt.docked_recipe.plist')[-1])
        self.assertEqual(target.layers[0].shapes[0].transform, component.transform)
        self.assertEqual(target.layers[0].shapes[0].alignment, -1)

    def test_batch_skips_existing_right_arrow_and_refreshes_only_new_masters(self):
        existing = Glyph(dict(glyphname='rightArrow.ss17', layers=[dict(
            layerId='keep', shapes=[dict(ref='rightArrow.lft.docked')], width=12345)]))
        self.font.glyphs.append(existing)
        before = existing.snapshot()
        ENGINE.Glyphs.font = self.font
        result = ENGINE.run_recipe('docked_arrows_recipe.plist', verbose=False)
        self.assertEqual(len(result['glyphs']), 81)
        self.assertEqual(existing.snapshot(), before)
        self.assertEqual(existing.layers[0].calls, [])
        for original in MAPPING:
            self.assertTrue(all(not layer.calls for layer in self.font.glyphs[original].layers))
        for source, target in MAPPING.items():
            if source in ('rightArrow.lft', 'rightArrow'):
                continue
            for layer in self.font.glyphs[target].layers:
                if layer.isMasterLayer:
                    self.assertIn('metrics', layer.calls)
                else:
                    self.assertEqual(layer.calls, ['shapes', 'alignment-dirty', 'metrics-dirty'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
