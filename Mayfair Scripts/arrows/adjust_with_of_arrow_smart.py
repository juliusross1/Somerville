#MenuTitle: Adjust with of arrows in a smart way


# Glyphs 3 Macro Panel script
#
# For the current glyph:
#
# • Choose a component name from the dropdown.
# • Enter W1 for layers associated with SemiCondensed masters.
# • Enter W2 for layers associated with SemiExpanded masters.
# • Only the FIRST occurrence of the selected component in each layer
#   is altered.
# • The selected component must have a smart-component axis whose name
#   is "Width" or contains the word "width".
#
# The script measures the response near the component's current smart
# value, calculates the required value from the local linear response,
# and then corrects for rounding.
#
# It re-fetches the component from the layer after every automatic-
# alignment recalculation, avoiding stale GSComponent wrapper objects.

from GlyphsApp import Glyphs, Message
from vanilla import (
    FloatingWindow,
    TextBox,
    PopUpButton,
    EditText,
    Button,
    ProgressBar,
)
from Foundation import NSRunLoop, NSDate


# ---------------------------------------------------------------------
# Basic helpers
# ---------------------------------------------------------------------

def component_name(component):
    """Return the glyph name referenced by a component."""
    try:
        return component.componentName
    except Exception:
        try:
            return component.name
        except Exception:
            return None


def shapes_in_layer(layer):
    """Return a Python list of the layer's shapes."""
    try:
        return list(layer.shapes)
    except Exception:
        return []


def components_in_layer(layer):
    """Return all component shapes in the layer."""
    result = []

    for shape in shapes_in_layer(layer):
        if component_name(shape):
            result.append(shape)

    return result


def first_named_component_index(layer, wanted_name):
    """
    Return the shape index of the first component with wanted_name.

    Later components with the same name are deliberately ignored.
    """
    try:
        shapes = layer.shapes
    except Exception:
        return None

    for index in range(len(shapes)):
        shape = shapes[index]

        if component_name(shape) == wanted_name:
            return index

    return None


def component_at_index(layer, shape_index):
    """
    Re-fetch a component from its layer by shape index.

    We avoid retaining a GSComponent object while automatic alignment
    is being recalculated.
    """
    try:
        shape = layer.shapes[shape_index]
    except Exception:
        return None

    if component_name(shape):
        return shape

    return None


def associated_master(font, layer):
    """
    Return the master associated with a master layer or special layer.
    """
    master_id = None

    try:
        master_id = layer.associatedMasterId
    except Exception:
        pass

    if not master_id:
        try:
            master_id = layer.layerId
        except Exception:
            return None

    for master in font.masters:
        try:
            if master.id == master_id:
                return master
        except Exception:
            pass

    return None


def associated_master_name(font, layer):
    """Return the name of the master associated with the layer."""
    master = associated_master(font, layer)

    if master is None:
        return ""

    try:
        return master.name
    except Exception:
        return str(master)


def process_events(delay=0.005):
    """Allow Glyphs to process alignment and redraw events."""
    try:
        NSRunLoop.currentRunLoop().runUntilDate_(
            NSDate.dateWithTimeIntervalSinceNow_(delay)
        )
    except Exception:
        pass


# ---------------------------------------------------------------------
# Smart-component helpers
# ---------------------------------------------------------------------

def smart_axes_for_component(component):
    """Return the smart axes belonging to a component's referenced glyph."""
    try:
        smart_glyph = component.component
    except Exception:
        return []

    if smart_glyph is None:
        return []

    try:
        return list(smart_glyph.smartComponentAxes)
    except Exception:
        return []


def find_width_axis(component):
    """
    Prefer an axis named exactly Width.

    Otherwise, return the first axis whose name contains "width".
    """
    axes = smart_axes_for_component(component)

    for axis in axes:
        try:
            axis_name = str(axis.name).strip().lower()

            if axis_name == "width":
                return axis
        except Exception:
            pass

    for axis in axes:
        try:
            axis_name = str(axis.name).lower()

            if "width" in axis_name:
                return axis
        except Exception:
            pass

    return None


def axis_identifier(axis):
    """Return the preferred dictionary key for a smart axis."""
    try:
        return axis.id
    except Exception:
        try:
            return axis.name
        except Exception:
            return None


def axis_display_name(axis):
    try:
        return str(axis.name)
    except Exception:
        return str(axis_identifier(axis))


def axis_default_value(axis):
    """
    Return a reasonable default when Glyphs omits the smart value from
    the dictionary.
    """
    try:
        return float(axis.bottomValue)
    except Exception:
        return 0.0


def copy_smart_values(component):
    """Copy the component's smart-values dictionary."""
    result = {}

    try:
        values = component.smartComponentValues

        for key in values:
            try:
                result[key] = float(values[key])
            except Exception:
                result[key] = values[key]

    except Exception:
        pass

    return result


def read_smart_value(component, axis):
    """Read the current value of a smart-component axis."""
    possible_keys = []

    try:
        possible_keys.append(axis.id)
    except Exception:
        pass

    try:
        possible_keys.append(axis.name)
    except Exception:
        pass

    try:
        values = component.smartComponentValues

        for key in possible_keys:
            try:
                if key in values:
                    return float(values[key])
            except Exception:
                pass

    except Exception:
        pass

    for key in possible_keys:
        try:
            return float(
                component.pieceValueForKey_(key)
            )
        except Exception:
            pass

    return axis_default_value(axis)


def set_smart_value_on_component(component, axis_id, axis_name, value):
    """
    Set a smart value on a freshly fetched component.

    Replacing the whole dictionary is tried first because it tends to
    trigger Glyphs' internal change notifications more reliably than
    mutating the wrapper dictionary in place.
    """
    value = float(value)
    values = copy_smart_values(component)

    selected_key = axis_id

    if selected_key is None:
        selected_key = axis_name

    # Preserve an existing key style if the dictionary uses the name
    # rather than the axis ID.
    if axis_name in values and axis_id not in values:
        selected_key = axis_name

    values[selected_key] = value

    try:
        component.smartComponentValues = values
        return
    except Exception:
        pass

    try:
        component.pieceSettings = values
        return
    except Exception:
        pass

    try:
        component.setPieceSettings_(values)
        return
    except Exception:
        pass

    try:
        component.smartComponentValues[selected_key] = value
        return
    except Exception:
        pass

    try:
        component.setPieceValue_forKey_(
            value,
            selected_key,
        )
        return
    except Exception:
        pass

    raise RuntimeError(
        "Could not set smart axis '%s' to %.4f."
        % (
            axis_name,
            value,
        )
    )


def set_value_by_index(
    layer,
    shape_index,
    axis_id,
    axis_name,
    value,
):
    """
    Re-fetch the component and set its smart value.
    """
    component = component_at_index(
        layer,
        shape_index,
    )

    if component is None:
        raise RuntimeError(
            "The selected component could not be re-fetched."
        )

    set_smart_value_on_component(
        component,
        axis_id,
        axis_name,
        value,
    )


# ---------------------------------------------------------------------
# Layer recalculation
# ---------------------------------------------------------------------

def fully_recalculate_layer(layer):
    """
    Force Glyphs to rebuild smart components, rerun automatic alignment,
    and recalculate the layer width.

    Multiple passes are deliberate because automatic alignment may
    propagate through a chain of components.
    """
    for pass_number in range(4):

        try:
            layer.setNeedUpdateShapes()
        except Exception:
            pass

        try:
            layer.setNeedsUpdateShapes()
        except Exception:
            pass

        # Request the interpolated component layers before alignment.
        try:
            for shape in layer.shapes:
                if component_name(shape):
                    try:
                        unused_component_layer = shape.componentLayer
                    except Exception:
                        try:
                            unused_component_layer = (
                                shape.componentLayer()
                            )
                        except Exception:
                            pass
        except Exception:
            pass

        try:
            layer.doAlignComponents()
        except Exception:
            pass

        try:
            layer.updateMetrics()
        except Exception:
            pass

        try:
            layer.syncMetrics()
        except Exception:
            pass

        try:
            unused_bounds = layer.bounds
        except Exception:
            pass

        try:
            unused_width = layer.width
        except Exception:
            pass

        try:
            Glyphs.redraw()
        except Exception:
            pass

        process_events(0.01)

    try:
        layer.doAlignComponents()
    except Exception:
        pass

    try:
        unused_bounds = layer.bounds
    except Exception:
        pass

    try:
        final_width = float(layer.width)
    except Exception:
        final_width = 0.0

    try:
        Glyphs.redraw()
    except Exception:
        pass

    process_events(0.01)

    return final_width


def measure_value(
    layer,
    shape_index,
    axis_id,
    axis_name,
    value,
):
    """
    Set one smart value, force full alignment recalculation, and return
    the resulting layer advance width.
    """
    set_value_by_index(
        layer,
        shape_index,
        axis_id,
        axis_name,
        value,
    )

    return fully_recalculate_layer(layer)


# ---------------------------------------------------------------------
# Linear fitting
# ---------------------------------------------------------------------

def fit_layer_width(
    layer,
    shape_index,
    axis,
    target_width,
    tolerance=1.0,
):
    """
    Determine the smart value using the locally linear relationship
    between the selected component's smart Width value and layer.width.
    """
    axis_id = axis_identifier(axis)
    axis_name = axis_display_name(axis)

    component = component_at_index(
        layer,
        shape_index,
    )

    if component is None:
        return {
            "success": False,
            "value": None,
            "width": float(layer.width),
            "error": None,
            "message": (
                "Could not locate the component at its original "
                "shape index."
            ),
        }

    current_value = read_smart_value(
        component,
        axis,
    )

    # Reapply the current value so that the first measurement is made
    # through exactly the same code path as subsequent measurements.
    current_width = measure_value(
        layer,
        shape_index,
        axis_id,
        axis_name,
        current_value,
    )

    current_error = abs(
        current_width - target_width
    )

    if current_error <= tolerance:
        return {
            "success": True,
            "value": current_value,
            "width": current_width,
            "error": current_error,
            "message": "",
        }

    try:
        nominal_span = abs(
            float(axis.topValue)
            - float(axis.bottomValue)
        )
    except Exception:
        nominal_span = 100.0

    if nominal_span < 1.0:
        nominal_span = 100.0

    # Use a local test step rather than jumping to both axis endpoints.
    test_step = nominal_span * 0.1

    if test_step < 1.0:
        test_step = 1.0

    test_value = current_value + test_step

    test_width = measure_value(
        layer,
        shape_index,
        axis_id,
        axis_name,
        test_value,
    )

    width_change = test_width - current_width

    # Try the other direction if the first local test appeared not to
    # change the width.
    if abs(width_change) < 0.001:
        test_value = current_value - test_step

        test_width = measure_value(
            layer,
            shape_index,
            axis_id,
            axis_name,
            test_value,
        )

        width_change = test_width - current_width

    print(
        "      local test: smart %.4f -> width %.2f; "
        "smart %.4f -> width %.2f"
        % (
            current_value,
            current_width,
            test_value,
            test_width,
        )
    )

    smart_change = test_value - current_value

    if (
        abs(width_change) < 0.001
        or abs(smart_change) < 0.001
    ):
        final_width = measure_value(
            layer,
            shape_index,
            axis_id,
            axis_name,
            current_value,
        )

        return {
            "success": False,
            "value": current_value,
            "width": final_width,
            "error": abs(final_width - target_width),
            "message": (
                "The local smart-value test did not produce a "
                "measurable width change."
            ),
        }

    slope = width_change / smart_change

    calculated_value = (
        current_value
        + (target_width - current_width) / slope
    )

    best_value = current_value
    best_width = current_width
    best_error = current_error

    # Usually one calculation should be enough because the relationship
    # is expected to be linear. Extra corrections accommodate rounding
    # and any delayed alignment update.
    for correction_number in range(6):

        calculated_width = measure_value(
            layer,
            shape_index,
            axis_id,
            axis_name,
            calculated_value,
        )

        calculated_error = abs(
            calculated_width - target_width
        )

        print(
            "      correction %i: smart %.4f -> width %.2f"
            % (
                correction_number + 1,
                calculated_value,
                calculated_width,
            )
        )

        if calculated_error < best_error:
            best_value = calculated_value
            best_width = calculated_width
            best_error = calculated_error

        if calculated_error <= tolerance:
            break

        # Measure another local point from the current calculated value.
        nearby_value = calculated_value + test_step

        nearby_width = measure_value(
            layer,
            shape_index,
            axis_id,
            axis_name,
            nearby_value,
        )

        nearby_width_change = (
            nearby_width - calculated_width
        )

        nearby_value_change = (
            nearby_value - calculated_value
        )

        if abs(nearby_width_change) < 0.001:
            nearby_value = calculated_value - test_step

            nearby_width = measure_value(
                layer,
                shape_index,
                axis_id,
                axis_name,
                nearby_value,
            )

            nearby_width_change = (
                nearby_width - calculated_width
            )

            nearby_value_change = (
                nearby_value - calculated_value
            )

        if (
            abs(nearby_width_change) < 0.001
            or abs(nearby_value_change) < 0.001
        ):
            break

        local_slope = (
            nearby_width_change
            / nearby_value_change
        )

        calculated_value = (
            calculated_value
            + (
                target_width - calculated_width
            ) / local_slope
        )

    # Test small offsets around the best value to handle integral advance
    # width rounding.
    nearby_offsets = (
        -1.0,
        -0.5,
        -0.25,
        0.0,
        0.25,
        0.5,
        1.0,
    )

    for offset in nearby_offsets:
        candidate_value = best_value + offset

        candidate_width = measure_value(
            layer,
            shape_index,
            axis_id,
            axis_name,
            candidate_value,
        )

        candidate_error = abs(
            candidate_width - target_width
        )

        if candidate_error < best_error:
            best_value = candidate_value
            best_width = candidate_width
            best_error = candidate_error

        if candidate_error <= tolerance:
            break

    final_width = measure_value(
        layer,
        shape_index,
        axis_id,
        axis_name,
        best_value,
    )

    final_error = abs(
        final_width - target_width
    )

    if final_error <= tolerance:
        message = ""
    else:
        message = (
            "Closest result was %.2f at smart value %.4f."
            % (
                final_width,
                best_value,
            )
        )

    return {
        "success": final_error <= tolerance,
        "value": best_value,
        "width": final_width,
        "error": final_error,
        "message": message,
    }


# ---------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------

class SmartComponentWidthWindow(object):

    def __init__(self):
        self.font = Glyphs.font
        self.glyph = self.current_glyph()

        if self.font is None or self.glyph is None:
            Message(
                "No Current Glyph",
                "Open a font and edit or select a glyph first.",
            )
            return

        self.component_names = (
            self.collect_component_names()
        )

        if not self.component_names:
            Message(
                "No Components",
                "The current glyph contains no components.",
            )
            return

        self.w = FloatingWindow(
            (430, 220),
            "Set Width with Smart Component",
            autosaveName=(
                "com.juliusross."
                "SetWidthWithFirstSmartComponentV3"
            ),
        )

        y = 18

        self.w.componentLabel = TextBox(
            (15, y + 3, 125, 20),
            "Component:",
        )

        self.w.componentPopup = PopUpButton(
            (140, y, -15, 24),
            self.component_names,
        )

        y += 42

        self.w.w1Label = TextBox(
            (15, y + 3, 225, 20),
            "SemiCondensed width W1:",
        )

        self.w.w1 = EditText(
            (250, y, -15, 24),
            "330",
        )

        y += 34

        self.w.w2Label = TextBox(
            (15, y + 3, 225, 20),
            "SemiExpanded width W2:",
        )

        self.w.w2 = EditText(
            (250, y, -15, 24),
            "450",
        )

        y += 42

        self.w.progress = ProgressBar(
            (15, y, -15, 16),
            minValue=0,
            maxValue=1,
        )

        y += 31

        self.w.runButton = Button(
            (-115, y, -15, 24),
            "Adjust",
            callback=self.run,
        )

        self.w.open()
        self.w.makeKey()

    def current_glyph(self):
        """Return the currently selected or edited glyph."""
        try:
            selected_layers = self.font.selectedLayers

            if selected_layers:
                return selected_layers[0].parent
        except Exception:
            pass

        return None

    def collect_component_names(self):
        """Collect unique component names from all glyph layers."""
        names = []

        for layer in self.glyph.layers:
            for component in components_in_layer(layer):
                name = component_name(component)

                if name and name not in names:
                    names.append(name)

        names.sort()
        return names

    def parse_number(self, control, label):
        text = str(control.get())
        text = text.strip().replace(",", ".")

        try:
            return float(text)
        except Exception:
            raise ValueError(
                "%s must be a number." % label
            )

    def eligible_layers(self):
        """
        Return tuples containing:

            layer, target width, associated master name
        """
        result = []

        w1 = self.parse_number(
            self.w.w1,
            "W1",
        )

        w2 = self.parse_number(
            self.w.w2,
            "W2",
        )

        for layer in self.glyph.layers:
            master_name = associated_master_name(
                self.font,
                layer,
            )

            if "SemiCondensed" in master_name:
                result.append(
                    (
                        layer,
                        w1,
                        master_name,
                    )
                )

            elif "SemiExpanded" in master_name:
                result.append(
                    (
                        layer,
                        w2,
                        master_name,
                    )
                )

        return result

    def run(self, sender):
        try:
            selected_index = (
                self.w.componentPopup.get()
            )

            selected_name = (
                self.component_names[selected_index]
            )

            layer_jobs = self.eligible_layers()

        except Exception as error:
            Message(
                "Invalid Input",
                str(error),
            )
            return

        if not layer_jobs:
            Message(
                "No Matching Layers",
                (
                    "No layers are associated with a "
                    "SemiCondensed or SemiExpanded master."
                ),
            )
            return

        self.w.runButton.enable(False)
        self.w.progress.set(0)

        try:
            progress_indicator = (
                self.w.progress.getNSProgressIndicator()
            )

            progress_indicator.setMaxValue_(
                len(layer_jobs)
            )
        except Exception:
            pass

        Glyphs.clearLog()
        Glyphs.showMacroWindow()

        print("=" * 78)
        print("Glyph: %s" % self.glyph.name)
        print("Component: %s" % selected_name)
        print(
            "Only the first matching component "
            "in each layer is adjusted."
        )
        print("=" * 78)

        successful = 0
        failed = 0
        skipped = 0

        try:
            self.glyph.beginUndo()
        except Exception:
            pass

        try:
            for index in range(len(layer_jobs)):
                (
                    layer,
                    target_width,
                    master_name,
                ) = layer_jobs[index]

                shape_index = first_named_component_index(
                    layer,
                    selected_name,
                )

                if shape_index is None:
                    skipped += 1

                    print(
                        "SKIP  %-40s no %s component"
                        % (
                            layer.name,
                            selected_name,
                        )
                    )

                    self.w.progress.set(
                        index + 1
                    )

                    process_events()
                    continue

                selected_component = component_at_index(
                    layer,
                    shape_index,
                )

                if selected_component is None:
                    failed += 1

                    print(
                        "FAIL  %-40s component could not be fetched"
                        % layer.name
                    )

                    self.w.progress.set(
                        index + 1
                    )

                    process_events()
                    continue

                width_axis = find_width_axis(
                    selected_component
                )

                if width_axis is None:
                    failed += 1

                    print(
                        "FAIL  %-40s no smart axis whose name "
                        "contains Width"
                        % layer.name
                    )

                    self.w.progress.set(
                        index + 1
                    )

                    process_events()
                    continue

                starting_width = fully_recalculate_layer(
                    layer
                )

                print(
                    "TEST  %-40s master=%s"
                    % (
                        layer.name,
                        master_name,
                    )
                )

                try:
                    result = fit_layer_width(
                        layer,
                        shape_index,
                        width_axis,
                        float(target_width),
                        tolerance=1.0,
                    )

                    if result["success"]:
                        status = "OK"
                        successful += 1
                    else:
                        status = "FAIL"
                        failed += 1

                    print(
                        "%-5s %-40s master=%s"
                        % (
                            status,
                            layer.name,
                            master_name,
                        )
                    )

                    if result["value"] is None:
                        value_text = "unchanged"
                    else:
                        value_text = "%.4f" % (
                            result["value"]
                        )

                    print(
                        "      width: %.2f -> %.2f; "
                        "target: %.2f; smart Width: %s"
                        % (
                            starting_width,
                            result["width"],
                            target_width,
                            value_text,
                        )
                    )

                    if result["message"]:
                        print(
                            "      %s"
                            % result["message"]
                        )

                except Exception as error:
                    failed += 1

                    print(
                        "ERROR %-40s %s"
                        % (
                            layer.name,
                            error,
                        )
                    )

                self.w.progress.set(
                    index + 1
                )

                process_events()

        finally:
            try:
                self.glyph.endUndo()
            except Exception:
                pass

            try:
                Glyphs.redraw()
            except Exception:
                pass

            self.w.runButton.enable(True)

        print("-" * 78)

        print(
            "Finished: %i successful, "
            "%i failed, %i skipped."
            % (
                successful,
                failed,
                skipped,
            )
        )

        print("=" * 78)

        Message(
            "Width Adjustment Complete",
            (
                "%s\n\n"
                "%i layers adjusted successfully.\n"
                "%i layers failed.\n"
                "%i layers skipped.\n\n"
                "Only the first matching component "
                "in each layer was altered.\n\n"
                "See the Macro Panel for measurements."
            )
            % (
                self.glyph.name,
                successful,
                failed,
                skipped,
            ),
        )


SmartComponentWidthWindow()