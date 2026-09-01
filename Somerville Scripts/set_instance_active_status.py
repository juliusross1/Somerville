#MenuTitle: Set Instance Active Status
# -*- coding: utf-8 -*-

"""
Choose which static instances should be active/exporting by selecting allowed
Weight, Width, and Optical size values.

The script opens a small window with one checkbox column for each axis group:

- Weight
- Width
- Optical sizes

It scans the font's instances and includes only complete static instances that
have usable values for all three axis groups. Axis values of 0 are ignored, so
placeholder or incomplete instances do not appear in the checkbox lists.

The checkbox state is initialized from the instances that are currently active
or exporting. Changing checkboxes does not immediately edit the font; click
"Set active instances" to apply the selection. An instance is made active only
when all three of its axis values are selected. Otherwise it is made inactive.

Use the small + or - buttons above a column to select or clear that whole axis
group. Use the + or - buttons at the bottom to select or clear every checkbox.

The script writes both modern and older Glyphs instance active/export flags
where available, so it works across different Glyphs API spellings.
"""

import re

import vanilla
from GlyphsApp import Glyphs


SCRIPT_VERSION = "2026-06-30 10:35 CDT explicit-apply"
IGNORED_AXIS_VALUES = (0,)

AXIS_GROUPS = (
    ("weights", "Weight", ("Weight",)),
    ("widths", "Width", ("Width",)),
    ("optical_sizes", "Optical sizes", ("Optical size", "Optical Size")),
)

DEFAULT_AXIS_VALUE_NAMES = {
    "weights": {
        360: "SemiLight",
        400: "Regular",
        475: "Medium",
        500: "Medium",
        550: "SemiBold",
        600: "SemiBold",
        650: "Bold",
        700: "ExtraBold",
        750: "ExtraBold",
        800: "ExtraBold",
        900: "Black",
    },
    "widths": {
        95: "SemiCondensed",
        100: "Normal",
        113: "SemiExpanded",
    },
    "optical_sizes": {
        5: "Micro",
        6: "Minuscule",
        7: "Miniature",
        8: "Caption",
        12: "Regular",
        16: "SubHeading",
        21: "Trumpet",
        32: "Headline",
        48: "Display",
        72: "Titling",
        96: "Hairline",
        1200: "Needlepoint",
    },
}

KNOWN_AXIS_VALUE_NAMES = {
    "weights": (
        "SemiLight",
        "Regular",
        "Medium",
        "SemiBold",
        "Bold",
        "ExtraBold",
        "Black",
    ),
    "widths": (
        "SemiCondensed",
        "Normal",
        "SemiExpanded",
    ),
    "optical_sizes": (
        "Micro",
        "Minuscule",
        "Miniature",
        "Caption",
        "Regular",
        "SubHeading",
        "Trumpet",
        "Headline",
        "Display",
        "Titling",
        "Hairline",
        "Needlepoint",
    ),
}


def axis_name(axis):
    value = getattr(axis, "name", "")
    if callable(value):
        try:
            value = value()
        except Exception:
            value = ""
    return str(value or "")


def axis_id(axis):
    for attribute_name in ("axisId", "id"):
        value = getattr(axis, attribute_name, None)
        if callable(value):
            try:
                value = value()
            except Exception:
                value = None
        if value:
            return str(value)
    return None


def axis_info(font, wanted_axis_names):
    wanted_names = set(wanted_axis_names)
    for index, axis in enumerate(font.axes):
        if axis_name(axis) in wanted_names:
            return index, axis_id(axis), axis_name(axis)
    raise ValueError("Could not find any axis named %s" % ", ".join(wanted_axis_names))


def raw_axes_values(instance):
    values = getattr(instance, "axesValues", None)
    if callable(values):
        values = values()
    return values


def dictionary_keys(value):
    try:
        return list(value.keys())
    except Exception:
        return None


def dictionary_copy(value):
    keys = dictionary_keys(value)
    if keys is None:
        return None
    return dict((key, value[key]) for key in keys)


def number_value(value):
    for attribute_name in ("value", "position", "pos", "floatValue"):
        attribute_value = getattr(value, attribute_name, None)
        if attribute_value is None:
            continue
        if callable(attribute_value):
            try:
                attribute_value = attribute_value()
            except Exception:
                continue
        if attribute_value is value:
            continue
        try:
            return number_value(attribute_value)
        except Exception:
            pass

    try:
        numeric_value = float(value)
    except Exception:
        match = re.search(r":\s*(-?\d+(?:\.\d+)?)\s*/", repr(value))
        if match is None:
            raise ValueError("Expected a numeric axis value, got %r" % value)
        numeric_value = float(match.group(1))

    if numeric_value.is_integer():
        return int(numeric_value)
    return numeric_value


def value_key(value):
    return number_value(value)


def is_ignored_axis_value(value):
    try:
        return number_value(value) in IGNORED_AXIS_VALUES
    except Exception:
        return False


def value_label(value):
    numeric_value = number_value(value)
    if isinstance(numeric_value, float) and numeric_value.is_integer():
        numeric_value = int(numeric_value)
    return str(numeric_value)


def normalized_name(value):
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def axis_value_label(axis_key, value, axis_value_names=None):
    label = value_label(value)
    axis_name_value = None

    if axis_value_names is not None:
        axis_name_value = axis_value_names.get(axis_key, {}).get(value)

    if axis_name_value is None:
        axis_name_value = DEFAULT_AXIS_VALUE_NAMES.get(axis_key, {}).get(value)

    if axis_name_value:
        return "%s - %s" % (label, axis_name_value)
    return label


def axis_value_from_axes_values(axes_values, axis_index_value, axis_id_value):
    axes_dictionary = dictionary_copy(axes_values)
    if axes_dictionary is not None:
        if axis_id_value is None:
            return None
        return axes_dictionary.get(axis_id_value)

    try:
        axes_list = list(axes_values or [])
    except Exception:
        return None

    if axis_index_value >= len(axes_list):
        return None
    return axes_list[axis_index_value]


def read_axis_value(instance, axis_index_value, axis_id_value):
    if axis_id_value is not None:
        for method_name in ("axisValueValueForId_", "axisValueForId_"):
            method = getattr(instance, method_name, None)
            if callable(method):
                try:
                    return method(axis_id_value)
                except Exception:
                    pass

    return axis_value_from_axes_values(raw_axes_values(instance), axis_index_value, axis_id_value)


def instance_name(instance):
    value = getattr(instance, "name", "Unnamed instance")
    if callable(value):
        try:
            value = value()
        except Exception:
            value = "Unnamed instance"
    return str(value or "Unnamed instance")


def read_instance_active(instance):
    for attribute_name in ("active", "exports"):
        value = getattr(instance, attribute_name, None)
        if value is None:
            continue
        if callable(value):
            try:
                value = value()
            except Exception:
                continue
        return bool(value)
    return True


def set_instance_active(instance, active):
    success = False
    active_value = bool(active)

    for setter_name in ("setActive_", "setExports_"):
        setter = getattr(instance, setter_name, None)
        if callable(setter):
            try:
                setter(active_value)
                success = True
            except Exception:
                pass

    for attribute_name in ("active", "exports"):
        try:
            setattr(instance, attribute_name, active_value)
            success = True
        except Exception:
            pass

    return success


def collect_font_data(font):
    axis_infos = {}
    for key, title, names in AXIS_GROUPS:
        index, identifier, actual_name = axis_info(font, names)
        axis_infos[key] = {
            "index": index,
            "id": identifier,
            "name": actual_name,
            "title": title,
        }

    values = dict((key, set()) for key, title, names in AXIS_GROUPS)
    instance_records = []

    for instance in font.instances:
        axes = {}
        complete = True
        for key, title, names in AXIS_GROUPS:
            info = axis_infos[key]
            raw_value = read_axis_value(instance, info["index"], info["id"])
            if raw_value is None:
                complete = False
                break
            try:
                axes[key] = value_key(raw_value)
            except Exception:
                complete = False
                break
            if is_ignored_axis_value(axes[key]):
                complete = False
                break

        if not complete:
            continue

        for key, axis_value in axes.items():
            values[key].add(axis_value)
        instance_records.append((instance, axes))

    sorted_values = {}
    for key, title, names in AXIS_GROUPS:
        sorted_values[key] = sorted(values[key])

    return axis_infos, sorted_values, instance_records


def infer_axis_value_names(instance_records):
    inferred_names = {}

    for key, title, names in AXIS_GROUPS:
        inferred_names[key] = {}
        known_names = KNOWN_AXIS_VALUE_NAMES.get(key, ())
        normalized_known_names = [
            (known_name, normalized_name(known_name))
            for known_name in known_names
        ]
        normalized_known_names.sort(key=lambda item: len(item[1]), reverse=True)

        axis_values = sorted(set(axes[key] for instance, axes in instance_records))
        for axis_value in axis_values:
            scores = dict((known_name, 0) for known_name in known_names)

            for instance, axes in instance_records:
                if axes[key] != axis_value:
                    continue

                normalized_instance_name = normalized_name(instance_name(instance))
                for known_name, normalized_known_name in normalized_known_names:
                    if normalized_known_name and normalized_known_name in normalized_instance_name:
                        scores[known_name] += 1
                        break

            best_name = None
            best_score = 0
            for known_name in known_names:
                score = scores[known_name]
                if score > best_score:
                    best_name = known_name
                    best_score = score

            if best_name is not None and best_score > 0:
                inferred_names[key][axis_value] = best_name

    return inferred_names


def active_axis_values(instance_records):
    selected = dict((key, set()) for key, title, names in AXIS_GROUPS)

    for instance, axes in instance_records:
        if not read_instance_active(instance):
            continue
        for key, title, names in AXIS_GROUPS:
            selected[key].add(axes[key])

    return selected


class InstanceActiveStatusWindow(object):
    def __init__(self):
        self.font = Glyphs.font
        Glyphs.clearLog()
        print("Set Instance Active Status")
        print("Script version: %s" % SCRIPT_VERSION)
        print("")

        if self.font is None:
            print("No font is open.")
            return

        try:
            self.axis_infos, self.values, self.instance_records = collect_font_data(self.font)
        except Exception as error:
            print("Could not collect instance axis values: %s" % error)
            return

        if not self.instance_records:
            print("No instances with complete Weight, Width, and Optical size values were found.")
            return

        self.axis_value_names = infer_axis_value_names(self.instance_records)
        self.initial_selected_values = active_axis_values(self.instance_records)
        self.checkboxes = {}
        self.updating_checkboxes = False
        self.has_pending_changes = False
        column_width = 190
        margin = 15
        row_height = 24
        heading_height = 22
        header_button_width = 24
        header_button_gap = 4
        button_height = 28
        status_height = 20
        max_rows = max(len(self.values[key]) for key, title, names in AXIS_GROUPS)
        window_width = margin * 2 + column_width * len(AXIS_GROUPS)
        window_height = margin * 4 + heading_height + row_height * max_rows + status_height + button_height

        self.w = vanilla.FloatingWindow((window_width, window_height), "Set Instance Active Status")

        for column_index, (key, title, names) in enumerate(AXIS_GROUPS):
            left = margin + column_index * column_width
            self.w.__setattr__(
                "%sLabel" % key,
                vanilla.TextBox((left, margin + 3, column_width - 2 * header_button_width - header_button_gap - 16, 18), title),
            )
            self.w.__setattr__(
                "%sPlusButton" % key,
                vanilla.Button(
                    (left + column_width - 2 * header_button_width - header_button_gap - 10, margin, header_button_width, 22),
                    "+",
                    callback=lambda sender, column_key=key: self.set_column_checked(column_key, True),
                ),
            )
            self.w.__setattr__(
                "%sMinusButton" % key,
                vanilla.Button(
                    (left + column_width - header_button_width - 10, margin, header_button_width, 22),
                    "-",
                    callback=lambda sender, column_key=key: self.set_column_checked(column_key, False),
                ),
            )
            self.checkboxes[key] = []
            for row_index, axis_value in enumerate(self.values[key]):
                checkbox = vanilla.CheckBox(
                    (left, margin + heading_height + row_index * row_height, column_width - 10, 20),
                    axis_value_label(key, axis_value, self.axis_value_names),
                    value=axis_value in self.initial_selected_values[key],
                    callback=self.checkbox_callback,
                )
                self.w.__setattr__("%s_%i" % (key, row_index), checkbox)
                self.checkboxes[key].append((axis_value, checkbox))

        status_top = window_height - margin * 2 - button_height - status_height
        self.w.statusLabel = vanilla.TextBox(
            (margin, status_top, -margin, status_height),
            "Ready",
        )

        button_top = window_height - margin - button_height
        self.w.allButton = vanilla.Button(
            (margin, button_top, 28, button_height),
            "+",
            callback=self.select_all_callback,
        )
        self.w.noneButton = vanilla.Button(
            (margin + 34, button_top, 28, button_height),
            "-",
            callback=self.select_none_callback,
        )
        self.w.applyButton = vanilla.Button(
            (margin + 74, button_top, -margin, button_height),
            "Set active instances",
            callback=self.apply_callback,
        )
        self.w.open()
        self.w.makeKey()
        print("UI opened.")

    def set_status(self, text):
        try:
            self.w.statusLabel.set(text)
        except Exception:
            pass

    def mark_pending_changes(self):
        self.has_pending_changes = True
        self.set_status("Selection changed. Click Set active instances.")

    def set_column_checked(self, key, checked, mark_pending=True):
        previous_updating_checkboxes = self.updating_checkboxes
        self.updating_checkboxes = True
        try:
            for axis_value, checkbox in self.checkboxes.get(key, []):
                checkbox.set(checked)
        finally:
            self.updating_checkboxes = previous_updating_checkboxes

        if mark_pending:
            self.mark_pending_changes()

    def select_all_callback(self, sender):
        self.updating_checkboxes = True
        try:
            for key, title, names in AXIS_GROUPS:
                self.set_column_checked(key, True, mark_pending=False)
        finally:
            self.updating_checkboxes = False
        self.mark_pending_changes()

    def select_none_callback(self, sender):
        self.updating_checkboxes = True
        try:
            for key, title, names in AXIS_GROUPS:
                self.set_column_checked(key, False, mark_pending=False)
        finally:
            self.updating_checkboxes = False
        self.mark_pending_changes()

    def checkbox_callback(self, sender):
        if self.updating_checkboxes:
            return
        self.mark_pending_changes()

    def apply_callback(self, sender):
        self.apply_current_selection()
        self.has_pending_changes = False
        self.set_status("Applied.")

    def selected_values(self):
        selected = {}
        for key, title, names in AXIS_GROUPS:
            selected[key] = set(
                axis_value
                for axis_value, checkbox in self.checkboxes[key]
                if checkbox.get()
            )
        return selected

    def apply_current_selection(self):
        Glyphs.clearLog()
        print("Set Instance Active Status")
        print("Script version: %s" % SCRIPT_VERSION)
        print("Explicit apply")
        print("")

        selected = self.selected_values()
        for key, title, names in AXIS_GROUPS:
            print("%s selected: %s" % (
                title,
                ", ".join(
                    axis_value_label(key, value, self.axis_value_names)
                    for value in sorted(selected[key])
                ) or "none",
            ))
        print("")

        if any(not selected[key] for key, title, names in AXIS_GROUPS):
            print("At least one axis has no selected values. All complete static instances will be made inactive.")
            print("")

        changed_count = 0
        unchanged_count = 0
        skipped_count = len(self.font.instances) - len(self.instance_records)

        self.font.disableUpdateInterface()
        try:
            for instance, axes in self.instance_records:
                should_be_active = all(axes[key] in selected[key] for key, title, names in AXIS_GROUPS)
                old_active = read_instance_active(instance)

                if not set_instance_active(instance, should_be_active):
                    skipped_count += 1
                    print("Skipping %s: could not set active status" % instance_name(instance))
                    continue

                status_text = "active" if should_be_active else "inactive"
                if old_active != should_be_active:
                    changed_count += 1
                    print("%s: %s -> %s" % (
                        instance_name(instance),
                        "active" if old_active else "inactive",
                        status_text,
                    ))
                else:
                    unchanged_count += 1
                    print("%s: already %s" % (instance_name(instance), status_text))
        finally:
            self.font.enableUpdateInterface()

        print("")
        print("Done. Changed %i instance(s); unchanged %i; skipped %i." % (
            changed_count,
            unchanged_count,
            skipped_count,
        ))


try:
    INSTANCE_ACTIVE_STATUS_WINDOW = InstanceActiveStatusWindow()
except Exception as error:
    import traceback

    Glyphs.clearLog()
    print("Set Instance Active Status")
    print("")
    print("Could not open UI: %s" % error)
    print(traceback.format_exc())
