#MenuTitle: Import Math Italic Glyphs From Source
# -*- coding: utf-8 -*-
"""
Copy Math Italic Glyphs From Source

This Glyphs 3 script copies the math italic Unicode glyphs listed in
UNICODE_TEXT from an open source font into the frontmost destination font.
The source font is guessed from the open fonts by looking for "Italic" in
the font name; the destination is guessed as the frontmost font. Both can
be changed in the small dialog before pressing Copy.

For each listed Unicode, the script asks Glyphs for the corresponding math
glyph name, derives the plain source glyph name, then copies outlines,
components, layers, stems, smart component axes/settings, and the Unicode
assignment into the destination. If the source has matching .ssNN alternates,
those are copied as target .ssNN glyphs too.

When a copied glyph depends on a component that already exists in the
destination, the source component is copied with a -italic suffix and the new
glyph is repointed to that suffixed component. At the end, the script opens a
new tab in the destination font containing the newly created base and .ssNN
math glyphs, but not the internal component glyphs.
"""

import re
import sys
import vanilla
from GlyphsApp import Glyphs, GSGlyph, GSSmartComponentAxis
try:
    from GlyphsApp import CORNER, SEGMENT, CAP
except Exception:
    CORNER = SEGMENT = CAP = None


UNICODE_TEXT = """
1D6FB  # gradientitalic-math
1D434  # Aitalic-math
1D6E2  # Alphaitalic-math
1D435  # Bitalic-math
1D6E3  # Betaitalic-math
1D436  # Citalic-math
1D437  # Ditalic-math
1D438  # Eitalic-math
1D6E6  # Epsilonitalic-math
1D439  # Fitalic-math
1D43A  # Gitalic-math
1D43B  # Hitalic-math
1D6E8  # Etaitalic-math
1D43C  # Iitalic-math
1D6EA  # Iotaitalic-math
1D43D  # Jitalic-math
1D43E  # Kitalic-math
1D6EB  # Kappaitalic-math
1D43F  # Litalic-math
1D440  # Mitalic-math
1D6ED  # Muitalic-math
1D441  # Nitalic-math
1D6EE  # Nuitalic-math
1D442  # Oitalic-math
1D6F0  # Omicronitalic-math
1D443  # Pitalic-math
1D6F2  # Rhoitalic-math
1D444  # Qitalic-math
1D445  # Ritalic-math
1D446  # Sitalic-math
1D447  # Titalic-math
1D6F5  # Tauitalic-math
1D448  # Uitalic-math
1D449  # Vitalic-math
1D44A  # Witalic-math
1D44B  # Xitalic-math
1D6F8  # Chiitalic-math
1D44C  # Yitalic-math
1D6F6  # Upsilonitalic-math
1D44D  # Zitalic-math
1D6E7  # Zetaitalic-math
210E  # planckconstant
1D44E  # aitalic-math
1D44F  # bitalic-math
1D450  # citalic-math
1D451  # ditalic-math
1D452  # eitalic-math
1D453  # fitalic-math
1D454  # gitalic-math
1D6A4  # idotlessitalic-math
1D456  # iitalic-math
1D6A5  # jdotlessitalic-math
1D457  # jitalic-math
1D458  # kitalic-math
1D459  # litalic-math
1D45A  # mitalic-math
1D45B  # nitalic-math
1D45C  # oitalic-math
1D45D  # pitalic-math
1D45E  # qitalic-math
1D45F  # ritalic-math
1D460  # sitalic-math
1D461  # titalic-math
1D462  # uitalic-math
1D463  # vitalic-math
1D464  # witalic-math
1D465  # xitalic-math
1D466  # yitalic-math
1D467  # zitalic-math
1D6E4  # Gammaitalic-math
1D6E5  # Deltaitalic-math
1D6E9  # Thetaitalic-math
1D6EC  # Lambdaitalic-math
1D6EF  # Xiitalic-math
1D6F1  # Piitalic-math
1D6F3  # ThetaSymbolitalic-math
1D6F4  # Sigmaitalic-math
1D6F7  # Phiitalic-math
1D6F9  # Psiitalic-math
1D6FA  # Omegaitalic-math
1D6FC  # alphaitalic-math
1D6FD  # betaitalic-math
1D6FE  # gammaitalic-math
1D6FF  # deltaitalic-math
1D700  # epsilonitalic-math
1D701  # zetaitalic-math
1D702  # etaitalic-math
1D703  # thetaitalic-math
1D704  # iotaitalic-math
1D705  # kappaitalic-math
1D706  # lambdaitalic-math
1D707  # muitalic-math
1D708  # nuitalic-math
1D709  # xiitalic-math
1D70A  # omicronitalic-math
1D70B  # piitalic-math
1D70C  # rhoitalic-math
1D70D  # sigmafinalitalic-math
1D70E  # sigmaitalic-math
1D70F  # tauitalic-math
1D710  # upsilonitalic-math
1D711  # phiitalic-math
1D712  # chiitalic-math
1D713  # psiitalic-math
1D714  # omegaitalic-math
1D716  # epsilonLunateSymbolitalic-math
1D717  # thetaSymbolitalic-math
1D718  # kappaSymbolitalic-math
1D719  # phiSymbolitalic-math
1D71A  # rhoSymbolitalic-math
1D71B  # piSymbolitalic-math
1D715  # partialdiffitalic-math
"""

CORNER_COMPONENT_TYPES = tuple(t for t in (CORNER, SEGMENT, CAP) if t is not None)
CORNER_COMPONENT_PREFIXES = ("_corner.", "_cap.", "_segment.", "_brush.")
COMPONENT_RENAME_SUFFIX = "-italic"
STYLISTIC_SET_SUFFIX_RE = re.compile(r"\.ss\d+$")


def unicode_values_from_text(text):
    values = []
    for line in text.splitlines():
        for match in re.findall(r"\b[0-9A-Fa-f]{4,6}\b", line):
            value = match.upper()
            if value not in values:
                values.append(value)
    return values


def font_label(font):
    path = getattr(font, "filepath", None)
    if path and hasattr(path, "lastPathComponent"):
        path_text = path.lastPathComponent()
    elif path:
        path_text = str(path).split("/")[-1]
    else:
        path_text = "unsaved"
    return "%s - %s" % (font.familyName or "Untitled", path_text)


def font_text_for_guess(font):
    text_parts = [font_label(font)]
    for attribute_name in ("familyName", "fontName", "fullName"):
        value = getattr(font, attribute_name, None)
        if value:
            text_parts.append(str(value))
    return " ".join(text_parts)


def guessed_source_index(fonts, destination_font):
    italic_indices = []
    for index, font in enumerate(fonts):
        if re.search(r"\bItalic\b", font_text_for_guess(font), re.IGNORECASE):
            italic_indices.append(index)

    for index in italic_indices:
        if fonts[index] is not destination_font:
            return index

    if italic_indices:
        return italic_indices[0]

    return 0


def font_index(fonts, font):
    for index, candidate in enumerate(fonts):
        if candidate is font:
            return index
    return 0


def glyph_for_unicode(font, unicode_value):
    if hasattr(font, "glyphForUnicode_"):
        glyph = font.glyphForUnicode_(unicode_value)
        if glyph is not None:
            return glyph

    for glyph in font.glyphs:
        unicodes = []
        if glyph.unicode:
            unicodes.append(glyph.unicode.upper())
        if getattr(glyph, "unicodes", None):
            unicodes.extend([u.upper() for u in glyph.unicodes if u])
        if unicode_value in unicodes:
            return glyph

    return None


def glyph_info_for_unicode(unicode_value):
    if hasattr(Glyphs, "glyphInfoForUnicode"):
        return Glyphs.glyphInfoForUnicode(unicode_value)
    if hasattr(Glyphs, "glyphInfoForUnicode_"):
        return Glyphs.glyphInfoForUnicode_(unicode_value)
    return None


def source_name_from_info(info, target_name):
    components = getattr(info, "components", None)
    if components:
        return components[0].name

    source_name = target_name
    replacements = [
        "sansbolditalic-math",
        "bolditalic-math",
        "sansitalic-math",
        "italic-math",
    ]
    for replacement in replacements:
        source_name = source_name.replace(replacement, "")
    return source_name.rstrip("-")


def target_map():
    targets = []
    for unicode_value in unicode_values_from_text(UNICODE_TEXT):
        info = glyph_info_for_unicode(unicode_value)
        if info is None:
            print("No Glyphs info for U+%s" % unicode_value)
            continue

        target_name = info.name
        source_name = source_name_from_info(info, target_name)
        targets.append((unicode_value, target_name, source_name))
    return targets


def append_created_name(created_glyph_names, glyph_name):
    if glyph_name not in created_glyph_names:
        created_glyph_names.append(glyph_name)


def open_destination_tab(destination_font, glyph_names):
    if not glyph_names:
        return

    tab_text = "/" + "/".join(glyph_names)
    try:
        destination_font.newTab(tab_text)
    except Exception as error:
        print_warning("Could not open destination tab: %s" % error)


def print_warning(message):
    sys.stderr.write("  Warning: %s\n" % message)
    sys.stderr.flush()


def stylistic_set_source_names(source_font, source_name):
    source_names = []
    pattern = re.compile(r"^%s(\.ss\d+)$" % re.escape(source_name))
    for glyph in source_font.glyphs:
        match = pattern.match(glyph.name)
        if match:
            source_names.append((match.group(1), glyph.name))

    return [
        name
        for suffix, name in sorted(source_names, key=lambda item: int(item[0].replace(".ss", "")))
    ]


def master_index_for_id(font, master_id):
    for index, master in enumerate(font.masters):
        if master.id == master_id:
            return index
    return None


def master_for_id(font, master_id):
    for master in font.masters:
        if master.id == master_id:
            return master
    return None


def copy_stems(source, target):
    if hasattr(source, "stems") and hasattr(target, "stems"):
        try:
            target.stems = [stem.copy() for stem in source.stems]
        except Exception:
            try:
                target.stems = source.stems.copy()
            except Exception as error:
                print("  Could not copy stems for %s: %s" % (getattr(target, "name", "glyph"), error))


def axis_identifier(axis):
    for attribute_name in ("id", "axisId"):
        value = getattr(axis, attribute_name, None)
        if value is None:
            continue
        if callable(value):
            value = value()
        if value:
            return str(value)
    return None


def copy_smart_component_axes(source_glyph, target_glyph):
    axes = list(getattr(source_glyph, "smartComponentAxes", []) or [])
    if not axes:
        return {}

    target_glyph.smartComponentAxes = []
    axis_id_map = {}
    for source_axis in axes:
        try:
            target_axis = source_axis.copy()
        except Exception:
            target_axis = GSSmartComponentAxis()
            for attribute_name in ("name", "bottomValue", "topValue"):
                if hasattr(source_axis, attribute_name):
                    setattr(target_axis, attribute_name, getattr(source_axis, attribute_name))

        target_glyph.smartComponentAxes.append(target_axis)
        source_axis_id = axis_identifier(source_axis)
        target_axis_id = axis_identifier(target_axis)
        if source_axis_id and target_axis_id:
            axis_id_map[source_axis_id] = target_axis_id

    return axis_id_map


def remap_dict_keys(value, key_map):
    if not value or not key_map:
        return value

    remapped = {}
    for key, item in dict(value).items():
        remapped[key_map.get(str(key), key)] = item
    return remapped


def remap_layer_smart_settings(layer, axis_id_map):
    if not axis_id_map:
        return

    if getattr(layer, "smartComponentPoleMapping", None):
        try:
            pole_mapping = dict(layer.smartComponentPoleMapping or {})
        except Exception:
            pole_mapping = None
        if pole_mapping:
            for old_axis_id, value in pole_mapping.items():
                new_axis_id = axis_id_map.get(str(old_axis_id))
                if new_axis_id and new_axis_id != old_axis_id:
                    layer.smartComponentPoleMapping[new_axis_id] = value
                    try:
                        del layer.smartComponentPoleMapping[old_axis_id]
                    except Exception:
                        pass

    try:
        part_selection = layer.valueForKey_("partSelection")
    except Exception:
        part_selection = None
    if part_selection:
        layer.setValue_forKey_(remap_dict_keys(part_selection, axis_id_map), "partSelection")


def remap_component_smart_values(component, axis_id_map):
    if not axis_id_map or not hasattr(component, "smartComponentValues"):
        return

    try:
        smart_values = dict(component.smartComponentValues or {})
    except Exception:
        smart_values = None
    if not smart_values:
        return

    for old_axis_id, value in smart_values.items():
        new_axis_id = axis_id_map.get(str(old_axis_id))
        if new_axis_id and new_axis_id != old_axis_id:
            component.smartComponentValues[new_axis_id] = value
            try:
                del component.smartComponentValues[old_axis_id]
            except Exception:
                pass


def destination_master_for_source_layer(source_font, destination_font, source_layer):
    source_master_id = source_layer.associatedMasterId or source_layer.layerId
    source_index = master_index_for_id(source_font, source_master_id)
    source_master = master_for_id(source_font, source_master_id)

    if source_master is not None:
        for destination_master in destination_font.masters:
            if destination_master.name == source_master.name:
                return destination_master

    if source_index is not None and source_index < len(destination_font.masters):
        return destination_font.masters[source_index]

    if destination_font.masters:
        return destination_font.masters[0]

    return None


def unique_component_name(destination_font, component_name, reserved_names):
    candidate = component_name + COMPONENT_RENAME_SUFFIX
    counter = 2
    while destination_font.glyphs[candidate] is not None or candidate in reserved_names:
        candidate = "%s%s.%i" % (component_name, COMPONENT_RENAME_SUFFIX, counter)
        counter += 1
    return candidate


def assign_unicode_if_available(destination_font, component_source, new_component, skipped):
    component_unicode = component_source.unicode
    if not component_unicode:
        return

    existing_unicode_glyph = glyph_for_unicode(destination_font, component_unicode)
    if existing_unicode_glyph is None:
        new_component.unicode = component_unicode
        return

    skipped["component_unicode_exists"] += 1
    print(
        "  Copied %s without U+%s because it already exists as %s."
        % (new_component.name, component_unicode, existing_unicode_glyph.name)
    )


def component_name_from_object(component):
    for attribute_name in ("componentName", "name"):
        if hasattr(component, attribute_name):
            value = getattr(component, attribute_name)
            if value:
                return value
    return None


def set_component_name(component, component_name):
    did_set = False
    for attribute_name in ("componentName", "name"):
        if hasattr(component, attribute_name):
            try:
                setattr(component, attribute_name, component_name)
                did_set = True
            except Exception:
                pass
    return did_set


def rewrite_component_references(layer, component_name_map, smart_axis_maps):
    for component in layer.components:
        component_name = component_name_from_object(component)
        remap_component_smart_values(component, smart_axis_maps.get(component_name))
        new_component_name = component_name_map.get(component_name)
        if new_component_name is not None and new_component_name != component_name:
            set_component_name(component, new_component_name)

    for shape in layer.shapes:
        component_name = component_name_from_object(shape)
        remap_component_smart_values(shape, smart_axis_maps.get(component_name))
        new_component_name = component_name_map.get(component_name)
        if new_component_name is not None and new_component_name != component_name:
            if set_component_name(shape, new_component_name):
                print("  Repointed component %s -> %s" % (component_name, new_component_name))

    for hint in layer.hints:
        hint_name = getattr(hint, "name", None)
        new_hint_name = component_name_map.get(hint_name)
        if new_hint_name is not None and new_hint_name != hint_name:
            hint.name = new_hint_name


def copy_layer_to_master(source_layer, target_glyph, destination_master, component_name_map, smart_axis_maps, target_axis_map):
    new_layer = source_layer.copy()
    new_layer.layerId = destination_master.id
    new_layer.associatedMasterId = destination_master.id
    remap_layer_smart_settings(new_layer, target_axis_map)
    rewrite_component_references(new_layer, component_name_map, smart_axis_maps)
    copy_stems(source_layer, new_layer)
    target_glyph.layers[destination_master.id] = new_layer


def copy_special_layer(source_font, destination_font, source_layer, target_glyph, component_name_map, smart_axis_maps, target_axis_map):
    new_layer = source_layer.copy()
    destination_master = destination_master_for_source_layer(source_font, destination_font, source_layer)
    if destination_master is not None:
        new_layer.associatedMasterId = destination_master.id
    remap_layer_smart_settings(new_layer, target_axis_map)
    rewrite_component_references(new_layer, component_name_map, smart_axis_maps)
    copy_stems(source_layer, new_layer)
    target_glyph.layers.append(new_layer)


def copy_glyph_layers(source_font, destination_font, source_glyph, target_glyph, component_name_map, smart_axis_maps, target_axis_map):
    for source_layer in source_glyph.layers:
        if source_layer.isMasterLayer:
            destination_master = destination_master_for_source_layer(source_font, destination_font, source_layer)
            if destination_master is not None:
                copy_layer_to_master(
                    source_layer,
                    target_glyph,
                    destination_master,
                    component_name_map,
                    smart_axis_maps,
                    target_axis_map,
                )
        else:
            copy_special_layer(
                source_font,
                destination_font,
                source_layer,
                target_glyph,
                component_name_map,
                smart_axis_maps,
                target_axis_map,
            )


def remove_layer_from_glyph(glyph, layer):
    for method_name in ("remove_", "removeObject_", "removeObject", "removeLayer_"):
        method = getattr(glyph.layers, method_name, None)
        if method is None:
            continue
        try:
            method(layer)
            return True
        except Exception:
            pass

    try:
        index = list(glyph.layers).index(layer)
        del glyph.layers[index]
        return True
    except Exception:
        return False


def is_master_layer(layer):
    value = getattr(layer, "isMasterLayer", False)
    if callable(value):
        try:
            value = value()
        except Exception:
            value = False
    return bool(value)


def clear_glyph_for_overwrite(glyph):
    removed_layers = 0
    for layer in reversed(list(glyph.layers)):
        if is_master_layer(layer):
            continue
        if remove_layer_from_glyph(glyph, layer):
            removed_layers += 1

    try:
        glyph.smartComponentAxes = []
    except Exception:
        pass

    try:
        glyph.stems = []
    except Exception:
        pass

    return removed_layers


def warn_unrepointed_components(target_glyph, component_name_map):
    warned = set()
    for layer in target_glyph.layers:
        for shape in layer.shapes:
            component_name = component_name_from_object(shape)
            new_component_name = component_name_map.get(component_name)
            if new_component_name is not None and new_component_name != component_name:
                warning_key = (target_glyph.name, component_name, new_component_name)
                if warning_key in warned:
                    continue
                warned.add(warning_key)
                print_warning(
                    "%s still references %s instead of %s"
                    % (target_glyph.name, component_name, new_component_name)
                )


def append_component_reference(references, component_name, is_special_component=False):
    if not component_name:
        return

    for existing_name, existing_is_special in references:
        if existing_name == component_name:
            if is_special_component and not existing_is_special:
                references.remove((existing_name, existing_is_special))
                references.append((component_name, True))
            return

    references.append((component_name, is_special_component))


def component_references_in_glyph(glyph):
    references = []
    for layer in glyph.layers:
        for component in layer.components:
            append_component_reference(references, component_name_from_object(component))

        for shape in layer.shapes:
            component_name = component_name_from_object(shape)
            if component_name:
                append_component_reference(references, component_name)

        for hint in layer.hints:
            hint_name = getattr(hint, "name", None)
            if not hint_name:
                continue

            hint_type = getattr(hint, "type", None)
            if hint_type in CORNER_COMPONENT_TYPES or hint_name.startswith(CORNER_COMPONENT_PREFIXES):
                append_component_reference(references, hint_name, True)

    return references


def copy_missing_component_glyphs(
    source_font,
    destination_font,
    source_glyph,
    copied,
    skipped,
    component_name_map,
    smart_axis_maps,
    created_glyph_names,
    stack=None,
):
    if stack is None:
        stack = set()

    for component_name, is_special_component in component_references_in_glyph(source_glyph):
        if component_name in stack:
            continue
        if component_name in component_name_map:
            continue

        component_source = source_font.glyphs[component_name]
        if component_source is None:
            if not is_special_component:
                skipped["missing_components"] += 1
                print("  Missing component in source: %s" % component_name)
            continue

        if destination_font.glyphs[component_name] is None and component_name not in component_name_map.values():
            destination_component_name = component_name
        else:
            destination_component_name = unique_component_name(destination_font, component_name, component_name_map.values())
            copied["renamed_components"] += 1
            print(
                "  Destination already has %s; copying source component as %s."
                % (component_name, destination_component_name)
            )

        component_name_map[component_name] = destination_component_name

        stack.add(component_name)
        copy_missing_component_glyphs(
            source_font,
            destination_font,
            component_source,
            copied,
            skipped,
            component_name_map,
            smart_axis_maps,
            created_glyph_names,
            stack,
        )
        stack.remove(component_name)

        if destination_font.glyphs[destination_component_name] is not None:
            continue

        new_component = GSGlyph(destination_component_name)
        assign_unicode_if_available(destination_font, component_source, new_component, skipped)
        copy_stems(component_source, new_component)
        axis_id_map = copy_smart_component_axes(component_source, new_component)
        smart_axis_maps[component_name] = axis_id_map
        destination_font.glyphs.append(new_component)
        copy_glyph_layers(
            source_font,
            destination_font,
            component_source,
            new_component,
            component_name_map,
            smart_axis_maps,
            axis_id_map,
        )
        copied["components"] += 1
        print("  Copied component glyph: %s" % destination_component_name)


def copy_source_glyph(
    source_font,
    destination_font,
    target_name,
    source_name,
    unicode_value,
    copied,
    skipped,
    component_name_map,
    smart_axis_maps,
    created_glyph_names,
    is_stylistic_set=False,
    overwrite_existing=False,
):
    source_glyph = source_font.glyphs[source_name]
    if source_glyph is None:
        skipped["missing_source"] += 1
        if unicode_value:
            print("Missing source glyph: %s for %s U+%s" % (source_name, target_name, unicode_value))
        else:
            print("Missing source glyph: %s for %s" % (source_name, target_name))
        return

    existing_target_glyph = destination_font.glyphs[target_name]
    if existing_target_glyph is not None and not overwrite_existing:
        skipped["target_exists"] += 1
        print("Skipped existing destination glyph: %s" % target_name)
        return

    if unicode_value:
        existing_unicode_glyph = glyph_for_unicode(destination_font, unicode_value)
        if existing_unicode_glyph is not None and existing_unicode_glyph.name != target_name:
            skipped["unicode_exists"] += 1
            print("Skipped %s, U+%s already exists as %s" % (target_name, unicode_value, existing_unicode_glyph.name))
            return

    copy_missing_component_glyphs(
        source_font,
        destination_font,
        source_glyph,
        copied,
        skipped,
        component_name_map,
        smart_axis_maps,
        created_glyph_names,
    )

    if existing_target_glyph is not None:
        target_glyph = existing_target_glyph
        removed_layers = clear_glyph_for_overwrite(target_glyph)
        copied["overwritten"] += 1
        print("Overwriting existing destination glyph: %s (%i old special layer(s) removed)" % (
            target_name,
            removed_layers,
        ))
    else:
        target_glyph = GSGlyph(target_name)
        destination_font.glyphs.append(target_glyph)

    if unicode_value:
        target_glyph.unicode = unicode_value
    copy_stems(source_glyph, target_glyph)
    axis_id_map = copy_smart_component_axes(source_glyph, target_glyph)
    smart_axis_maps[source_name] = axis_id_map
    copy_glyph_layers(
        source_font,
        destination_font,
        source_glyph,
        target_glyph,
        component_name_map,
        smart_axis_maps,
        axis_id_map,
    )
    warn_unrepointed_components(target_glyph, component_name_map)
    if is_stylistic_set:
        copied["stylistic_sets"] += 1
    else:
        copied["math"] += 1
    append_created_name(created_glyph_names, target_name)
    if unicode_value:
        print("Copied %s -> %s U+%s" % (source_name, target_name, unicode_value))
    else:
        print("Copied %s -> %s" % (source_name, target_name))


def copy_math_glyph(
    source_font,
    destination_font,
    unicode_value,
    target_name,
    source_name,
    copied,
    skipped,
    component_name_map,
    smart_axis_maps,
    created_glyph_names,
    overwrite_existing=False,
):
    copy_source_glyph(
        source_font,
        destination_font,
        target_name,
        source_name,
        unicode_value,
        copied,
        skipped,
        component_name_map,
        smart_axis_maps,
        created_glyph_names,
        overwrite_existing=overwrite_existing,
    )

    for alternate_source_name in stylistic_set_source_names(source_font, source_name):
        suffix_match = STYLISTIC_SET_SUFFIX_RE.search(alternate_source_name)
        if suffix_match is None:
            continue

        alternate_target_name = target_name + suffix_match.group(0)
        print("  Stylistic set alternate: %s -> %s" % (alternate_source_name, alternate_target_name))
        copy_source_glyph(
            source_font,
            destination_font,
            alternate_target_name,
            alternate_source_name,
            None,
            copied,
            skipped,
            component_name_map,
            smart_axis_maps,
            created_glyph_names,
            is_stylistic_set=True,
            overwrite_existing=overwrite_existing,
        )


class MathItalicGlyphCopier(object):
    def __init__(self):
        Glyphs.clearLog()
        Glyphs.showMacroWindow()
        print("Copy Math Italic Glyphs From Source")
        print("Choose source and destination fonts, then click the copy button.")
        print("")

        self.fonts = list(Glyphs.fonts)
        self.labels = [font_label(font) for font in self.fonts]
        destination_font = Glyphs.font
        destination_index = font_index(self.fonts, destination_font)
        source_index = guessed_source_index(self.fonts, destination_font)

        self.w = vanilla.FloatingWindow((420, 202), "Copy Math Italic Glyphs")
        self.w.sourceLabel = vanilla.TextBox((15, 18, 90, 20), "Source")
        self.w.source = vanilla.PopUpButton((110, 15, -15, 24), self.labels)
        self.w.destinationLabel = vanilla.TextBox((15, 53, 90, 20), "Destination")
        self.w.destination = vanilla.PopUpButton((110, 50, -15, 24), self.labels)
        self.w.overwrite = vanilla.CheckBox((110, 82, -15, 22), "Overwrite existing destination glyphs", value=False)
        self.w.openTab = vanilla.CheckBox((110, 108, -15, 22), "Open tab with imported glyphs", value=False)
        self.w.copyButton = vanilla.Button((15, 155, -15, 30), "Copy math italic glyphs", callback=self.copy_callback)

        self.w.source.set(source_index)
        self.w.destination.set(destination_index)

        self.w.open()

    def copy_callback(self, sender):
        Glyphs.clearLog()
        Glyphs.showMacroWindow()
        print("copying glyphs...")
        print("Copy button pressed. Starting math italic glyph copy.")
        print("")

        if len(self.fonts) < 2:
            print("Open at least two fonts: one source and one destination.")
            return

        source_index = self.w.source.get()
        destination_index = self.w.destination.get()
        overwrite_existing = bool(self.w.overwrite.get())
        open_tab = bool(self.w.openTab.get())
        self.w.close()

        source_font = self.fonts[source_index]
        destination_font = self.fonts[destination_index]

        if source_font is destination_font:
            print("Source and destination are the same font. Choose two different fonts.")
            return

        print("Source: %s" % font_label(source_font))
        print("Destination: %s" % font_label(destination_font))
        print("Overwrite existing destination glyphs: %s" % ("yes" if overwrite_existing else "no"))
        print("Open tab with imported glyphs: %s" % ("yes" if open_tab else "no"))
        print("")

        copied = {"math": 0, "stylistic_sets": 0, "components": 0, "renamed_components": 0, "overwritten": 0}
        component_name_map = {}
        smart_axis_maps = {}
        created_glyph_names = []
        skipped = {
            "missing_source": 0,
            "target_exists": 0,
            "unicode_exists": 0,
            "missing_components": 0,
            "component_unicode_exists": 0,
        }
        targets = target_map()
        target_count = len(targets)
        print("Preparing to copy %i math glyphs." % target_count)
        print("Will also copy matching source .ssNN alternates as target .ssNN glyphs.")
        print("")

        destination_font.disableUpdateInterface()
        try:
            for index, (unicode_value, target_name, source_name) in enumerate(targets, 1):
                print("[%i/%i] %s -> %s U+%s" % (index, target_count, source_name, target_name, unicode_value))
                copy_math_glyph(
                    source_font,
                    destination_font,
                    unicode_value,
                    target_name,
                    source_name,
                    copied,
                    skipped,
                    component_name_map,
                    smart_axis_maps,
                    created_glyph_names,
                    overwrite_existing,
                )
        finally:
            destination_font.enableUpdateInterface()

        if open_tab:
            open_destination_tab(destination_font, created_glyph_names)

        print("")
        print("Done.")
        print("Math glyphs copied: %i" % copied["math"])
        print("Stylistic-set glyphs copied: %i" % copied["stylistic_sets"])
        print("Component glyphs copied: %i" % copied["components"])
        print("Components renamed to avoid destination glyphs: %i" % copied["renamed_components"])
        print("Existing destination glyphs overwritten: %i" % copied["overwritten"])
        print("Skipped existing target glyphs: %i" % skipped["target_exists"])
        print("Skipped existing target unicodes: %i" % skipped["unicode_exists"])
        print("Missing source glyphs: %i" % skipped["missing_source"])
        print("Missing source component glyphs: %i" % skipped["missing_components"])
        print("Skipped component unicodes already present: %i" % skipped["component_unicode_exists"])


MathItalicGlyphCopier()
