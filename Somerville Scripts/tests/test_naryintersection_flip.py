"""Check centered reflection and placement for every naryintersection size."""
import ast
from pathlib import Path
import plistlib
from types import ModuleType, SimpleNamespace
import unittest


RECIPES = Path(__file__).resolve().parents[1] / "recipes"
path = RECIPES / "math_glyphs_recipe_lib.py"
tree = ast.parse(path.read_text())
tree.body = [node for node in tree.body if not (
    isinstance(node, ast.ImportFrom)
    and node.module in ("GlyphsApp", "AppKit", "Foundation")
)]
ENGINE = ModuleType("recipe_engine")
exec(compile(tree, str(path), "exec"), ENGINE.__dict__)


class Component:
    componentName = "_smart.naryunion"
    points = ((0, -30), (50, -20), (50, 200), (0, 180))

    def __init__(self, size, shear):
        self.transform = (1, shear, 0, 1 + size / 10, 35, 120 + size * 17)

    def transformed_points(self):
        a, b, c, d, tx, ty = self.transform
        return [(a*x + c*y + tx, b*x + d*y + ty) for x, y in self.points]

    @property
    def bounds(self):
        xs, ys = zip(*self.transformed_points())
        return ((min(xs), min(ys)), (max(xs)-min(xs), max(ys)-min(ys)))

    def setDisableAlignment_(self, value):
        # Simulate Glyphs changing placement when automatic alignment is disabled.
        a, b, c, d, tx, ty = self.transform
        self.transform = (a, b, c, d, tx, ty - 75)


class CenteredFlipTests(unittest.TestCase):
    def test_base_and_all_variants_keep_bounds_when_alignment_moves_them(self):
        self.check_recipe("naryintersection_recipe.plist")

    def test_serif_base_and_all_variants_keep_bounds_when_alignment_moves_them(self):
        self.check_recipe("naryintersection.serif_recipe.plist")

    def check_recipe(self, filename):
        recipe = plistlib.loads((RECIPES / filename).read_bytes())
        args = next(a["arguments"] for a in recipe["actions"]
                    if a.get("function") == "flipComponents").copy()
        constants = plistlib.loads((RECIPES / "recipe_constants.plist").read_bytes())
        count = int(constants["constants"]["SizeVariantCount"])
        args["variantCount"] = count
        font = SimpleNamespace(glyphs={})
        originals = []
        for index, name in enumerate(ENGINE.variant_names(args["glyph"], count)):
            layers = []
            for shear in (0, 0.2):
                component = Component(index, shear)
                component.componentName = args["components"][0]
                originals.append((component, component.transformed_points(), component.bounds))
                layers.append(SimpleNamespace(components=[component]))
            font.glyphs[name] = SimpleNamespace(layers=layers)
        self.assertEqual(ENGINE.action_flip_components(font, **args), 2*(count+1))
        for component, points, bounds in originals:
            min_y = bounds[0][1]
            max_y = min_y + bounds[1][1]
            self.assertAlmostEqual(component.bounds[0][1], min_y)
            self.assertAlmostEqual(component.bounds[1][1], max_y-min_y)
            for (old_x, old_y), (new_x, new_y) in zip(points, component.transformed_points()):
                self.assertAlmostEqual(new_x, old_x)
                self.assertAlmostEqual(new_y, min_y + max_y - old_y)


if __name__ == "__main__":
    unittest.main()
