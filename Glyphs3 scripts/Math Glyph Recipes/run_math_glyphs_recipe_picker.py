#MenuTitle: Run Math Glyphs Recipe Picker
# -*- coding: utf-8 -*-

import os
import plistlib
import sys
import traceback
from importlib import reload

import vanilla
from GlyphsApp import Glyphs


SCRIPT_VERSION = "2026-07-02 12:35 CDT initial"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
RUNNABLE_RECIPE_KINDS = ("macro", "recipe")

import math_glyphs_recipe_lib  # noqa: E402

math_glyphs_recipe_lib = reload(math_glyphs_recipe_lib)

from math_glyphs_recipe_lib import print_warning, run_recipe  # noqa: E402


def verbosity_enabled(control):
    return bool(control.get())


def show_macro_window_for_verbose_run():
    Glyphs.clearLog()
    Glyphs.showMacroWindow()


def recipe_files():
    files = []
    for file_name in sorted(os.listdir(SCRIPT_DIR)):
        if file_name.endswith(".plist"):
            files.append(file_name)
    return files


def load_recipe_summary(file_name):
    path = os.path.join(SCRIPT_DIR, file_name)
    try:
        with open(path, "rb") as handle:
            plist = plistlib.load(handle)
    except Exception as error:
        return dict(
            file=file_name,
            name="<error>",
            kind="<error>",
            runnable=False,
            status=str(error),
        )

    kind = str(plist.get("kind", ""))
    name = str(plist.get("name", file_name))
    runnable = kind in RUNNABLE_RECIPE_KINDS
    return dict(
        file=file_name,
        name=name,
        kind=kind or "<unknown>",
        runnable=runnable,
        status="ready" if runnable else "not runnable",
    )


class MathGlyphsRecipePicker(object):
    def __init__(self):
        self.rows = []
        self.w = vanilla.FloatingWindow(
            (640, 360),
            "Math Glyph Recipes",
            minSize=(520, 260),
        )
        self.w.recipeList = vanilla.List(
            (12, 12, -12, -82),
            [],
            columnDescriptions=[
                dict(title="Recipe", key="name", width=190),
                dict(title="File", key="file", width=230),
                dict(title="Kind", key="kind", width=80),
                dict(title="Status", key="status"),
            ],
            selectionCallback=self.selection_callback,
            doubleClickCallback=self.run_callback,
        )
        self.w.verbose = vanilla.CheckBox(
            (12, -62, 155, 22),
            "Verbose Macro log",
            value=False,
        )
        self.w.overwrite = vanilla.CheckBox(
            (174, -62, 140, 22),
            "Overwrite glyphs",
            value=False,
        )
        self.w.refreshButton = vanilla.Button(
            (-236, -64, 104, 26),
            "Refresh",
            callback=self.refresh_callback,
        )
        self.w.runButton = vanilla.Button(
            (-124, -64, 112, 26),
            "Run Recipe",
            callback=self.run_callback,
        )
        self.refresh()
        self.w.open()

    def selected_row(self):
        selection = list(self.w.recipeList.getSelection() or [])
        if not selection:
            return None
        index = selection[0]
        if index < 0 or index >= len(self.rows):
            return None
        return self.rows[index]

    def refresh(self):
        self.rows = [load_recipe_summary(file_name) for file_name in recipe_files()]
        self.w.recipeList.set(self.rows)
        if self.rows:
            first_runnable = 0
            for index, row in enumerate(self.rows):
                if row.get("runnable"):
                    first_runnable = index
                    break
            self.w.recipeList.setSelection([first_runnable])
        self.selection_callback(None)

    def refresh_callback(self, sender):
        self.refresh()

    def selection_callback(self, sender):
        row = self.selected_row()
        self.w.runButton.enable(bool(row and row.get("runnable")))

    def run_callback(self, sender):
        row = self.selected_row()
        if not row:
            return
        verbose = verbosity_enabled(self.w.verbose)
        if not row.get("runnable"):
            Glyphs.showMacroWindow()
            print_warning("%s is not a runnable recipe." % row.get("file"))
            return
        overwrite_glyphs = bool(self.w.overwrite.get())

        if verbose:
            show_macro_window_for_verbose_run()
            print("Run Math Glyphs Recipe Picker")
            print("Script version: %s" % SCRIPT_VERSION)
            print("Selected recipe: %s" % row.get("file"))
            print("Overwrite glyphs: %s" % ("yes" if overwrite_glyphs else "no"))
            print("")

        try:
            run_recipe(row["file"], verbose=verbose, overwrite_glyphs=overwrite_glyphs)
        except Exception as error:
            Glyphs.showMacroWindow()
            print_warning(error)
            print(traceback.format_exc())


_mathGlyphsRecipePicker = MathGlyphsRecipePicker()
