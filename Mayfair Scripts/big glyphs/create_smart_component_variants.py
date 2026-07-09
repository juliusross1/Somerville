#MenuTitle: Create Smart Component Variants
# -*- coding: utf-8 -*-

import uuid
import re

import vanilla
from GlyphsApp import Glyphs, GSGlyph, GSGlyphReference


SCRIPT_VERSION = "2026-06-29 13:05 CDT base-smart-value-step-variants"
SETTINGS_USER_DATA_KEY = "com.opentypemathtools.smartComponentVariants"
MATH_PLUGIN_VARIANTS_USER_DATA_KEY = "com.nagwa.MATHPlugin.variants"
MATH_PLUGIN_VARIANT_KEYS = dict(
    height="vVariants",
    width="hVariants",
)
SMART_AXIS_NAMES = ("height", "width")
DEFAULT_VARIANT_COUNT = 1
DEFAULT_STEP = 1
DEFAULT_SMART_AXIS_NAME = "height"
VARIANT_SUFFIX_PATTERN = re.compile(r"\.s\d+$")


def print_warning(message):
    print("WARNING: %s" % message)


def safe_call(value, default=None):
    if callable(value):
        try:
            return value()
        except Exception:
            return default
    return value


def layer_name(layer):
    return str(safe_call(getattr(layer, "name", ""), "") or "")


def layer_id(layer):
    value = safe_call(getattr(layer, "layerId", None))
    if value is None:
        return None
    return str(value)


def is_master_layer(layer):
    return bool(safe_call(getattr(layer, "isMasterLayer", False), False))


def set_associated_master_id(layer, associated_master_id):
    method = getattr(layer, "setAssociatedMasterId_", None)
    if method is not None:
        try:
            method(associated_master_id)
            return
        except Exception:
            pass
    try:
        layer.associatedMasterId = associated_master_id
    except Exception:
        pass


def remove_layer(glyph, layer):
    for method_name in ("remove_", "removeObject_", "removeObject", "removeLayer_"):
        method = getattr(glyph.layers, method_name, None)
        if method is None:
            continue
        try:
            method(layer)
            return True
        except Exception:
            pass

    current_layer_id = layer_id(layer)
    if current_layer_id is not None:
        try:
            del glyph.layers[current_layer_id]
            return True
        except Exception:
            pass
    return False


def selected_glyph(font):
    selected_layers = list(font.selectedLayers or [])
    if not selected_layers:
        return None
    return selected_layers[0].parent


def is_s_variant_glyph(glyph):
    glyph_name = getattr(glyph, "name", "")
    return bool(VARIANT_SUFFIX_PATTERN.search(str(glyph_name or "")))


def layer_components(layer):
    try:
        return list(layer.components)
    except Exception:
        return []


def layer_paths(layer):
    try:
        return list(layer.paths)
    except Exception:
        return []


def component_name(component):
    for attribute_name in ("componentName", "name"):
        value = safe_call(getattr(component, attribute_name, None))
        if value:
            return str(value)

    component_glyph = safe_call(getattr(component, "component", None))
    if component_glyph is not None:
        value = safe_call(getattr(component_glyph, "name", None))
        if value:
            return str(value)

    glyph = safe_call(getattr(component, "glyph", None))
    if glyph is not None:
        value = safe_call(getattr(glyph, "name", None))
        if value:
            return str(value)
    return None


def component_glyph(font, component):
    glyph = safe_call(getattr(component, "component", None))
    if glyph is not None and safe_call(getattr(glyph, "name", None)):
        return glyph

    glyph = safe_call(getattr(component, "glyph", None))
    if glyph is not None and safe_call(getattr(glyph, "name", None)):
        return glyph

    name = component_name(component)
    if name is None:
        return None
    try:
        return font.glyphs[name]
    except Exception:
        return None


def smart_axes_count(glyph):
    if glyph is None:
        return 0
    try:
        return len(list(glyph.smartComponentAxes or []))
    except Exception:
        return 0


def axis_identifier(axis):
    for attribute_name in ("id", "axisId"):
        value = safe_call(getattr(axis, attribute_name, None))
        if value:
            return str(value)
    return None


def smart_axis_name(axis):
    value = safe_call(getattr(axis, "name", None))
    if value:
        return str(value)
    return ""


def smart_axis_for_name(glyph, wanted_name):
    if glyph is None:
        return None
    try:
        axes = list(glyph.smartComponentAxes or [])
    except Exception:
        axes = []
    for axis in axes:
        if smart_axis_name(axis) == wanted_name:
            return axis
    return None


def smart_axis_id_for_name(glyph, wanted_name):
    axis = smart_axis_for_name(glyph, wanted_name)
    if axis is not None:
        return axis_identifier(axis)
    return None


def smart_axis_id_for_component(font, component, smart_axis_name_value):
    glyph = component_glyph(font, component)
    if glyph is None:
        return None
    return smart_axis_id_for_name(glyph, smart_axis_name_value)


def numeric_value(value):
    try:
        return float(value)
    except Exception:
        return None


def smart_axis_default_value(axis):
    for attribute_name in ("bottomValue", "topValue"):
        value = numeric_value(safe_call(getattr(axis, attribute_name, None)))
        if value is not None:
            return value
    return None


def component_smart_axis_value(font, component, smart_axis_name_value):
    glyph = component_glyph(font, component)
    axis = smart_axis_for_name(glyph, smart_axis_name_value)
    smart_axis_id = axis_identifier(axis) if axis is not None else None
    if smart_axis_id is None:
        return None

    try:
        values = dict(component.smartComponentValues or {})
    except Exception:
        values = {}

    for key in (smart_axis_id, smart_axis_name_value):
        if key in values:
            value = numeric_value(values[key])
            if value is not None:
                return value

    return smart_axis_default_value(axis)


def format_number_list(values):
    cleaned = []
    for value in values:
        cleaned.append(clean_number(value))
    return ", ".join([str(value) for value in cleaned])


def y_value_summary(values):
    unique_values = sorted(set([clean_number(value) for value in values]))
    if not unique_values:
        return "unavailable"
    if len(unique_values) == 1:
        return str(unique_values[0])
    return "mixed (%s)" % format_number_list(unique_values)


def validate_source_glyph(font, glyph, smart_axis_name_value):
    component_names = set()
    layer_count = 0
    component_count = 0
    component_axis_ids = {}
    base_smart_axis_values = []

    for layer in glyph.layers:
        components = layer_components(layer)
        paths = layer_paths(layer)
        layer_label = layer_name(layer) or layer_id(layer) or "<unnamed layer>"

        if not components or paths:
            print_warning("%s/%s: expected one or more components and no paths; found %i component(s), %i path(s)" % (
                glyph.name,
                layer_label,
                len(components),
                len(paths),
            ))
            return None

        for component in components:
            name = component_name(component)
            if name is None:
                print_warning("%s/%s: could not read a component name" % (glyph.name, layer_label))
                return None

            base_component_glyph = component_glyph(font, component)
            if smart_axes_count(base_component_glyph) == 0:
                print_warning("%s/%s uses %s, but that component glyph has no smart component axes." % (
                    glyph.name,
                    layer_label,
                    name,
                ))
                return None

            smart_axis_id = smart_axis_id_for_name(base_component_glyph, smart_axis_name_value)
            if smart_axis_id is None:
                print_warning("%s/%s uses %s, but that component glyph has no smart axis named %s." % (
                    glyph.name,
                    layer_label,
                    name,
                    smart_axis_name_value,
                ))
                return None

            base_value = component_smart_axis_value(font, component, smart_axis_name_value)
            if base_value is None:
                print_warning("%s/%s uses %s, but its current %s value could not be read." % (
                    glyph.name,
                    layer_label,
                    name,
                    smart_axis_name_value,
                ))
                return None

            component_names.add(name)
            component_axis_ids[name] = smart_axis_id
            base_smart_axis_values.append(base_value)
            component_count += 1
        layer_count += 1

    if not component_names:
        print_warning("%s has no component layers." % glyph.name)
        return None

    return dict(
        component_names=sorted(component_names),
        layer_count=layer_count,
        component_count=component_count,
        component_axis_ids=component_axis_ids,
        base_smart_axis_values=base_smart_axis_values,
    )


def variant_name(source_name, number):
    return "%s.s%02i" % (source_name, number)


def variant_names(source_name, variant_count):
    return [source_name] + [variant_name(source_name, number) for number in range(1, variant_count + 1)]


def copy_glyph_metadata(source_glyph, target_glyph):
    for attribute_name in ("category", "subCategory", "script", "leftMetricsKey", "rightMetricsKey", "widthMetricsKey"):
        try:
            setattr(target_glyph, attribute_name, getattr(source_glyph, attribute_name))
        except Exception:
            pass
    try:
        target_glyph.export = source_glyph.export
    except Exception:
        pass


def glyph_for_name(font, glyph_name):
    try:
        return font.glyphs[glyph_name]
    except Exception:
        return None


def get_or_create_glyph(font, glyph_name, source_glyph):
    glyph = glyph_for_name(font, glyph_name)
    if glyph is not None:
        return glyph, False

    glyph = GSGlyph(glyph_name)
    copy_glyph_metadata(source_glyph, glyph)
    font.glyphs.append(glyph)
    return glyph, True


def remove_non_master_layers(glyph):
    removed = 0
    for layer in list(glyph.layers):
        if is_master_layer(layer):
            continue
        if remove_layer(glyph, layer):
            removed += 1
    return removed


def copied_layer(source_layer):
    layer = source_layer.copy()
    if not layer_id(layer):
        layer.layerId = str(uuid.uuid4()).upper()
    return layer


def set_component_smart_value(component, axis_id_value, value):
    if not hasattr(component, "smartComponentValues"):
        return False
    try:
        component.smartComponentValues[axis_id_value] = value
        return True
    except Exception:
        pass
    try:
        values = dict(component.smartComponentValues or {})
        values[axis_id_value] = value
        component.smartComponentValues = values
        return True
    except Exception:
        return False


def set_layer_component_smart_value(font, layer, smart_axis_name_value, smart_axis_increment):
    changed = 0
    skipped = 0
    for component in layer_components(layer):
        smart_axis_id = smart_axis_id_for_component(font, component, smart_axis_name_value)
        if smart_axis_id is None:
            skipped += 1
            continue
        base_value = component_smart_axis_value(font, component, smart_axis_name_value)
        if base_value is None:
            skipped += 1
            continue
        smart_axis_value = clean_number(base_value + smart_axis_increment)
        if set_component_smart_value(component, smart_axis_id, smart_axis_value):
            changed += 1
        else:
            skipped += 1
    return changed, skipped


def populate_variant_from_source(font, source_glyph, target_glyph, smart_axis_name_value, smart_axis_increment):
    remove_non_master_layers(target_glyph)

    copied_master_layers = 0
    copied_special_layers = 0
    smart_components_set = 0
    smart_components_skipped = 0
    for source_layer in source_glyph.layers:
        if is_master_layer(source_layer):
            source_layer_id = layer_id(source_layer)
            new_layer = copied_layer(source_layer)
            new_layer.layerId = source_layer_id
            set_associated_master_id(new_layer, source_layer_id)
            changed, skipped = set_layer_component_smart_value(font, new_layer, smart_axis_name_value, smart_axis_increment)
            smart_components_set += changed
            smart_components_skipped += skipped
            target_glyph.layers[source_layer_id] = new_layer
            copied_master_layers += 1
            continue

        new_layer = copied_layer(source_layer)
        changed, skipped = set_layer_component_smart_value(font, new_layer, smart_axis_name_value, smart_axis_increment)
        smart_components_set += changed
        smart_components_skipped += skipped
        target_glyph.layers.append(new_layer)
        copied_special_layers += 1

    copy_glyph_metadata(source_glyph, target_glyph)
    return copied_master_layers, copied_special_layers, smart_components_set, smart_components_skipped


def parse_variant_count(text):
    try:
        value = int(str(text).strip())
    except Exception:
        raise ValueError("N must be a positive integer.")
    if value < 1:
        raise ValueError("N must be a positive integer.")
    return value


def parse_step(text):
    try:
        return float(str(text).strip())
    except Exception:
        raise ValueError("Step must be a number.")


def default_settings():
    return dict(
        N=DEFAULT_VARIANT_COUNT,
        step=DEFAULT_STEP,
        axis=DEFAULT_SMART_AXIS_NAME,
    )


def normalized_axis_name(axis_name_value):
    axis_name_value = str(axis_name_value or DEFAULT_SMART_AXIS_NAME)
    if axis_name_value not in SMART_AXIS_NAMES:
        return DEFAULT_SMART_AXIS_NAME
    return axis_name_value


def settings_from_glyph(glyph):
    settings = default_settings()
    if glyph is None:
        return settings

    value = None
    try:
        value = glyph.userData[SETTINGS_USER_DATA_KEY]
    except Exception:
        pass
    try:
        stored = dict(value or {})
    except Exception:
        stored = {}

    try:
        settings["N"] = parse_variant_count(stored.get("N", settings["N"]))
    except Exception:
        pass
    try:
        settings["step"] = parse_step(stored.get("step", settings["step"]))
    except Exception:
        pass
    settings["axis"] = normalized_axis_name(stored.get("axis", settings["axis"]))
    return settings


def store_settings_on_glyph(glyph, variant_count, step, smart_axis_name_value):
    settings = dict(
        N=int(variant_count),
        step=clean_number(step),
        axis=normalized_axis_name(smart_axis_name_value),
    )

    try:
        glyph.userData[SETTINGS_USER_DATA_KEY] = settings
    except Exception:
        print_warning("%s: could not store settings in glyph userData." % glyph.name)
    return settings


def glyph_reference_for_name(font, glyph_name):
    glyph = glyph_for_name(font, glyph_name)
    if glyph is None:
        return None
    try:
        return GSGlyphReference(glyph)
    except Exception:
        return None


def store_math_plugin_variants_on_glyph(font, glyph, variant_count, smart_axis_name_value):
    smart_axis_name_value = normalized_axis_name(smart_axis_name_value)
    variant_key = MATH_PLUGIN_VARIANT_KEYS[smart_axis_name_value]
    names = variant_names(glyph.name, variant_count)
    references = []

    for name in names:
        reference = glyph_reference_for_name(font, name)
        if reference is None:
            print_warning("%s: could not create GSGlyphReference for %s." % (glyph.name, name))
            return variant_key, names, False
        references.append(reference)

    existing_value = None
    try:
        existing_value = glyph.userData[MATH_PLUGIN_VARIANTS_USER_DATA_KEY]
    except Exception:
        pass

    try:
        math_plugin_variants = dict(existing_value or {})
    except Exception:
        math_plugin_variants = {}

    math_plugin_variants[variant_key] = references
    try:
        glyph.userData[MATH_PLUGIN_VARIANTS_USER_DATA_KEY] = math_plugin_variants
    except Exception:
        print_warning("%s: could not store MATH plugin variants in glyph userData." % glyph.name)
        return variant_key, names, False
    return variant_key, names, True


def clean_number(value):
    value = float(value)
    if value.is_integer():
        return int(value)
    return value


def run(source_glyph, variant_count, step, smart_axis_name_value):
    font = Glyphs.font
    if font is None:
        print_warning("No font open.")
        return

    if is_s_variant_glyph(source_glyph):
        print_warning("%s already has an .s-number suffix; select the base glyph instead." % source_glyph.name)
        return

    smart_axis_name_value = normalized_axis_name(smart_axis_name_value)
    validation = validate_source_glyph(font, source_glyph, smart_axis_name_value)
    if validation is None:
        return

    store_settings_on_glyph(source_glyph, variant_count, step, smart_axis_name_value)

    print("Source glyph: %s" % source_glyph.name)
    print("Component glyphs: %s" % ", ".join(validation["component_names"]))
    print("Source layers checked: %i" % validation["layer_count"])
    print("Smart components checked: %i" % validation["component_count"])
    print("Smart axis: %s" % smart_axis_name_value)
    print("Y (%s value on selected glyph): %s" % (
        smart_axis_name_value,
        y_value_summary(validation["base_smart_axis_values"]),
    ))
    print("Variants requested: %i" % variant_count)
    print("Step: %s" % clean_number(step))
    print("Formula: .sM %s = Y + M * step" % smart_axis_name_value)
    print("Stored settings userData key: %s" % SETTINGS_USER_DATA_KEY)
    print("")

    created = 0
    refreshed = 0
    font.disableUpdateInterface()
    try:
        for number in range(1, variant_count + 1):
            target_name = variant_name(source_glyph.name, number)
            smart_axis_increment = number * step
            target_glyph, did_create = get_or_create_glyph(font, target_name, source_glyph)
            master_count, special_count, smart_components_set, smart_components_skipped = populate_variant_from_source(
                font,
                source_glyph,
                target_glyph,
                smart_axis_name_value,
                smart_axis_increment,
            )
            if did_create:
                created += 1
            else:
                refreshed += 1
            print("%s: %s, copied %i master layer(s) and %i special layer(s); set %s=%s on %i component(s)" % (
                target_name,
                "created" if did_create else "updated",
                master_count,
                special_count,
                smart_axis_name_value,
                "Y + %s" % clean_number(smart_axis_increment),
                smart_components_set,
            ))
            if smart_components_skipped:
                print_warning("%s: skipped %i component(s) whose %s value could not be set." % (
                    target_name,
                    smart_components_skipped,
                    smart_axis_name_value,
                ))

        variant_key, math_plugin_variant_names, stored_math_plugin_variants = store_math_plugin_variants_on_glyph(
            font,
            source_glyph,
            variant_count,
            smart_axis_name_value,
        )
    finally:
        font.enableUpdateInterface()

    print("")
    if stored_math_plugin_variants:
        print("Stored MATH plugin %s as GSGlyphReference list: %s" % (
            variant_key,
            ", ".join(math_plugin_variant_names),
        ))
    print("Done. Created %i glyph(s); updated %i existing glyph(s)." % (created, refreshed))
    return dict(
        y_value_summary=y_value_summary(validation["base_smart_axis_values"]),
        created=created,
        refreshed=refreshed,
    )


class SmartComponentVariantsWindow(object):
    def __init__(self):
        self.font = Glyphs.font
        self.source_glyph = selected_glyph(self.font) if self.font is not None else None
        self.settings = settings_from_glyph(self.source_glyph)

        title = "Smart Component Variants"
        self.w = vanilla.FloatingWindow((320, 224), title)
        source_label = self.source_glyph.name if self.source_glyph is not None else "No glyph selected"
        self.w.sourceLabel = vanilla.TextBox((15, 16, -15, 18), "Source: %s" % source_label)
        self.w.countLabel = vanilla.TextBox((15, 48, 35, 18), "N")
        self.w.count = vanilla.EditText((55, 44, 80, 24), str(self.settings["N"]))
        self.w.stepLabel = vanilla.TextBox((155, 48, 45, 18), "Step")
        self.w.step = vanilla.EditText((205, 44, 80, 24), str(clean_number(self.settings["step"])))
        self.w.axisLabel = vanilla.TextBox((15, 82, 45, 18), "Axis")
        self.w.axis = vanilla.PopUpButton((55, 78, 230, 24), list(SMART_AXIS_NAMES))
        self.w.axis.set(list(SMART_AXIS_NAMES).index(self.settings["axis"]))
        self.w.yLabel = vanilla.TextBox((15, 116, -15, 36), "Y: run to read selected glyph")
        self.w.runButton = vanilla.Button((15, 182, -15, 26), "Create/update variants", callback=self.run_callback)
        self.w.open()
        self.w.makeKey()
        print("UI opened.")

    def run_callback(self, sender):
        Glyphs.clearLog()
        Glyphs.showMacroWindow()
        print("Create Smart Component Variants")
        print("Script version: %s" % SCRIPT_VERSION)
        print("")

        font = Glyphs.font
        if font is None:
            print_warning("No font open.")
            return

        source_glyph = selected_glyph(font)
        if source_glyph is None:
            print_warning("No glyph selected.")
            return
        if is_s_variant_glyph(source_glyph):
            print_warning("%s already has an .s-number suffix; select the base glyph instead." % source_glyph.name)
            return

        try:
            variant_count = parse_variant_count(self.w.count.get())
        except Exception as error:
            print_warning(error)
            return

        try:
            step = parse_step(self.w.step.get())
        except Exception as error:
            print_warning(error)
            return

        axis_index = self.w.axis.get()
        smart_axis_name_value = SMART_AXIS_NAMES[axis_index]
        result = run(source_glyph, variant_count, step, smart_axis_name_value)
        if result is not None:
            self.w.yLabel.set("Y (%s): %s" % (
                smart_axis_name_value,
                result["y_value_summary"],
            ))


try:
    Glyphs.clearLog()
    Glyphs.showMacroWindow()
    print("Create Smart Component Variants")
    print("Script version: %s" % SCRIPT_VERSION)
    print("")
    current_font = Glyphs.font
    current_glyph = selected_glyph(current_font) if current_font is not None else None
    if current_glyph is not None and is_s_variant_glyph(current_glyph):
        print_warning("%s already has an .s-number suffix; select the base glyph instead." % current_glyph.name)
    else:
        SMART_COMPONENT_VARIANTS_WINDOW = SmartComponentVariantsWindow()
except Exception as error:
    import traceback

    Glyphs.clearLog()
    Glyphs.showMacroWindow()
    print("Create Smart Component Variants")
    print("")
    print_warning("Could not open UI: %s" % error)
    print_warning(traceback.format_exc())
