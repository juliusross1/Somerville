#MenuTitle: Apply ARLN Floor Middle-Piece Exchanges
# -*- coding: utf-8 -*-

"""Choose and apply a configuration block from recipes/ARLN_floors.plist.

The plist contains a ``Blocks`` array. The script presents those named blocks
in a window, shows the selected block's Unicode points, Floor, and middle-piece
exchanges, and runs only the selected block. For every Unicode character in
that block, each component matching a ``MiddleGlyphInput`` is changed to its
``MiddleGlyphOutput``. A component is considered only once, so exchange pairs
cannot cascade during a single run. Existing dot suffixes are ignored when
matching, so an input such as ``Arrow.mid.ShortShort`` also matches
``Arrow.mid.ShortShort.FloorB``.

Every configured ``MiddleGlyphOutput`` is created if missing and then passed
to ``adjust_arrow_mid_components``, even when none of the glyphs listed in
``UnicodePoints`` needs a component exchange. Its A layer is created at ARLN
0, and its B layer is created at the selected block's ``Floor`` value. For
each master and supported component, both A and B component widths are
the same value Y. Y is the piecewise-linear interpolation of the corresponding
``MiddleGlyphInput`` component's explicit widths, evaluated at ARLN=Floor.
Intermediate layers provide their own ARLN knots, and the master layer provides
the knot at ``ARLNmaximum`` from ``recipe_constants.plist``. Afterward, the
output glyph's metrics are updated for every master.
"""

import importlib.util
import os
import plistlib

import vanilla
from GlyphsApp import Glyphs, Message


SCRIPT_VERSION = "2026-08-07 piecewise-input-width-interpolation"
PLIST_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "recipes", "ARLN_floors.plist")
)
ARROW_ADJUSTER_PATH = os.path.join(
    os.path.dirname(__file__), "create_arn_intermediates_and_set_arrow_mid_width.py"
)


def load_arrow_adjuster():
    """Load the sibling script without opening its user interface."""
    try:
        spec = importlib.util.spec_from_file_location(
            "mayfair_adjust_arrow_mid_components", ARROW_ADJUSTER_PATH
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception as error:
        raise RuntimeError(
            "Could not load adjust_arrow_mid_components from %s: %s"
            % (ARROW_ADJUSTER_PATH, error)
        )


def corresponding_component_width(
    adjuster, layer, glyph_name, master_name, output_component, component_index
):
    """Read the corresponding explicit component width from one input layer."""
    input_components = adjuster.components_in_layer(layer)
    if component_index >= len(input_components):
        raise RuntimeError(
            "%s / %s has no corresponding supported component %i."
            % (glyph_name, layer.name or master_name, component_index + 1)
        )
    input_component = input_components[component_index]
    input_name = adjuster.component_name(input_component)
    output_name = adjuster.component_name(output_component)
    if input_name != output_name:
        raise RuntimeError(
            "%s / %s component %i is %s, but the output component is %s."
            % (
                glyph_name,
                layer.name or master_name,
                component_index + 1,
                input_name,
                output_name,
            )
        )
    x = adjuster.read_component_smart_value(input_component)
    if x is None:
        raise RuntimeError(
            "%s / %s component %i has no explicit width value."
            % (glyph_name, layer.name or master_name, component_index + 1)
        )
    return float(x)


def interpolated_component_width(
    adjuster, input_glyph, floor, arln_maximum, master, output_component, component_index
):
    """Evaluate the input component's piecewise-linear ARLN width at Floor."""
    font = input_glyph.parent
    arn_axis = adjuster.find_arrow_length_axis(font)
    arn_axis_id = adjuster.axis_identifier(arn_axis)
    master_coordinates = adjuster.master_coordinates(font, master)
    master_layer = adjuster.master_layer_for_glyph(input_glyph, master)
    if master_layer is None:
        raise RuntimeError(
            "%s has no master layer for %s." % (input_glyph.name, master.name)
        )

    knots = [
        (
            float(arln_maximum),
            corresponding_component_width(
                adjuster,
                master_layer,
                input_glyph.name,
                master.name,
                output_component,
                component_index,
            ),
            str(master_layer.name or master.name),
        )
    ]
    for layer in input_glyph.layers:
        if adjuster.is_master_layer(layer):
            continue
        if adjuster.associated_master_id(layer) != str(master.id):
            continue
        coordinates = adjuster.coordinates_dict(
            font, adjuster.layer_attribute(layer, "coordinates")
        )
        if coordinates is None or arn_axis_id not in coordinates:
            continue
        # Ignore intermediate layers that move away from this master's slice
        # on an axis other than ARLN.
        if any(
            axis_id != arn_axis_id
            and abs(coordinates[axis_id] - master_coordinates[axis_id]) > 0.0001
            for axis_id in coordinates
            if axis_id in master_coordinates
        ):
            continue
        knots.append(
            (
                float(coordinates[arn_axis_id]),
                corresponding_component_width(
                    adjuster,
                    layer,
                    input_glyph.name,
                    master.name,
                    output_component,
                    component_index,
                ),
                str(layer.name or layer.layerId),
            )
        )

    knots.sort(key=lambda knot: knot[0])
    unique_knots = []
    for position, width, label in knots:
        if unique_knots and abs(position - unique_knots[-1][0]) <= 0.0001:
            if abs(width - unique_knots[-1][1]) > 0.0001:
                raise RuntimeError(
                    "%s / %s has conflicting widths %s and %s at ARLN %s."
                    % (
                        input_glyph.name,
                        master.name,
                        unique_knots[-1][1],
                        width,
                        position,
                    )
                )
            continue
        unique_knots.append((position, width, label))

    floor = float(floor)
    for position, width, label in unique_knots:
        if abs(floor - position) <= 0.0001:
            return width, unique_knots
    for left, right in zip(unique_knots, unique_knots[1:]):
        left_position, left_width, left_label = left
        right_position, right_width, right_label = right
        if left_position < floor < right_position:
            fraction = (floor - left_position) / (right_position - left_position)
            width = left_width + fraction * (right_width - left_width)
            return width, unique_knots
    raise RuntimeError(
        "%s / %s has no ARLN knot interval containing Floor %s (available: %s)."
        % (
            input_glyph.name,
            master.name,
            floor,
            ", ".join(str(knot[0]) for knot in unique_knots),
        )
    )


def update_metrics_for_all_masters(glyph, adjuster):
    """Run Glyphs' metrics update on every master layer of a glyph."""
    updated = 0
    for layer in glyph.layers:
        if not adjuster.is_master_layer(layer):
            continue
        try:
            layer.updateMetrics()
        except Exception as error:
            raise RuntimeError(
                "Could not update metrics for %s / %s: %s"
                % (glyph.name, layer.name or layer.layerId, error)
            )
        updated += 1
    return updated


def component_name(component):
    for attribute_name in ("componentName", "name"):
        try:
            value = getattr(component, attribute_name)
            if value:
                return str(value)
        except Exception:
            pass
    return None


def exchange_output_for_component(current_name, exchanges):
    """Find an exchange by exact name or by ignoring existing dot suffixes."""
    if current_name in exchanges:
        return exchanges[current_name]
    matching_inputs = [
        input_name
        for input_name in exchanges
        if current_name.startswith(input_name + ".")
    ]
    if not matching_inputs:
        return None
    # Prefer the most specific configured input if names overlap.
    matching_input = max(matching_inputs, key=len)
    return exchanges[matching_input]


def components_in_layer(layer):
    try:
        shapes = list(layer.shapes)
    except Exception:
        shapes = []
    return [shape for shape in shapes if component_name(shape)]


def unicode_value(value):
    """Return an integer Unicode scalar from a character or hex notation."""
    text = str(value).strip()
    if len(text) == 1:
        return ord(text)
    upper = text.upper()
    if upper.startswith("U+"):
        upper = upper[2:]
    elif upper.startswith("0X"):
        upper = upper[2:]
    try:
        return int(upper, 16)
    except Exception:
        raise ValueError("Invalid Unicode point in ARLN_floors.plist: %r" % text)


def glyph_unicode_values(glyph):
    values = []
    try:
        values.extend(list(glyph.unicodes or []))
    except Exception:
        pass
    if not values:
        try:
            if glyph.unicode:
                values.append(glyph.unicode)
        except Exception:
            pass
    result = []
    for value in values:
        try:
            result.append(unicode_value(value))
        except Exception:
            pass
    return result


def font_unicode_map(font):
    result = {}
    for glyph in font.glyphs:
        for value in glyph_unicode_values(glyph):
            if value not in result:
                result[value] = glyph
    return result


def glyph_for_name(font, glyph_name):
    try:
        return font.glyphs[glyph_name]
    except Exception:
        return None


def validate_exchange_sources(font, exchanges):
    """Validate an ordered exchange plan without changing the font."""
    available_names = set()
    for glyph in font.glyphs:
        try:
            available_names.add(str(glyph.name))
        except Exception:
            pass

    for input_name, output_name in exchanges.items():
        if output_name in available_names:
            continue
        if input_name not in available_names:
            raise RuntimeError(
                "Cannot create %s because its input glyph %s does not exist."
                % (output_name, input_name)
            )
        # A later exchange is allowed to use this planned copy as its input.
        available_names.add(output_name)


def ensure_exchange_outputs(font, exchanges):
    """Deep-copy missing output glyphs from their configured input glyphs."""
    created_names = []
    for input_name, output_name in exchanges.items():
        if glyph_for_name(font, output_name) is not None:
            print("  Output exists; leaving it unchanged: %s" % output_name)
            continue

        input_glyph = glyph_for_name(font, input_name)
        if input_glyph is None:
            raise RuntimeError(
                "Cannot create %s because its input glyph %s does not exist."
                % (output_name, input_name)
            )

        try:
            output_glyph = input_glyph.copy()
        except Exception as error:
            raise RuntimeError(
                "Could not copy %s to create %s: %s"
                % (input_name, output_name, error)
            )
        if output_glyph is None:
            raise RuntimeError("Copying %s returned no glyph." % input_name)

        output_glyph.name = output_name
        try:
            font.glyphs.append(output_glyph)
        except Exception as error:
            raise RuntimeError("Could not add copied glyph %s: %s" % (output_name, error))

        actual_glyph = glyph_for_name(font, output_name)
        if actual_glyph is None:
            raise RuntimeError("Glyphs did not retain copied glyph %s." % output_name)
        created_names.append(output_name)
        print(
            "  Created full glyph copy: %s -> %s (%i layer(s))"
            % (input_name, output_name, len(list(actual_glyph.layers)))
        )
    return created_names


def load_configurations():
    """Load and validate every named configuration block in the plist."""
    try:
        with open(PLIST_PATH, "rb") as handle:
            configuration = plistlib.load(handle)
    except Exception as error:
        raise RuntimeError("Could not read %s: %s" % (PLIST_PATH, error))

    raw_blocks = configuration.get("Blocks")
    if not isinstance(raw_blocks, list) or not raw_blocks:
        raise RuntimeError("Blocks must be a non-empty array.")

    blocks = []
    seen_names = set()
    for block_index, raw_block in enumerate(raw_blocks, 1):
        if not isinstance(raw_block, dict):
            raise RuntimeError("Block %i must be a dictionary." % block_index)
        name = str(raw_block.get("Name") or "").strip()
        if not name:
            raise RuntimeError("Block %i needs a Name." % block_index)
        if name in seen_names:
            raise RuntimeError("Block name %s is used more than once." % name)
        seen_names.add(name)

        raw_unicode_points = raw_block.get("UnicodePoints")
        if not isinstance(raw_unicode_points, list) or not raw_unicode_points:
            raise RuntimeError("Block %s needs a non-empty UnicodePoints array." % name)
        try:
            unicode_points = [unicode_value(value) for value in raw_unicode_points]
        except Exception as error:
            raise RuntimeError("Block %s: %s" % (name, error))

        floor = raw_block.get("Floor")
        try:
            floor = float(floor)
        except (TypeError, ValueError):
            raise RuntimeError("Block %s needs a numeric Floor." % name)

        exchange_entries = raw_block.get("MiddlePieceExchange")
        if not isinstance(exchange_entries, list) or not exchange_entries:
            raise RuntimeError(
                "Block %s needs a non-empty MiddlePieceExchange array." % name
            )
        exchanges = {}
        output_floors = []
        for entry_index, entry in enumerate(exchange_entries, 1):
            if not isinstance(entry, dict):
                raise RuntimeError(
                    "Block %s, MiddlePieceExchange entry %i must be a dictionary."
                    % (name, entry_index)
                )
            input_name = str(entry.get("MiddleGlyphInput") or "").strip()
            output_name = str(entry.get("MiddleGlyphOutput") or "").strip()
            if not input_name or not output_name:
                raise RuntimeError(
                    "Block %s, exchange %i needs MiddleGlyphInput and MiddleGlyphOutput."
                    % (name, entry_index)
                )
            if input_name in exchanges and exchanges[input_name] != output_name:
                raise RuntimeError(
                    "Block %s gives MiddleGlyphInput %s more than one output."
                    % (name, input_name)
                )
            exchanges[input_name] = output_name
            output_floors.append((input_name, output_name, floor))

        blocks.append(
            {
                "name": name,
                "unicodePoints": unicode_points,
                "exchanges": exchanges,
                "outputFloors": output_floors,
                "floor": floor,
            }
        )
    return blocks


def set_component_name(component, output_name):
    """Change a component reference and verify that Glyphs retained it."""
    try:
        original_transform = component.transform
    except Exception:
        original_transform = None
    try:
        original_alignment = component.automaticAlignment
    except Exception:
        original_alignment = None

    setter_error = None
    try:
        component.componentName = output_name
    except Exception as error:
        setter_error = error
        try:
            component.name = output_name
            setter_error = None
        except Exception as fallback_error:
            setter_error = fallback_error

    if setter_error is not None:
        raise RuntimeError("could not set component name: %s" % setter_error)

    if original_transform is not None:
        try:
            component.transform = original_transform
        except Exception:
            pass
    if original_alignment is not None:
        try:
            component.automaticAlignment = original_alignment
        except Exception:
            pass

    actual_name = component_name(component)
    if actual_name != output_name:
        raise RuntimeError(
            "requested %s but component still reports %s"
            % (output_name, actual_name or "no name")
        )


def apply_configuration_block(block):
    """Apply one validated block returned by ``load_configurations``."""
    font = Glyphs.font
    if font is None:
        Message("No Font Open", "Open a font before running this script.")
        return

    unicode_points = block["unicodePoints"]
    exchanges = block["exchanges"]
    output_floors = block["outputFloors"]

    try:
        validate_exchange_sources(font, exchanges)
    except Exception as error:
        Message("Cannot Prepare ARLN Floor Glyphs", str(error))
        print("ARLN floor preparation error: %s" % error)
        return

    missing_characters = []
    created_output_glyphs = []
    changed_components = 0
    changed_layers = 0
    changed_glyphs = 0
    adjusted_output_glyphs = 0
    adjusted_output_components = 0
    errors = []

    print("Apply ARLN Floor Middle-Piece Exchanges")
    print("Script version: %s" % SCRIPT_VERSION)
    print("Configuration: %s" % PLIST_PATH)
    print("Selected block: %s" % block["name"])
    print("Floor: %s" % block["floor"])
    print("Unicode points: %s" % " ".join(chr(value) for value in unicode_points))
    print("Configured exchanges:")
    for input_name, output_name in exchanges.items():
        print("  %s -> %s" % (input_name, output_name))

    font.disableUpdateInterface()
    try:
        print("Preparing MiddleGlyphOutput glyphs:")
        try:
            created_output_glyphs = ensure_exchange_outputs(font, exchanges)
        except Exception as error:
            Message("Could Not Prepare ARLN Floor Glyphs", str(error))
            print("  ERROR: %s" % error)
            return

        unicode_map = font_unicode_map(font)
        for value in unicode_points:
            character = chr(value)
            glyph = unicode_map.get(value)
            if glyph is None:
                missing_characters.append("%s (U+%04X)" % (character, value))
                print("Missing glyph for %s (U+%04X)" % (character, value))
                continue

            print("Glyph %s for %s (U+%04X):" % (glyph.name, character, value))
            glyph_changed = False
            try:
                glyph.beginUndo()
            except Exception:
                pass
            try:
                for layer in glyph.layers:
                    layer_changes = 0
                    for component_index, component in enumerate(components_in_layer(layer), 1):
                        input_name = component_name(component)
                        output_name = exchange_output_for_component(
                            input_name, exchanges
                        )
                        if output_name is None or output_name == input_name:
                            continue
                        try:
                            set_component_name(component, output_name)
                            layer_changes += 1
                            changed_components += 1
                            glyph_changed = True
                            print(
                                "  Layer %s | component %i: %s -> %s"
                                % (
                                    layer.name or layer.layerId,
                                    component_index,
                                    input_name,
                                    output_name,
                                )
                            )
                        except Exception as error:
                            errors.append(
                                "%s / %s / component %i: %s"
                                % (
                                    glyph.name,
                                    layer.name or layer.layerId,
                                    component_index,
                                    error,
                                )
                            )
                    if layer_changes:
                        changed_layers += 1
                if glyph_changed:
                    changed_glyphs += 1
                else:
                    print("  No configured component exchanges were needed.")
            finally:
                try:
                    glyph.endUndo()
                except Exception:
                    pass
    finally:
        font.enableUpdateInterface()

    # This is intentionally independent of changed_components: configured
    # Floor output glyphs must be prepared even when the Unicode scan made no
    # component exchanges.
    print("Adjusting every configured MiddleGlyphOutput ARLN layer set:")
    try:
        adjuster = load_arrow_adjuster()
        adjust_arrow_mid_components = adjuster.adjust_arrow_mid_components
        arln_maximum = adjuster.recipe_constant("ARLNmaximum")
        if abs(arln_maximum) < 0.0001:
            raise RuntimeError("ARLNmaximum must not be zero.")
        print("  ARLNmaximum=%s" % adjuster.format_number(arln_maximum))
    except Exception as error:
        errors.append(str(error))
        adjust_arrow_mid_components = None
    if adjust_arrow_mid_components is not None:
        for input_name, output_name, floor in output_floors:
            input_glyph = glyph_for_name(font, input_name)
            output_glyph = glyph_for_name(font, output_name)
            if input_glyph is None:
                errors.append("Missing MiddleGlyphInput glyph %s." % input_name)
                continue
            if output_glyph is None:
                errors.append("Missing MiddleGlyphOutput glyph %s." % output_name)
                continue
            try:
                width_calculations = {}

                def calculated_width(master, component, component_index):
                    cache_key = (
                        str(master.id),
                        component_index,
                        adjuster.component_name(component),
                    )
                    if cache_key not in width_calculations:
                        width_calculations[cache_key] = interpolated_component_width(
                            adjuster,
                            input_glyph,
                            floor,
                            arln_maximum,
                            master,
                            component,
                            component_index,
                        )
                    return width_calculations[cache_key][0]

                result = adjust_arrow_mid_components(
                    output_glyph,
                    b=floor,
                    a=0,
                    component_width_a=calculated_width,
                    component_width_b=calculated_width,
                )
                updated_metric_layers = update_metrics_for_all_masters(
                    output_glyph, adjuster
                )
                adjusted_output_glyphs += 1
                adjusted_output_components += result["changedComponents"]
                print(
                    "  %s -> %s: A=0, B=%s; both widths=interpolated input width at B; created %i layer(s), updated %i component(s), updated metrics on %i master layer(s)"
                    % (
                        input_name,
                        output_name,
                        floor,
                        result["createdLayers"],
                        result["changedComponents"],
                        updated_metric_layers,
                    )
                )
                for cache_key, calculation in width_calculations.items():
                    master_id, component_index, smart_component_name = cache_key
                    width, knots = calculation
                    master = next(
                        item for item in font.masters if str(item.id) == master_id
                    )
                    print(
                        "    %s | %s component %i | knots: %s | Y at ARLN %s = %s"
                        % (
                            master.name,
                            smart_component_name,
                            component_index + 1,
                            ", ".join(
                                "%s:%s"
                                % (
                                    adjuster.format_number(position),
                                    adjuster.format_number(width_at_position),
                                )
                                for position, width_at_position, label in knots
                            ),
                            adjuster.format_number(floor),
                            adjuster.format_number(width),
                        )
                    )
                for layer_result in result["layers"]:
                    print(
                        "    %s | %s component width(s): %s"
                        % (
                            layer_result["master"],
                            layer_result["position"],
                            ", ".join(
                                adjuster.format_number(value)
                                for value in layer_result["componentWidths"]
                            ) or "no supported component",
                        )
                    )
            except Exception as error:
                errors.append("%s ARLN adjustment: %s" % (output_name, error))

    print("Summary:")
    print("  Created output glyph copies: %i" % len(created_output_glyphs))
    for glyph_name in created_output_glyphs:
        print("    %s" % glyph_name)
    print("  Changed glyphs: %i" % changed_glyphs)
    print("  Changed layers: %i" % changed_layers)
    print("  Changed components: %i" % changed_components)
    print("  Adjusted MiddleGlyphOutput glyphs: %i" % adjusted_output_glyphs)
    print("  Adjusted MiddleGlyphOutput components: %i" % adjusted_output_components)
    if missing_characters:
        print("  Missing Unicode glyphs: %s" % ", ".join(missing_characters))
    for error in errors:
        print("  ERROR: %s" % error)

    if errors:
        Message(
            "ARLN Floor Exchanges Completed with Errors",
            "Changed %i component(s). See the Macro window for %i error(s)."
            % (changed_components, len(errors)),
        )
    else:
        Message(
            "ARLN Floor Exchanges Complete",
            "%s: changed %i component(s) across %i glyph(s)."
            % (block["name"], changed_components, changed_glyphs),
        )


def block_description(block):
    """Build the human-readable preview shown in the selection window."""
    unicode_lines = [
        "%s  U+%04X" % (chr(value), value) for value in block["unicodePoints"]
    ]
    exchange_lines = [
        "%s  →  %s" % (input_name, output_name)
        for input_name, output_name in block["exchanges"].items()
    ]
    return (
        "Name: %s\n"
        "Floor / B value: %s\n"
        "A value: 0\n"
        "Component width at A: Y\n"
        "Component width at B: Y\n"
        "Y: MiddleGlyphInput width interpolated at ARLN = Floor\n\n"
        "Unicode points:\n%s\n\n"
        "Middle-piece exchanges:\n%s"
        % (
            block["name"],
            block["floor"],
            "\n".join("  " + line for line in unicode_lines),
            "\n".join("  " + line for line in exchange_lines),
        )
    )


class ARLNFloorsWindow(object):
    def __init__(self):
        try:
            self.blocks = load_configurations()
        except Exception as error:
            Message("Invalid ARLN Floors Configuration", str(error))
            print("ARLN floor configuration error: %s" % error)
            return

        self.w = vanilla.FloatingWindow(
            (600, 440),
            "Apply ARLN Floor Block",
        )
        self.w.intro = vanilla.TextBox(
            (15, 14, -15, 36),
            "Choose one configuration block. Only the selected block will be applied.",
        )
        self.w.blockLabel = vanilla.TextBox((15, 58, 120, 18), "Configuration block")
        self.w.block = vanilla.PopUpButton(
            (140, 54, -15, 25),
            [block["name"] for block in self.blocks],
            callback=self.update_preview,
        )
        self.w.preview = vanilla.TextEditor(
            (15, 92, -15, -62),
            "",
            readOnly=True,
        )
        self.w.status = vanilla.TextBox((15, -42, 360, 18), "Ready")
        self.w.runButton = vanilla.Button(
            (-160, -48, 145, 28),
            "Run Selected Block",
            callback=self.run_selected,
        )
        self.update_preview()
        self.w.open()
        self.w.makeKey()

    def selected_block(self):
        return self.blocks[int(self.w.block.get())]

    def update_preview(self, sender=None):
        self.w.preview.set(block_description(self.selected_block()))

    def run_selected(self, sender):
        block = self.selected_block()
        self.w.status.set("Running %s…" % block["name"])
        apply_configuration_block(block)
        self.w.status.set("Finished %s" % block["name"])


if __name__ == "__main__":
    ARLNFloorsWindow()
