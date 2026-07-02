#MenuTitle: Run Math Glyphs Recipe
# -*- coding: utf-8 -*-

import os
import sys
import traceback
from importlib import reload

from GlyphsApp import Glyphs


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import math_glyphs_recipe_lib  # noqa: E402

math_glyphs_recipe_lib = reload(math_glyphs_recipe_lib)

from math_glyphs_recipe_lib import (  # noqa: E402
    DEFAULT_RECIPE_FILE,
    SCRIPT_VERSION,
    VERBOSE,
    print_warning,
    run_recipe,
)


if VERBOSE:
    Glyphs.clearLog()
    Glyphs.showMacroWindow()
    print("Run Math Glyphs Recipe")
    print("Launcher version: %s" % SCRIPT_VERSION)

try:
    run_recipe(DEFAULT_RECIPE_FILE, verbose=VERBOSE)
except Exception as error:
    Glyphs.showMacroWindow()
    print_warning(error)
    print(traceback.format_exc())
