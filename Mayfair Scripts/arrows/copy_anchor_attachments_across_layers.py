# MenuTitle: Copy Selected Component Attachment to All Layers
# -*- coding: utf-8 -*-

from GlyphsApp import Glyphs
import traceback


# --------------------------------------------------------------------
# SETTINGS
# --------------------------------------------------------------------

# If True, do not modify a target layer unless the chosen base anchor
# can be found in that layer.
REQUIRE_BASE_ANCHOR = True

# If True, do not modify a target component unless its source layer
# contains a compatible underscore anchor.
REQUIRE_MARK_ANCHOR = True

# The target component must use automatic alignment for its anchor
# selection to control its placement.
ENABLE_AUTOMATIC_ALIGNMENT = True


# --------------------------------------------------------------------
# HELPERS
# --------------------------------------------------------------------

def safe_string(value):
    if value is None:
        return ""
    try:
        return str(value)
    except Exception:
        return repr(value)


def layer_description(layer):
    glyph_name = "<?>"
    layer_name = "<?>"

    try:
        glyph_name = layer.parent.name
    except Exception:
        pass

    try:
        layer_name = layer.name
    except Exception:
        pass

    return "%s — %s" % (glyph_name, layer_name)


def layer_type_description(layer):
    """
    Give a readable description of the layer type.
    """
    try:
        if layer.isMasterLayer:
            return "master"
    except Exception:
        pass

    try:
        if layer.isSpecialLayer:
            return "special/intermediate"
    except Exception:
        pass

    return "non-master"


def selected_components(layer):
    """
    Return components selected in Edit view.
    """
    result = []

    try:
        for item in layer.selection:
            if item.__class__.__name__ == "GSComponent":
                result.append(item)
    except Exception:
        pass

    if not result:
        try:
            for component in layer.components:
                if component.selected:
                    result.append(component)
        except Exception:
            pass

    return result


def components_as_list(layer):
    try:
        return list(layer.components)
    except Exception:
        result = []

        try:
            count = layer.components.count()
            for index in range(count):
                result.append(layer.components.objectAtIndex_(index))
        except Exception:
            pass

        return result


def anchors_as_list(anchor_collection):
    if anchor_collection is None:
        return []

    try:
        return list(anchor_collection)
    except Exception:
        result = []

        try:
            count = anchor_collection.count()
            for index in range(count):
                result.append(anchor_collection.objectAtIndex_(index))
        except Exception:
            pass

        return result


def explicit_anchors(layer):
    if layer is None:
        return []

    try:
        return anchors_as_list(layer.anchors)
    except Exception:
        return []


def traversing_anchors(layer):
    """
    Return the anchors available in a composite layer, including
    anchors inherited from components.
    """
    if layer is None:
        return []

    try:
        return anchors_as_list(
            layer.anchorsTraversingComponents()
        )
    except Exception:
        return explicit_anchors(layer)


def anchor_names(anchors):
    result = []

    for anchor in anchors:
        try:
            name = safe_string(anchor.name)
        except Exception:
            continue

        if name and name not in result:
            result.append(name)

    return result


def compatible_mark_anchor_names(mark_layer, base_anchor_name):
    """
    A mark anchor such as '_stroke' is compatible with base anchors
    whose names begin with 'stroke':

        _stroke  ->  stroke
        _stroke  ->  stroke_head
        _stroke  ->  stroke_head_tail

    Return all compatible underscore-anchor names, most specific first.
    """
    compatible = []

    for anchor in explicit_anchors(mark_layer):
        try:
            mark_name = safe_string(anchor.name)
        except Exception:
            continue

        if not mark_name.startswith("_"):
            continue

        stem = mark_name[1:]

        if stem and base_anchor_name.startswith(stem):
            compatible.append(mark_name)

    compatible.sort(
        key=lambda name: len(name),
        reverse=True,
    )

    return compatible


def available_base_anchor_names(layer):
    """
    Return all non-underscore anchors available in the containing layer,
    including anchors inherited from its components.
    """
    names = []

    for name in anchor_names(traversing_anchors(layer)):
        if not name.startswith("_") and name not in names:
            names.append(name)

    return names


def component_name(component):
    try:
        return safe_string(component.componentName)
    except Exception:
        try:
            return safe_string(component.name)
        except Exception:
            return "<?>"


def component_source_layer(component):
    try:
        return component.componentLayer
    except Exception:
        return None


def automatic_alignment(component):
    """
    Return the current automatic-alignment state where available.
    """
    try:
        return bool(component.automaticAlignment)
    except Exception:
        return None


def set_automatic_alignment(component, value):
    """
    Set automatic alignment, with a fallback for API variations.
    """
    try:
        component.automaticAlignment = value
        return True
    except Exception:
        pass

    try:
        component.setAutomaticAlignment_(value)
        return True
    except Exception:
        return False


def component_anchor(component):
    try:
        value = component.anchor
    except Exception:
        return None

    if value is None:
        return None

    value = safe_string(value)

    if not value:
        return None

    return value


def set_component_anchor(component, anchor_name):
    """
    Set the base-anchor choice stored on the component.
    """
    try:
        component.anchor = anchor_name
        return True
    except Exception:
        pass

    try:
        component.setAnchor_(anchor_name)
        return True
    except Exception:
        return False


def find_corresponding_component(
    target_layer,
    source_component_index,
    source_component_name,
):
    """
    Find the component corresponding to the selected source component.

    Strategy:

    1. Use the same component index if it contains the same component
       glyph.
    2. Otherwise, use a unique component with the same component name.
    3. If there are multiple same-name candidates, report ambiguity.
    """
    components = components_as_list(target_layer)

    if (
        source_component_index < len(components)
        and component_name(
            components[source_component_index]
        ) == source_component_name
    ):
        return (
            components[source_component_index],
            "same index",
            None,
        )

    same_name = [
        component
        for component in components
        if component_name(component) == source_component_name
    ]

    if len(same_name) == 1:
        return (
            same_name[0],
            "unique name match",
            None,
        )

    if len(same_name) == 0:
        return (
            None,
            None,
            "no component named '%s'" % source_component_name,
        )

    return (
        None,
        None,
        "%d components named '%s'; correspondence is ambiguous"
        % (
            len(same_name),
            source_component_name,
        ),
    )


def trigger_component_update(component):
    """
    Ask Glyphs to recalculate automatic alignment when that API is
    exposed. Setting component.anchor normally triggers this already,
    so failure here is not considered an error.
    """
    try:
        component.updateAlignment()
        return True
    except Exception:
        pass

    try:
        component.updateAlignment_(True)
        return True
    except Exception:
        return False


# --------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------

Glyphs.clearLog()
Glyphs.showMacroWindow()

print("=" * 80)
print("COPY SELECTED COMPONENT ATTACHMENT TO ALL LAYERS")
print("=" * 80)

font = Glyphs.font

if font is None:
    print("ERROR: No font is open.")

else:
    current_layer = (
        font.selectedLayers[0]
        if font.selectedLayers
        else None
    )

    if current_layer is None:
        print("ERROR: No current layer could be found.")

    else:
        glyph = current_layer.parent
        selected = selected_components(current_layer)

        if not selected:
            print(
                "ERROR: Select one component in Edit view and "
                "run the script again."
            )

        elif len(selected) > 1:
            print(
                "ERROR: More than one component is selected. "
                "Select exactly one component."
            )

        else:
            source_component = selected[0]
            source_component_name = component_name(source_component)
            current_components = components_as_list(current_layer)

            try:
                source_component_index = current_components.index(
                    source_component
                )
            except Exception:
                source_component_index = -1

            source_anchor_name = component_anchor(source_component)
            source_mark_layer = component_source_layer(source_component)

            print("Glyph                  : %s" % glyph.name)
            print("Source layer           : %s" % current_layer.name)
            print(
                "Source layer type      : %s"
                % layer_type_description(current_layer)
            )
            print(
                "Selected component     : %s"
                % source_component_name
            )
            print(
                "Component index        : %s"
                % (
                    source_component_index
                    if source_component_index >= 0
                    else "unknown"
                )
            )
            print(
                "Automatic alignment    : %s"
                % automatic_alignment(source_component)
            )
            print(
                "Chosen base anchor     : %s"
                % (
                    source_anchor_name
                    if source_anchor_name
                    else "automatic/default"
                )
            )

            if source_mark_layer is not None:
                print(
                    "Mark source layer     : %s"
                    % source_mark_layer.name
                )
            else:
                print("Mark source layer     : unavailable")

            print()

            if source_component_index < 0:
                print(
                    "ERROR: Could not determine the selected "
                    "component's index."
                )

            elif not source_anchor_name:
                print(
                    "ERROR: The selected component has no explicit "
                    "anchor choice."
                )
                print()
                print(
                    "Choose an anchor in the component's Anchor popup "
                    "before running this script."
                )

            else:
                source_compatible_marks = (
                    compatible_mark_anchor_names(
                        source_mark_layer,
                        source_anchor_name,
                    )
                )

                source_base_names = available_base_anchor_names(
                    current_layer
                )

                print("-" * 80)
                print("SOURCE ATTACHMENT")
                print("-" * 80)
                print(
                    "Chosen base anchor     : %s"
                    % source_anchor_name
                )

                if source_compatible_marks:
                    print(
                        "Compatible mark anchor: %s"
                        % source_compatible_marks[0]
                    )

                    if len(source_compatible_marks) > 1:
                        print(
                            "Other compatible marks: %s"
                            % ", ".join(
                                source_compatible_marks[1:]
                            )
                        )
                else:
                    print(
                        "Compatible mark anchor: NONE FOUND"
                    )

                if source_anchor_name in source_base_names:
                    print(
                        "Base anchor available : yes"
                    )
                else:
                    print(
                        "Base anchor available : not returned by "
                        "anchorsTraversingComponents()"
                    )

                print()
                print("-" * 80)
                print("PROCESSING TARGET LAYERS")
                print("-" * 80)

                results = {
                    "changed": [],
                    "already_same": [],
                    "source": [],
                    "missing_component": [],
                    "ambiguous_component": [],
                    "missing_mark_anchor": [],
                    "missing_base_anchor": [],
                    "errors": [],
                }

                interface_disabled = False

                try:
                    try:
                        font.disableUpdateInterface()
                        interface_disabled = True
                    except Exception:
                        pass

                    for target_layer in glyph.layers:
                        print()
                        print("=" * 80)
                        print(
                            "LAYER: %s"
                            % target_layer.name
                        )
                        print(
                            "TYPE : %s"
                            % layer_type_description(target_layer)
                        )

                        if target_layer == current_layer:
                            print(
                                "STATUS: SOURCE LAYER — no change"
                            )
                            results["source"].append(
                                target_layer.name
                            )
                            continue

                        (
                            target_component,
                            match_method,
                            match_error,
                        ) = find_corresponding_component(
                            target_layer,
                            source_component_index,
                            source_component_name,
                        )

                        if target_component is None:
                            print(
                                "STATUS: SKIPPED"
                            )
                            print(
                                "REASON: %s"
                                % match_error
                            )

                            if (
                                match_error
                                and "ambiguous" in match_error
                            ):
                                results[
                                    "ambiguous_component"
                                ].append(
                                    (
                                        target_layer.name,
                                        match_error,
                                    )
                                )
                            else:
                                results[
                                    "missing_component"
                                ].append(
                                    (
                                        target_layer.name,
                                        match_error,
                                    )
                                )

                            continue

                        print(
                            "Component found        : %s"
                            % component_name(target_component)
                        )
                        print(
                            "Matching method        : %s"
                            % match_method
                        )

                        target_mark_layer = component_source_layer(
                            target_component
                        )

                        if target_mark_layer is None:
                            target_mark_layer_name = "unavailable"
                        else:
                            target_mark_layer_name = (
                                target_mark_layer.name
                            )

                        print(
                            "Mark source layer      : %s"
                            % target_mark_layer_name
                        )

                        compatible_marks = (
                            compatible_mark_anchor_names(
                                target_mark_layer,
                                source_anchor_name,
                            )
                        )

                        if compatible_marks:
                            print(
                                "Compatible mark anchor: %s"
                                % compatible_marks[0]
                            )

                            if len(compatible_marks) > 1:
                                print(
                                    "Other matches         : %s"
                                    % ", ".join(
                                        compatible_marks[1:]
                                    )
                                )
                        else:
                            print(
                                "Compatible mark anchor: NONE"
                            )

                            if REQUIRE_MARK_ANCHOR:
                                print("STATUS: SKIPPED")
                                print(
                                    "REASON: The target mark layer "
                                    "has no underscore anchor compatible "
                                    "with '%s'."
                                    % source_anchor_name
                                )

                                results[
                                    "missing_mark_anchor"
                                ].append(
                                    target_layer.name
                                )
                                continue

                        target_base_names = (
                            available_base_anchor_names(
                                target_layer
                            )
                        )

                        base_anchor_available = (
                            source_anchor_name
                            in target_base_names
                        )

                        print(
                            "Chosen base available  : %s"
                            % (
                                "yes"
                                if base_anchor_available
                                else "no"
                            )
                        )

                        if (
                            REQUIRE_BASE_ANCHOR
                            and not base_anchor_available
                        ):
                            print("STATUS: SKIPPED")
                            print(
                                "REASON: The containing layer does "
                                "not supply a base anchor named '%s'."
                                % source_anchor_name
                            )

                            if target_base_names:
                                print(
                                    "Available base anchors: %s"
                                    % ", ".join(
                                        sorted(target_base_names)
                                    )
                                )
                            else:
                                print(
                                    "Available base anchors: none"
                                )

                            results[
                                "missing_base_anchor"
                            ].append(
                                target_layer.name
                            )
                            continue

                        old_anchor_name = component_anchor(
                            target_component
                        )
                        old_alignment = automatic_alignment(
                            target_component
                        )

                        print(
                            "Previous anchor choice : %s"
                            % (
                                old_anchor_name
                                if old_anchor_name
                                else "automatic/default"
                            )
                        )
                        print(
                            "Previous auto alignment: %s"
                            % old_alignment
                        )

                        needs_anchor_change = (
                            old_anchor_name
                            != source_anchor_name
                        )

                        needs_alignment_change = (
                            ENABLE_AUTOMATIC_ALIGNMENT
                            and old_alignment is not True
                        )

                        if (
                            not needs_anchor_change
                            and not needs_alignment_change
                        ):
                            print(
                                "STATUS: ALREADY CORRECT"
                            )
                            results["already_same"].append(
                                target_layer.name
                            )
                            continue

                        try:
                            if ENABLE_AUTOMATIC_ALIGNMENT:
                                alignment_set = (
                                    set_automatic_alignment(
                                        target_component,
                                        True,
                                    )
                                )

                                if not alignment_set:
                                    raise RuntimeError(
                                        "Could not enable automatic "
                                        "alignment."
                                    )

                            anchor_set = set_component_anchor(
                                target_component,
                                source_anchor_name,
                            )

                            if not anchor_set:
                                raise RuntimeError(
                                    "Could not set component.anchor."
                                )

                            trigger_component_update(
                                target_component
                            )

                            new_anchor_name = component_anchor(
                                target_component
                            )
                            new_alignment = automatic_alignment(
                                target_component
                            )

                            print(
                                "New anchor choice      : %s"
                                % new_anchor_name
                            )
                            print(
                                "New auto alignment     : %s"
                                % new_alignment
                            )

                            if new_anchor_name != source_anchor_name:
                                raise RuntimeError(
                                    "Glyphs did not retain the requested "
                                    "anchor value."
                                )

                            print("STATUS: CHANGED")

                            results["changed"].append(
                                (
                                    target_layer.name,
                                    old_anchor_name,
                                    new_anchor_name,
                                    match_method,
                                )
                            )

                        except Exception as error:
                            print("STATUS: ERROR")
                            print("ERROR : %s" % error)

                            results["errors"].append(
                                (
                                    target_layer.name,
                                    safe_string(error),
                                )
                            )

                except Exception:
                    print()
                    print("=" * 80)
                    print("UNEXPECTED SCRIPT ERROR")
                    print("=" * 80)
                    print(traceback.format_exc())

                finally:
                    if interface_disabled:
                        try:
                            font.enableUpdateInterface()
                        except Exception:
                            pass

                try:
                    font.currentTab.redraw()
                except Exception:
                    pass

                # ----------------------------------------------------
                # SUMMARY
                # ----------------------------------------------------

                total_layers = len(glyph.layers)

                print()
                print()
                print("=" * 80)
                print("FINAL SUMMARY")
                print("=" * 80)
                print("Glyph                  : %s" % glyph.name)
                print(
                    "Component              : %s"
                    % source_component_name
                )
                print(
                    "Copied base anchor      : %s"
                    % source_anchor_name
                )

                if source_compatible_marks:
                    print(
                        "Source mark anchor     : %s"
                        % source_compatible_marks[0]
                    )

                print(
                    "Total glyph layers      : %d"
                    % total_layers
                )
                print(
                    "Source layers           : %d"
                    % len(results["source"])
                )
                print(
                    "Changed                 : %d"
                    % len(results["changed"])
                )
                print(
                    "Already correct         : %d"
                    % len(results["already_same"])
                )
                print(
                    "Missing component       : %d"
                    % len(results["missing_component"])
                )
                print(
                    "Ambiguous component     : %d"
                    % len(results["ambiguous_component"])
                )
                print(
                    "Missing mark anchor     : %d"
                    % len(results["missing_mark_anchor"])
                )
                print(
                    "Missing base anchor     : %d"
                    % len(results["missing_base_anchor"])
                )
                print(
                    "Errors                  : %d"
                    % len(results["errors"])
                )

                if results["changed"]:
                    print()
                    print("-" * 80)
                    print("CHANGED LAYERS")
                    print("-" * 80)

                    for (
                        layer_name,
                        old_name,
                        new_name,
                        method,
                    ) in results["changed"]:
                        print(
                            "%s"
                            % layer_name
                        )
                        print(
                            "    %s -> %s"
                            % (
                                old_name
                                if old_name
                                else "automatic/default",
                                new_name,
                            )
                        )
                        print(
                            "    component match: %s"
                            % method
                        )

                if results["already_same"]:
                    print()
                    print("-" * 80)
                    print("ALREADY CORRECT")
                    print("-" * 80)

                    for layer_name in results["already_same"]:
                        print(layer_name)

                skipped_count = (
                    len(results["missing_component"])
                    + len(results["ambiguous_component"])
                    + len(results["missing_mark_anchor"])
                    + len(results["missing_base_anchor"])
                )

                if skipped_count:
                    print()
                    print("-" * 80)
                    print("SKIPPED LAYERS")
                    print("-" * 80)

                    for layer_name, reason in results[
                        "missing_component"
                    ]:
                        print(
                            "%s: %s"
                            % (layer_name, reason)
                        )

                    for layer_name, reason in results[
                        "ambiguous_component"
                    ]:
                        print(
                            "%s: %s"
                            % (layer_name, reason)
                        )

                    for layer_name in results[
                        "missing_mark_anchor"
                    ]:
                        print(
                            "%s: no compatible mark anchor"
                            % layer_name
                        )

                    for layer_name in results[
                        "missing_base_anchor"
                    ]:
                        print(
                            "%s: base anchor '%s' unavailable"
                            % (
                                layer_name,
                                source_anchor_name,
                            )
                        )

                if results["errors"]:
                    print()
                    print("-" * 80)
                    print("ERRORS")
                    print("-" * 80)

                    for layer_name, error in results["errors"]:
                        print(
                            "%s: %s"
                            % (layer_name, error)
                        )

                print()
                print("=" * 80)

                if results["errors"]:
                    print(
                        "COMPLETED WITH ERRORS: %d layer(s) changed."
                        % len(results["changed"])
                    )
                elif skipped_count:
                    print(
                        "COMPLETED WITH SKIPS: %d layer(s) changed; "
                        "%d layer(s) skipped."
                        % (
                            len(results["changed"]),
                            skipped_count,
                        )
                    )
                else:
                    print(
                        "COMPLETED SUCCESSFULLY: %d layer(s) changed."
                        % len(results["changed"])
                    )

                print("=" * 80)