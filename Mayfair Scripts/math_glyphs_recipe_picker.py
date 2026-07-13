#MenuTitle: Math Glyphs Recipe Picker
# -*- coding: utf-8 -*-

import os
import plistlib
import sys
import traceback
from importlib import reload

import vanilla
from AppKit import NSAttributedString, NSColor, NSForegroundColorAttributeName
from GlyphsApp import Glyphs


SCRIPT_VERSION = "2026-07-03 15:05 CDT filter-existing-exports"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RECIPE_DIR = (
    os.path.join(SCRIPT_DIR, "recipes")
    if os.path.isdir(os.path.join(SCRIPT_DIR, "recipes"))
    else SCRIPT_DIR
)
for import_path in (RECIPE_DIR, SCRIPT_DIR):
    if import_path not in sys.path:
        sys.path.insert(0, import_path)
RUNNABLE_RECIPE_KINDS = ("macro", "recipe")

import math_glyphs_recipe_lib  # noqa: E402

math_glyphs_recipe_lib = reload(math_glyphs_recipe_lib)

from math_glyphs_recipe_lib import RecipeStopped, print_warning, run_recipe  # noqa: E402


def verbosity_enabled(control):
    return bool(control.get())


def show_macro_window_for_verbose_run():
    Glyphs.clearLog()
    Glyphs.showMacroWindow()


def open_tab_for_glyphs(font, glyph_names):
    glyph_names = [name for name in glyph_names or [] if name]
    if not glyph_names:
        return False
    tab_text = "".join("/%s" % name for name in glyph_names)
    try:
        font.newTab(tab_text)
        return True
    except Exception:
        pass
    try:
        Glyphs.font.newTab(tab_text)
        return True
    except Exception:
        return False


def recipe_files():
    files = []
    for file_name in sorted(os.listdir(RECIPE_DIR)):
        if not file_name.endswith(".plist"):
            continue
        path = os.path.join(RECIPE_DIR, file_name)
        try:
            with open(path, "rb") as handle:
                plist = plistlib.load(handle)
        except Exception:
            files.append(file_name)
            continue
        if str(plist.get("kind", "")) in RUNNABLE_RECIPE_KINDS:
            files.append(file_name)
    return files


def unique_names(names):
    seen = set()
    result = []
    for name in names:
        if not name or name in seen:
            continue
        seen.add(name)
        result.append(name)
    return result


def variant_export_names(arguments):
    base_name = arguments.get("glyph")
    if not base_name:
        return []

    values = math_glyphs_recipe_lib.number_list(arguments.get("values"))
    if values is None:
        try:
            variant_count = int(arguments.get("N", 1))
        except Exception:
            variant_count = 1
    else:
        variant_count = max(0, len(values) - 1)

    try:
        start_number = int(arguments.get("startNumber", 1))
    except Exception:
        start_number = 1

    return [
        math_glyphs_recipe_lib.variant_name(base_name, number)
        for number in range(start_number, start_number + variant_count)
    ]


def color_named(name):
    if name == "red":
        method_names = ("systemRedColor", "redColor")
    elif name == "green":
        method_names = ("systemGreenColor", "greenColor")
    elif name == "orange":
        method_names = ("systemOrangeColor", "orangeColor")
    else:
        method_names = ("labelColor", "blackColor")
    for method_name in method_names:
        method = getattr(NSColor, method_name, None)
        if method is None:
            continue
        try:
            return method()
        except Exception:
            pass
    return NSColor.blackColor()


def colored_text(text, color_name=None):
    if not color_name:
        return text
    return NSAttributedString.alloc().initWithString_attributes_(
        text,
        {NSForegroundColorAttributeName: color_named(color_name)},
    )


def colored_export_status(text, state):
    if state == "missing":
        return colored_text(text, "red")
    if state == "exists":
        return colored_text(text, "green")
    if state == "partial":
        return colored_text(text, "orange")
    return text


def exported_glyph_names(file_name):
    try:
        _recipe, _template, _parameters, actions, _recipe_path, _template_path = (
            math_glyphs_recipe_lib.expanded_actions_from_recipe(file_name)
        )
    except Exception:
        return []

    names = []
    for action in actions:
        if action.get("type") != "call":
            continue
        function_name = action.get("function")
        arguments = dict(action.get("arguments", {}))
        if function_name == "createGlyph":
            glyph_name = arguments.get("glyph")
            if glyph_name and math_glyphs_recipe_lib.boolean_value(arguments.get("export", True)):
                names.append(glyph_name)
        elif function_name == "createSmartComponentVariants":
            names.extend(variant_export_names(arguments))
    return unique_names(names)


def export_existence_status(file_name, runnable):
    font = Glyphs.font
    if font is None:
        return "no font", "neutral"

    names = exported_glyph_names(file_name)
    if not names:
        return "none", "neutral"

    existing = 0
    for name in names:
        glyph = math_glyphs_recipe_lib.glyph_for_name(font, name)
        if glyph is not None and not math_glyphs_recipe_lib.glyph_is_empty(glyph):
            existing += 1

    if existing == 0:
        return ("missing" if len(names) == 1 else "missing 0/%i" % len(names)), "missing"
    if existing == len(names):
        return ("exists" if len(names) == 1 else "exists %i/%i" % (existing, len(names))), "exists"
    return "partial %i/%i" % (existing, len(names)), "partial"


def load_recipe_summary(file_name):
    path = os.path.join(RECIPE_DIR, file_name)
    try:
        with open(path, "rb") as handle:
            plist = plistlib.load(handle)
    except Exception as error:
        return dict(
            file=file_name,
            name="<error>",
            runnable=False,
            status=str(error),
            exports="error",
        )

    kind = str(plist.get("kind", ""))
    name = str(plist.get("name", file_name))
    runnable = kind in RUNNABLE_RECIPE_KINDS
    export_status, export_state = export_existence_status(file_name, runnable)
    return dict(
        file=file_name,
        name=name,
        runnable=runnable,
        status="ready",
        exports=colored_export_status(export_status, export_state),
        exportState=export_state,
    )


class MathGlyphsRecipePicker(object):
    def __init__(self):
        self.rows = []
        self.w = vanilla.FloatingWindow(
            (720, 390),
            "Math Glyph Recipes",
            minSize=(520, 260),
        )
        self.w.recipeList = vanilla.List(
            (12, 12, -12, -112),
            [],
            columnDescriptions=[
                dict(title="Recipe", key="name", width=225),
                dict(title="File", key="file", width=235),
                dict(title="Exports", key="exports", width=95),
                dict(title="Status", key="status"),
            ],
            selectionCallback=self.selection_callback,
            doubleClickCallback=self.run_callback,
        )
        self.w.verbose = vanilla.CheckBox(
            (12, -92, 155, 22),
            "Verbose Macro log",
            value=False,
        )
        self.w.overwrite = vanilla.CheckBox(
            (174, -92, 140, 22),
            "Overwrite glyphs",
            value=False,
        )
        self.w.openTab = vanilla.CheckBox(
            (318, -92, 84, 22),
            "Open tab",
            value=True,
        )
        self.w.showExisting = vanilla.CheckBox(
            (410, -92, 178, 22),
            "Show completed recipes",
            value=False,
            callback=self.refresh_callback,
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

    def refresh(self, selected_file=None):
        if selected_file is None:
            row = self.selected_row()
            if row:
                selected_file = row.get("file")
        rows = [load_recipe_summary(file_name) for file_name in recipe_files()]
        if not bool(self.w.showExisting.get()):
            rows = [row for row in rows if row.get("exportState") != "exists"]
        self.rows = rows
        self.w.recipeList.set(self.rows)
        if self.rows:
            first_runnable = 0
            for index, row in enumerate(self.rows):
                if selected_file and row.get("file") == selected_file:
                    first_runnable = index
                    break
                if row.get("runnable"):
                    first_runnable = index
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
        open_tab = bool(self.w.openTab.get())

        if verbose:
            show_macro_window_for_verbose_run()
            print("Run Math Glyphs Recipe Picker")
            print("Script version: %s" % SCRIPT_VERSION)
            print("Selected recipe: %s" % row.get("file"))
            print("Overwrite glyphs: %s" % ("yes" if overwrite_glyphs else "no"))
            print("Open tab: %s" % ("yes" if open_tab else "no"))
            print("")

        try:
            result = run_recipe(row["file"], verbose=verbose, overwrite_glyphs=overwrite_glyphs)
            if open_tab:
                glyph_names = (result or {}).get("glyphs", [])
                if not open_tab_for_glyphs(Glyphs.font, glyph_names) and verbose:
                    print_warning("Could not open a tab for created glyphs.")
        except RecipeStopped as stopped:
            Glyphs.showMacroWindow()
            print_warning(stopped)
        except Exception as error:
            Glyphs.showMacroWindow()
            print_warning(error)
            print(traceback.format_exc())
        finally:
            self.refresh(selected_file=row.get("file"))


_mathGlyphsRecipePicker = MathGlyphsRecipePicker()
