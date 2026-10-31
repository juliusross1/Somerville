# MenuTitle: adjust math spacing
# -*- coding: utf-8 -*-
"""Move anchors and adjust Somerville sidebearings on the current glyph.

The selection is resolved by name in the document font, so an interpolated
preview never becomes an edit target. Anchor arrows move anchors on every layer.
Sidebearing grids address the eight
Agate/Needlepoint, SemiLight/Black, SemiCondensed/SemiExpanded masters by axis
coordinates, independent of axis order or master names. Cell, row and column
buttons change the chosen bearing by 10 font units on those masters and every
associated intermediate, alternate, smart-component or backup layer. Backgrounds
are not separate entries in glyph.layers. Existing metrics keys are preserved.
Inherited component bearings are edited on their source glyphs instead; shared
component layers are changed only once per click. Undo belongs to edited glyphs.
"""

import math
import os
import runpy
import traceback

import vanilla
from AppKit import (
    NSAffineTransform, NSBezierPath, NSBitmapImageRep, NSColor,
    NSDeviceRGBColorSpace, NSGraphicsContext, NSImage, NSMakeRect, NSMakeSize,
)
from Foundation import NSMakePoint
from GlyphsApp import Glyphs, UPDATEINTERFACE


ANCHOR_ORDER = ("math.ta", "math.tl", "math.tr", "math.bl", "math.br")
STEP = 10
OPTICAL_SIZES = (("Agate", 5), ("Needlepoint", 1200))
WEIGHTS = (("SemiLight", 360), ("Black", 900))
WIDTHS = (("SemiCondensed", 95), ("SemiExpanded", 113))


def corner_anchor_script_path():
    """Find the shared dialog when Glyphs runs menu scripts without __file__."""
    directories = []
    filename = globals().get("__file__")
    if filename:
        directories.append(os.path.dirname(os.path.realpath(filename)))
    for version in ("4", "3"):
        directories.append(os.path.expanduser(
            "~/Library/Application Support/Glyphs %s/Scripts/Somerville Scripts" % version
        ))
    for directory in directories:
        path = os.path.realpath(os.path.join(
            directory, "setup", "add_missing_math_corner_anchors.py"
        ))
        if os.path.isfile(path):
            return path
    raise FileNotFoundError(
        "Cannot find setup/add_missing_math_corner_anchors.py beside this script "
        "or in the installed Somerville Scripts folder."
    )


def master_grid(font):
    """Map grid cells to master IDs, using source (not exported user) axes."""
    cells = {
        (optical, weight, width): set()
        for optical, _ in OPTICAL_SIZES
        for weight, _ in WEIGHTS
        for width, _ in WIDTHS
    }
    if font is None:
        return cells
    axes = {axis.axisTag: index for index, axis in enumerate(font.axes)}
    if not all(tag in axes for tag in ("opsz", "wght", "wdth")):
        return cells
    for master in font.masters:
        for optical, optical_value in OPTICAL_SIZES:
            for weight, weight_value in WEIGHTS:
                for width, width_value in WIDTHS:
                    if all(abs(float(master.axes[axes[tag]]) - value) < .01
                           for tag, value in (("opsz", optical_value),
                                              ("wght", weight_value),
                                              ("wdth", width_value))):
                        cells[(optical, weight, width)].add(master.id)
    return cells


def associated_layers(glyph, master_ids):
    """Include each matching layer once, even in row/column operations."""
    return [layer for layer in glyph.layers
            if layer.layerId in master_ids or layer.associatedMasterId in master_ids]


def preview_layer(font, glyph):
    """Use the first available master layer; fall back to another glyph layer."""
    if font is None or glyph is None:
        return None
    layers = {layer.layerId: layer for layer in glyph.layers}
    for master in font.masters:
        if master.id in layers:
            return layers[master.id]
    return next(iter(glyph.layers), None)


def preview_image(layer, width=305, height=160):
    """Render the actual outline, including components, fitted to the box."""
    if layer is None:
        return None
    path = None
    open_path = False
    for attribute in ("completeBezierPath", "bezierPath", "completeOpenBezierPath"):
        candidate = getattr(layer, attribute, None)
        if callable(candidate):
            candidate = candidate()
        if candidate is not None and not candidate.isEmpty():
            path = candidate.copy()
            open_path = attribute == "completeOpenBezierPath"
            break
    if path is None:
        return None
    bounds = path.bounds()
    outline_width, outline_height = bounds.size.width, bounds.size.height
    if not all(math.isfinite(value) for value in (
            bounds.origin.x, bounds.origin.y, outline_width, outline_height)):
        return None
    if outline_width <= 0 and outline_height <= 0:
        return None
    margin = 14
    scale = min((width - 2 * margin) / max(outline_width, 1),
                (height - 2 * margin) / max(outline_height, 1))
    transform = NSAffineTransform.transform()
    transform.translateXBy_yBy_((width - outline_width * scale) / 2,
                               (height - outline_height * scale) / 2)
    transform.scaleXBy_yBy_(scale, scale)
    transform.translateXBy_yBy_(-bounds.origin.x, -bounds.origin.y)
    path.transformUsingAffineTransform_(transform)
    bitmap = NSBitmapImageRep.alloc().initWithBitmapDataPlanes_pixelsWide_pixelsHigh_bitsPerSample_samplesPerPixel_hasAlpha_isPlanar_colorSpaceName_bytesPerRow_bitsPerPixel_(
        None, width, height, 8, 4, True, False, NSDeviceRGBColorSpace, 0, 0
    )
    context = NSGraphicsContext.graphicsContextWithBitmapImageRep_(bitmap)
    NSGraphicsContext.saveGraphicsState()
    try:
        NSGraphicsContext.setCurrentContext_(context)
        rect = NSMakeRect(0, 0, width, height)
        NSColor.whiteColor().set()
        NSBezierPath.fillRect_(rect)
        NSColor.lightGrayColor().set()
        NSBezierPath.strokeRect_(rect)
        NSColor.blackColor().set()
        if open_path:
            path.setLineWidth_(1)
            path.stroke()
        else:
            path.fill()
    finally:
        NSGraphicsContext.restoreGraphicsState()
    image = NSImage.alloc().initWithSize_(NSMakeSize(width, height))
    image.addRepresentation_(bitmap)
    return image


def sidebearing_updates(layers, bearing, delta):
    """Snapshot both bearings before editing any master or dependent layer."""
    updates = []
    for layer in layers:
        lsb, rsb = float(layer.LSB), float(layer.RSB)
        if not math.isfinite(lsb) or not math.isfinite(rsb):
            raise ValueError("Cannot measure sidebearings on layer %s" % layer.name)
        updates.append((layer, lsb + (delta if bearing == "LSB" else 0),
                        rsb + (delta if bearing == "RSB" else 0)))
    # Edit master layers first; set dependent layers to their own saved targets.
    return sorted(updates, key=lambda item: not item[0].isMasterLayer)


def api_value(obj, name, default=None):
    value = getattr(obj, name, default)
    return value() if callable(value) else value


def refresh_spacing_metrics(layers):
    """Finish source alignment before measuring a dependent composite layer."""
    seen = set()

    def refresh_layer(layer):
        key = (layer.parent.name, layer.layerId)
        if key in seen:
            return
        seen.add(key)
        components = list(getattr(layer, "components", ()))
        for component in components:
            source = api_value(component, "component")
            if source is None:
                continue
            master_id = api_value(component, "componentMasterId") or layer.associatedMasterId
            for source_layer in source.layers:
                if source_layer.layerId == master_id:
                    refresh_layer(source_layer)
                    break
        if components:
            # setNeedsAlignment alone defers this until drawing. That is too
            # late for the before/after checks in a button's callback.
            layer.setNeedsAlignment()
            immediate = getattr(layer, "doAlignComponents", None)
            if not callable(immediate):
                raise ValueError("Immediate component alignment is unavailable for %s/%s."
                                 % (layer.parent.name, layer.name))
            immediate()
        update = getattr(layer, "updateMetrics", None)
        if callable(update):
            update()

    for layer in layers:
        refresh_layer(layer)


def component_source_layer(component, layer):
    source_layer = api_value(component, "componentLayer")
    if source_layer is None:
        source = api_value(component, "component")
        master_id = api_value(component, "componentMasterId") or layer.associatedMasterId
        if source is not None:
            source_layer = next((item for item in source.layers if item.layerId == master_id), None)
    return source_layer


def component_anchor_map(component, layer):
    source_layer = component_source_layer(component, layer)
    return {anchor.name: anchor for anchor in getattr(source_layer, "anchors", ())}


def component_is_attachment(component, layer):
    """Distinguish ordinary _anchor attachment from an entry/exit chain."""
    anchors = component_anchor_map(component, layer)
    anchor = api_value(component, "anchor")
    if anchor and "_" + anchor in anchors:
        return True
    # Glyphs can report doesAttach for the entry/exit-connected spacing bases
    # as well. It is not by itself evidence that a component is a mark.
    cursive = any(name in anchors for name in ("#entry", "#exit", "entry", "exit"))
    if cursive:
        return False
    return bool(api_value(component, "doesAttach", False))


def components_join(previous, component, layer):
    previous_anchors = component_anchor_map(previous, layer)
    anchors = component_anchor_map(component, layer)
    # Resolve the connection by its named anchors, not cached positions, which
    # can still reflect the preceding edit or an unaligned saved layer.
    return any(exit_name in previous_anchors and entry_name in anchors
               for exit_name, entry_name in (("#exit", "#entry"), ("exit", "entry")))


def inherited_component(layer, bearing):
    """Find the aligned base supplying this bearing, excluding attached marks."""
    inherited = api_value(layer, "hasAlignedSideBearings")
    if inherited is None:
        inherited = api_value(layer, "hasAlignedWidth", False) and api_value(layer, "isAligned", False)
    if not inherited:
        return None
    bases = []
    for index, component in enumerate(layer.components):
        if component_is_attachment(component, layer):
            continue
        anchors = component_anchor_map(component, layer)
        starts_chain = (index == 0 and any(name in anchors for name in ("#exit", "exit"))
                        and api_value(component, "alignment", 0) != -1)
        joins_chain = bool(bases) and components_join(bases[-1], component, layer)
        if api_value(component, "doesAlign", False) or starts_chain or joins_chain:
            bases.append(component)
    if not bases:
        details = "; ".join("%s: doesAlign=%s, doesAttach=%s, anchor=%r, anchors=%r" % (
            component.componentName, api_value(component, "doesAlign"),
            api_value(component, "doesAttach"), api_value(component, "anchor"),
            sorted(component_anchor_map(component, layer))) for component in layer.components)
        raise ValueError("%s/%s inherits spacing but no spacing base was resolved. %s"
                         % (layer.parent.name, layer.name, details))
    return bases[0] if bearing == "LSB" else bases[-1]


def sidebearing_plan(glyph, master_ids, bearing, delta):
    """Resolve inherited spacing to real source layers before changing anything."""
    targets = {}
    routes = set()
    roots = associated_layers(glyph, master_ids)

    def resolve(layer, chain):
        owner = layer.parent
        key = (owner.name, layer.layerId)
        if key in chain:
            raise ValueError("Component spacing cycle at %s/%s." % (owner.name, layer.name))
        component = inherited_component(layer, bearing)
        if component is None:
            if key not in targets:
                targets[key] = (layer, owner)
            return
        source = api_value(component, "component")
        if source is None:
            raise ValueError("Missing component %s in %s/%s."
                             % (component.componentName, owner.name, layer.name))
        transform = api_value(component, "transform", (1, 0, 0, 1, 0, 0))
        try:
            linear = tuple(transform)[:4]
        except TypeError:
            linear = (transform.m11, transform.m12, transform.m21, transform.m22)
        if any(abs(float(actual) - expected) > .000001
               for actual, expected in zip(linear, (1, 0, 0, 1))):
            raise ValueError("Cannot route a 10-unit spacing edit through scaled/rotated component %s."
                             % source.name)
        source_master = api_value(component, "componentMasterId") or layer.associatedMasterId
        source_layers = associated_layers(source, {source_master})
        if not any(item.layerId == source_master for item in source_layers):
            raise ValueError("No source master %s on component %s." % (source_master, source.name))
        routes.add((owner.name, source.name, source_master))
        for source_layer in source_layers:
            resolve(source_layer, chain + (key,))

    for layer in roots:
        resolve(layer, ())
    # Snapshot all targets before a component edit can alter a dependent layer.
    updates = sidebearing_updates([layer for layer, owner in targets.values()], bearing, delta)
    # Sources precede their dependants, including mixed path/component backups.
    # Otherwise a later source edit could change a direct layer already spaced.
    owners = {owner.name: owner for layer, owner in targets.values()}
    order = []
    visiting = set()

    def order_owner(name):
        if name in order:
            return
        if name in visiting:
            raise ValueError("Component dependency cycle at %s." % name)
        visiting.add(name)
        for layer, owner in targets.values():
            if owner.name == name:
                for component in getattr(layer, "components", ()):
                    if component.componentName in owners:
                        order_owner(component.componentName)
        visiting.remove(name)
        order.append(name)

    for name in owners:
        order_owner(name)
    rank = {name: index for index, name in enumerate(order)}
    updates.sort(key=lambda item: (rank[item[0].parent.name], not item[0].isMasterLayer))
    return updates, routes, roots


def bearing_diagnostics(layer, target_lsb, target_rsb, before):
    owner = layer.parent
    components = ["%s (aligns=%s, attached=%s, anchor=%r, alignment=%s, effective=%s)" % (
        component.componentName, api_value(component, "doesAlign", False),
        component_is_attachment(component, layer), api_value(component, "anchor"),
        api_value(component, "alignment"), api_value(component, "effectiveAlignment"))
        for component in getattr(layer, "components", ())]
    return ("  %s / %s [%s]\n"
            "    before LSB=%g RSB=%g; target LSB=%g RSB=%g; actual LSB=%g RSB=%g\n"
            "    inherited=%s; glyph keys=%r/%r/%r; layer keys=%r/%r/%r\n"
            "    components: %s" % (
                owner.name, layer.name, layer.layerId, before[0], before[1],
                target_lsb, target_rsb, layer.LSB, layer.RSB,
                api_value(layer, "hasAlignedSideBearings"),
                getattr(owner, "leftMetricsKey", None), getattr(owner, "rightMetricsKey", None),
                getattr(owner, "widthMetricsKey", None), getattr(layer, "leftMetricsKey", None),
                getattr(layer, "rightMetricsKey", None), getattr(layer, "widthMetricsKey", None),
                ", ".join(components) or "none"))


def spacing_target_labels(glyph, master_ids):
    """Describe the same resolved edit targets used by the bearing buttons."""
    labels = {}
    shared = False
    for bearing in ("LSB", "RSB"):
        if glyph is None or not master_ids:
            labels[bearing] = "%s: no spacing targets" % bearing
            continue
        try:
            updates, routes, roots = sidebearing_plan(glyph, master_ids, bearing, 0)
            names = {layer.parent.name for layer, lsb, rsb in updates}
            components = sorted(names - {glyph.name})
            if components:
                shared = True
                text = "%s edits COMPONENTS: %s" % (bearing, ", ".join(components))
                if glyph.name in names:
                    text += "; also %s's own layers" % glyph.name
            elif names:
                text = "%s edits this glyph: %s" % (bearing, glyph.name)
            else:
                text = "%s: no spacing targets" % bearing
            labels[bearing] = text
        except Exception as error:
            labels[bearing] = "%s: cannot resolve targets (%s)" % (bearing, error)
    return labels, shared


def sidebearing_result(layer, bearing, before, requested_delta, role):
    old = before[0 if bearing == "LSB" else 1]
    actual = float(getattr(layer, bearing))
    change = actual - old
    message = ("  RESULT [%s] %s / %s [%s]: %s %g -> %g "
               "(change %+g; requested %+g)" % (
                   role, layer.parent.name, layer.name, layer.layerId,
                   bearing, old, actual, change, requested_delta))
    return message, change


def spacing_preview_targets(glyph, master_ids):
    """Return actual edited glyphs, their bearings, and representative layers."""
    targets = {}
    errors = []
    if glyph is not None and master_ids:
        for bearing in ("LSB", "RSB"):
            try:
                updates, _, _ = sidebearing_plan(glyph, master_ids, bearing, 0)
                for layer, _, _ in updates:
                    name = layer.parent.name
                    if name not in targets:
                        targets[name] = [layer, set()]
                    elif layer.isMasterLayer and not targets[name][0].isMasterLayer:
                        targets[name][0] = layer
                    targets[name][1].add(bearing)
            except Exception as error:
                errors.append("%s: %s" % (bearing, error))
    return [(name, targets[name][0], tuple(sorted(targets[name][1])))
            for name in sorted(targets)], errors


def component_users(font):
    """Index direct component users across all stored layers, including backups."""
    users = {}
    if font is not None:
        try:
            glyphs = list(font.glyphs)
        except AttributeError:
            # Some Glyphs wrappers call a missing native `glyphs` selector.
            # Bypass the collection proxy, including its broken len/index path.
            count = font.countOfGlyphs()
            glyphs = [font.glyphAtIndex_(index) for index in range(count)]
        for glyph in glyphs:
            for layer in glyph.layers:
                for component in layer.components:
                    users.setdefault(component.componentName, set()).add(glyph.name)
    return users


def all_component_users(users, name):
    """Include nested component users; never loop on a component cycle."""
    found = {name}
    pending = [name]
    while pending:
        for user in users.get(pending.pop(), ()):
            if user not in found:
                found.add(user)
                pending.append(user)
    return sorted(found - {name})


class AnchorMover:
    def __init__(self):
        self.signature = None
        self.actions = {}
        self.bearing_actions = {}
        self.cell_labels = {}
        self.cells = {}
        self.busy = False
        self.preview_signature = None
        self.users_selection = None
        self.users_index = {}
        self.users_error = None
        self.corner_anchor_dialog = None
        self.w = vanilla.FloatingWindow((800, 666), "adjust math spacing")
        self.w.glyphName = vanilla.TextBox((12, 12, 305, 20), "")
        self.w.previewTitle = vanilla.TextBox((12, 36, 305, 18), "Spacing sources across both grids", sizeStyle="small")
        self.w.usersTitle = vanilla.TextBox((12, 304, 224, 18), "Glyphs using these sources (incl. nested)", sizeStyle="small")
        self.w.refreshUsers = vanilla.Button((244, 300, 73, 22), "Refresh", sizeStyle="small", callback=self.refresh_users)
        self.w.hint = vanilla.TextBox(
            (176, 432, 141, 20), "Move 10 units; all layers.", sizeStyle="small"
        )
        self.w.insertCorners = vanilla.Button(
            (12, 430, 154, 22), "Add Corner Anchors…", sizeStyle="small",
            callback=self.open_corner_anchor_dialog,
        )
        self.w.bearingTitle = vanilla.TextBox((336, 12, -12, 20), "Sidebearings: 10 font units per click")
        self.w.bearingHint = vanilla.TextBox(
            (336, 36, -12, 26), "Includes associated layers; inherited bearings edit components.", sizeStyle="small"
        )
        for index, (optical, _) in enumerate(OPTICAL_SIZES):
            self.make_grid(optical, index)
        self.w.status = vanilla.TextBox((12, -42, -12, 32), "", sizeStyle="small")
        self.w.bind("close", self.close)
        self.refresh()
        Glyphs.addCallback(self.refresh, UPDATEINTERFACE)
        self.w.open()

    def make_grid(self, optical, index):
        group = vanilla.Group((336, 66 + index * 276, 444, 262))
        group.title = vanilla.TextBox((0, 0, -1, 20), optical)
        for column, (width, _) in enumerate(WIDTHS):
            x = 146 + column * 146
            setattr(group, "columnLabel%d" % column,
                    vanilla.TextBox((x, 26, 140, 18), width, sizeStyle="small"))
            keys = tuple((optical, weight, width) for weight, _ in WEIGHTS)
            self.add_bearing_buttons(group, "column%d" % column, x, 48, keys)
        for row, (weight, _) in enumerate(WEIGHTS):
            y = 110 + row * 78
            setattr(group, "rowLabel%d" % row,
                    vanilla.TextBox((0, y, 135, 18), weight, sizeStyle="small"))
            keys = tuple((optical, weight, width) for width, _ in WIDTHS)
            self.add_bearing_buttons(group, "row%d" % row, 0, y + 20, keys)
            for column, (width, _) in enumerate(WIDTHS):
                x = 146 + column * 146
                key = (optical, weight, width)
                label = vanilla.TextBox((x, y, 140, 18), "", sizeStyle="small")
                setattr(group, "cellLabel%d%d" % (row, column), label)
                self.cell_labels[key] = label
                self.add_bearing_buttons(group, "cell%d%d" % (row, column), x, y + 20, (key,))
        setattr(self.w, "grid%d" % index, group)

    def add_bearing_buttons(self, group, prefix, x, y, keys):
        for bearing_column, bearing in enumerate(("LSB", "RSB")):
            bearing_x = x + bearing_column * 70
            setattr(group, prefix + bearing + "Label", vanilla.TextBox(
                (bearing_x, y, 61, 18), bearing, sizeStyle="small", alignment="center"
            ))
            for column, (label, delta) in enumerate((("−", -STEP), ("+", STEP))):
                button = vanilla.Button(
                    (bearing_x + column * 32, y + 22, 29, 22),
                    label, callback=self.adjust_sidebearing,
                )
                setattr(group, prefix + bearing + str(column), button)
                self.bearing_actions[id(button)] = (button, keys, bearing, delta)

    def selection(self):
        font = Glyphs.font
        if font is None or not font.selectedLayers:
            return None, None
        displayed_glyph = font.selectedLayers[0].parent
        if displayed_glyph is None:
            return font, None
        # An axis-preview layer belongs to a temporary interpolated glyph.
        # Always edit the stored glyph and its real master/special layers.
        return font, font.glyphForName_(displayed_glyph.name)

    def refresh(self, sender=None):
        if self.busy:
            return
        font, glyph = self.selection()
        self.w.glyphName.set(glyph.name if glyph is not None else "Select a glyph.")
        self.w.insertCorners.enable(glyph is not None)
        names = {
            anchor.name
            for layer in glyph.layers
            for anchor in layer.anchors
        } if glyph is not None else set()
        ordered = [name for name in ANCHOR_ORDER if name in names]
        cells = master_grid(font)
        grid_signature = tuple(sorted((key, tuple(sorted(ids))) for key, ids in cells.items()))
        layers_signature = tuple((layer.layerId, layer.associatedMasterId) for layer in glyph.layers) if glyph else ()
        signature = (font, glyph, tuple(ordered), grid_signature, layers_signature)
        self.cells = cells
        self.refresh_sidebearings(font, glyph)
        if signature == self.signature:
            return
        self.signature = signature
        self.actions = {}
        if hasattr(self.w, "anchors"):
            del self.w.anchors
        rows = vanilla.Group((0, 0, 285, 154))
        # Keep the corner positions fixed even when an anchor is missing.
        positions = ((72, 0), (0, 50), (144, 50), (0, 104), (144, 104))
        for index, (name, (x, y)) in enumerate(zip(ANCHOR_ORDER, positions)):
            setattr(rows, "label%d" % index, vanilla.TextBox(
                (x, y, 136, 18), name, alignment="center", sizeStyle="small"
            ))
            for direction, label, offset, delta in (
                ("left", "←", 22, -STEP),
                ("right", "→", 74, STEP),
            ):
                button = vanilla.Button((x + offset, y + 20, 40, 24), label, callback=self.move)
                button.enable(name in names)
                setattr(rows, "%s%d" % (direction, index), button)
                if name in names:
                    self.actions[id(button)] = (name, delta)
        self.anchor_group = rows
        self.w.anchors = vanilla.ScrollView(
            (12, 456, 305, -54), rows.getNSView(), hasHorizontalScroller=False
        )

    def refresh_sidebearings(self, font, glyph):
        master_ids = set().union(*self.cells.values())
        self.refresh_previews(font, glyph, master_ids)
        for key, label in self.cell_labels.items():
            masters = [layer for layer in glyph.layers if layer.layerId in self.cells[key]] if glyph else []
            if not masters:
                label.set("No matching master layer")
            elif len(masters) == 1:
                label.set("L %g   R %g" % (masters[0].LSB, masters[0].RSB))
            else:
                label.set("%i master layers" % len(masters))
        present = {layer.layerId for layer in glyph.layers} if glyph else set()
        for button, keys, bearing, delta in self.bearing_actions.values():
            ids = set().union(*(self.cells[key] for key in keys))
            button.enable(bool(ids & present))

    def refresh_users(self, sender=None):
        self.users_selection = None
        self.preview_signature = None
        self.refresh()

    def refresh_previews(self, font, glyph, master_ids):
        targets, errors = spacing_preview_targets(glyph, master_ids)
        selection = (font, glyph, tuple(name for name, _, _ in targets))
        if selection != self.users_selection:
            self.users_error = None
            try:
                self.users_index = component_users(font)
            except Exception as error:
                self.users_index = {}
                self.users_error = "Component users unavailable: %s" % error
                traceback.print_exc()
            self.users_selection = selection
        if self.users_error:
            errors.append(self.users_error)
        signature = (selection, tuple((name, layer.layerId, bearings)
                                     for name, layer, bearings in targets), tuple(errors))
        if signature != self.preview_signature:
            self.preview_signature = signature
            for attribute in ("sourcePreviews", "sourceUsers"):
                if hasattr(self.w, attribute):
                    delattr(self.w, attribute)
            rows = vanilla.Group((0, 0, 285, max(40, len(targets) * 164 + len(errors) * 48)))
            self.preview_controls = []
            for index, (name, layer, bearings) in enumerate(targets):
                y = index * 164
                label = vanilla.TextBox((2, y, 281, 18), "%s: %s" % (" / ".join(bearings), name), sizeStyle="small")
                label.getNSTextField().setToolTip_(name)
                setattr(rows, "name%d" % index, label)
                image = vanilla.ImageView((2, y + 20, 279, 118))
                setattr(rows, "image%d" % index, image)
                caption = vanilla.TextBox((2, y + 140, 281, 20), layer.name, sizeStyle="small")
                setattr(rows, "caption%d" % index, caption)
                self.preview_controls.append((image, caption))
            for index, error in enumerate(errors):
                control = vanilla.TextBox((2, len(targets) * 164 + index * 48, 281, 46), error, sizeStyle="small")
                control.getNSTextField().setToolTip_(error)
                setattr(rows, "error%d" % index, control)
            if not targets and not errors:
                rows.empty = vanilla.TextBox((2, 4, 281, 32), "No spacing sources. Select a glyph.", sizeStyle="small")
            self.preview_group = rows
            self.w.sourcePreviews = vanilla.ScrollView((12, 58, 305, 238), rows.getNSView(), hasHorizontalScroller=False)
            user_rows = vanilla.Group((0, 0, 285, 40))
            y = 0
            for index, (name, _, bearings) in enumerate(targets):
                label = vanilla.TextBox((2, y, 281, 18), "%s: %s" % (" / ".join(bearings), name), sizeStyle="small")
                label.getNSTextField().setToolTip_(name)
                setattr(user_rows, "source%d" % index, label)
                y += 20
                names = (["(Component lookup unavailable)"] if self.users_error
                         else all_component_users(self.users_index, name))
                for number, user in enumerate(names or ["(No component users)"]):
                    control = vanilla.TextBox((10, y, 273, 16), user, sizeStyle="small")
                    control.getNSTextField().setToolTip_(user)
                    setattr(user_rows, "user%d_%d" % (index, number), control)
                    y += 17
                y += 8
            user_rows.setPosSize((0, 0, 285, max(40, y)))
            self.users_group = user_rows
            self.w.sourceUsers = vanilla.ScrollView((12, 328, 305, 94), user_rows.getNSView(), hasHorizontalScroller=False)
        # Re-render after edits even when the target list has not changed.
        for (name, layer, bearings), (control, caption) in zip(targets, self.preview_controls):
            try:
                image = preview_image(layer, 279, 118)
                text = layer.name + (" (no outline)" if image is None else "")
            except Exception:
                image = None
                text = "Preview unavailable; see Macro Window."
                if getattr(self, "preview_error_layer", None) is not layer:
                    traceback.print_exc()
                self.preview_error_layer = layer
            control.getNSImageView().setImage_(image)
            caption.set(text)

    def checked_selection(self):
        previous = self.signature
        self.refresh()
        if previous != self.signature:
            self.w.status.set("Selection or masters changed. Click again to apply to the displayed glyph.")
            return None, None
        return self.selection()

    def move(self, sender):
        action = self.actions.get(id(sender))
        font, glyph = self.checked_selection()
        if action is None or glyph is None:
            return
        name, delta = action
        self.busy = True
        font.disableUpdateInterface()
        try:
            glyph.beginUndo()
            try:
                for layer in glyph.layers:
                    anchor = layer.anchors[name]
                    if anchor is not None:
                        anchor.position = NSMakePoint(
                            anchor.position.x + delta, anchor.position.y
                        )
            finally:
                glyph.endUndo()
        except Exception:
            Glyphs.showMacroWindow()
            traceback.print_exc()
        finally:
            font.enableUpdateInterface()
            self.busy = False
            self.refresh()
            Glyphs.redraw()

    def adjust_sidebearing(self, sender):
        action = self.bearing_actions.get(id(sender))
        font, glyph = self.checked_selection()
        if action is None or glyph is None:
            return
        button, keys, bearing, delta = action
        master_ids = set().union(*(self.cells[key] for key in keys))
        try:
            refresh_spacing_metrics(associated_layers(glyph, master_ids))
            updates, routes, roots = sidebearing_plan(glyph, master_ids, bearing, delta)
            before = {(layer.parent.name, layer.layerId): (float(layer.LSB), float(layer.RSB))
                      for layer, lsb, rsb in updates}
            root_before = {(layer.parent.name, layer.layerId): (float(layer.LSB), float(layer.RSB))
                           for layer in roots}
        except Exception:
            Glyphs.showMacroWindow()
            traceback.print_exc()
            self.w.status.set("Cannot resolve spacing sources; nothing changed. See Macro Window.")
            return
        if not updates:
            self.w.status.set("No layers for these masters in the current glyph.")
            return
        error = None
        edited_glyphs = []
        for layer, lsb, rsb in updates:
            if not any(owner is layer.parent for owner in edited_glyphs):
                edited_glyphs.append(layer.parent)
        print("%s: %s %+g; editing %s (%i layers)." % (
            glyph.name, bearing, delta, ", ".join(owner.name for owner in edited_glyphs), len(updates)))
        for owner_name, source_name, source_master in sorted(routes):
            print("  inherited %s: %s -> %s [master %s]"
                  % (bearing, owner_name, source_name, source_master))
        self.busy = True
        font.disableUpdateInterface()
        undo_open = []
        try:
            try:
                for owner in edited_glyphs:
                    owner.beginUndo()
                    undo_open.append(owner)
                for layer, lsb, rsb in updates:
                    # Do not reset the LSB during an RSB-only edit. With component
                    # dependencies, even a redundant setter can re-align a layer.
                    if bearing == "LSB" or abs(layer.LSB - lsb) > .01:
                        layer.LSB = lsb
                    layer.RSB = rsb
                refresh_spacing_metrics([layer for layer, lsb, rsb in updates] + roots)
            finally:
                for owner in reversed(undo_open):
                    owner.endUndo()
        except Exception:
            error = traceback.format_exc()
        finally:
            font.enableUpdateInterface()
            self.busy = False
        self.refresh()
        Glyphs.redraw()
        if error:
            Glyphs.showMacroWindow()
            print(error)
            self.w.status.set("Edit failed; see Macro Window. Undo is in each edited glyph.")
            return
        root_mismatched = []
        for layer in roots:
            message, change = sidebearing_result(
                layer, bearing, root_before[(layer.parent.name, layer.layerId)], delta, "selected glyph")
            print(message)
            if abs(change - delta) > .01:
                root_mismatched.append(layer)
        for layer, lsb, rsb in updates:
            if (layer.parent.name, layer.layerId) not in root_before:
                message, change = sidebearing_result(
                    layer, bearing, before[(layer.parent.name, layer.layerId)], delta, "component source")
                print(message)
        mismatched = [(layer, lsb, rsb) for layer, lsb, rsb in updates
                      if abs(layer.LSB - lsb) > .01 or abs(layer.RSB - rsb) > .01]
        if mismatched:
            Glyphs.showMacroWindow()
            print("%s: %s %+g targets did not stick:" % (glyph.name, bearing, delta))
            for layer, lsb, rsb in mismatched:
                print(bearing_diagnostics(layer, lsb, rsb, before[(layer.parent.name, layer.layerId)]))
            self.w.status.set("Some targets differ; before/target/actual and component details are in Macro Window.")
        elif root_mismatched:
            Glyphs.showMacroWindow()
            print("Component edits reached their targets, but %s's measured %s change differs from %+g on %i layer(s)."
                  % (glyph.name, bearing, delta, len(root_mismatched)))
            for layer in root_mismatched:
                old = root_before[(layer.parent.name, layer.layerId)]
                print(bearing_diagnostics(
                    layer, old[0] + (delta if bearing == "LSB" else 0),
                    old[1] + (delta if bearing == "RSB" else 0), old))
            self.w.status.set("Sources changed; %s's measured %s differs from %+g on %i layers. See RESULT lines."
                              % (glyph.name, bearing, delta, len(root_mismatched)))
        else:
            self.w.status.set("Measured %s %s %+g on %i layers. Edited: %s. Undo is in the edited glyphs."
                              % (glyph.name, bearing, delta, len(roots),
                                 ", ".join(owner.name for owner in edited_glyphs)))

    def open_corner_anchor_dialog(self, sender):
        font, glyph = self.selection()
        if glyph is None:
            self.w.status.set("Select a glyph in an open font first.")
            return
        try:
            dialog = self.corner_anchor_dialog
            if dialog is not None and getattr(dialog.w, "_window", None) is not None:
                dialog.w.show()
                dialog.w.getNSWindow().makeKeyAndOrderFront_(None)
                return
            path = corner_anchor_script_path()
            namespace = runpy.run_path(path, run_name="somerville_math_corner_anchors")
            self.corner_anchor_dialog = namespace["MathCornerAnchorDialog"](
                on_added=self.corner_anchors_added, selection=self.selection
            )
        except Exception:
            Glyphs.showMacroWindow()
            traceback.print_exc()
            self.w.status.set("Could not open corner anchor selector. See Macro Window.")

    def corner_anchors_added(self, message):
        self.refresh()
        self.w.status.set(message)
        Glyphs.redraw()

    def close(self, sender):
        dialog = self.corner_anchor_dialog
        if dialog is not None and getattr(dialog.w, "_window", None) is not None:
            dialog.w.close()
        self.corner_anchor_dialog = None
        Glyphs.removeCallback(self.refresh)


if __name__ == "__main__":
    # A closed Vanilla window can leave its script instance alive.
    previous_window = getattr(globals().get("anchor_mover"), "w", None)
    if getattr(previous_window, "_window", None) is not None:
        previous_window.close()
    anchor_mover = AnchorMover()
