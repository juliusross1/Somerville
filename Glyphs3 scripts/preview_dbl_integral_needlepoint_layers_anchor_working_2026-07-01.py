#MenuTitle: Preview dblIntegral Needlepoint Layers
# -*- coding: utf-8 -*-

import vanilla
from AppKit import (
    NSAffineTransform,
    NSBezierPath,
    NSColor,
    NSImage,
    NSMakeRect,
    NSMakeSize,
)
from Foundation import NSTimer
from GlyphsApp import Glyphs


SCRIPT_VERSION = "2026-07-01 16:42 CDT live-anchor-alignment"
GLYPH_NAME = "dblIntegral"
PREVIEW_MASTERS = (
    ("Needlepoint SemiCondensed Upright", "SemiCondensed"),
    ("Needlepoint SemiExpanded Upright", "SemiExpanded"),
)
WINDOW_SIZE = (720, 420)
REDRAW_INTERVAL = 0.20


def print_warning(message):
    print("WARNING: %s" % message)


def safe_call(value, default=None):
    if callable(value):
        try:
            return value()
        except Exception:
            return default
    return value


def master_name(master):
    return str(safe_call(getattr(master, "name", None), "") or "")


def glyph_for_name(font, glyph_name):
    try:
        return font.glyphs[glyph_name]
    except Exception:
        return None


def component_name(component):
    for attribute_name in ("componentName", "name"):
        value = safe_call(getattr(component, attribute_name, None))
        if value:
            return str(value)
    return ""


def layer_name(layer):
    return str(safe_call(getattr(layer, "name", None), "") or "")


def compact_name(name):
    return str(name or "").lower().replace(" ", "")


def master_for_name(font, wanted_name):
    try:
        masters = list(font.masters)
    except Exception:
        masters = []

    for master in masters:
        if master_name(master) == wanted_name:
            return master

    wanted_compact = compact_name(wanted_name)
    for master in masters:
        if compact_name(master_name(master)) == wanted_compact:
            return master

    return None


def layer_for_master(glyph, master):
    if glyph is None or master is None:
        return None

    master_id = getattr(master, "id", None)
    if master_id:
        try:
            layer = glyph.layers[master_id]
            if layer is not None:
                return layer
        except Exception:
            pass

    for layer in glyph.layers:
        if getattr(layer, "associatedMasterId", None) == master_id:
            return layer
        if getattr(layer, "layerId", None) == master_id:
            return layer

    return None


def layer_for_hint(glyph, hint_layer):
    if glyph is None or hint_layer is None:
        return None

    hint_layer_id = getattr(hint_layer, "layerId", None)
    if hint_layer_id:
        try:
            layer = glyph.layers[hint_layer_id]
            if layer is not None:
                return layer
        except Exception:
            pass

    hint_associated_master_id = getattr(hint_layer, "associatedMasterId", None)
    hint_name = layer_name(hint_layer)
    for layer in glyph.layers:
        if hint_name and layer_name(layer) == hint_name:
            return layer
        if hint_associated_master_id and getattr(layer, "associatedMasterId", None) == hint_associated_master_id:
            return layer

    return None


def append_path(target_path, source_path):
    if source_path is None:
        return False

    try:
        if source_path.isEmpty():
            return False
    except Exception:
        pass

    try:
        target_path.appendBezierPath_(source_path)
        return True
    except Exception:
        return False


def layer_direct_path(layer):
    path = NSBezierPath.bezierPath()
    appended = False

    try:
        layer_paths = list(layer.paths)
    except Exception:
        layer_paths = []

    for layer_path_item in layer_paths:
        for attribute_name in ("bezierPath", "completeBezierPath"):
            path_value = safe_call(getattr(layer_path_item, attribute_name, None))
            if append_path(path, path_value):
                appended = True
                break

    return path if appended else None


def component_transform_values(component):
    transform = safe_call(getattr(component, "transform", None))
    if transform is not None:
        try:
            return (
                float(transform.m11),
                float(transform.m12),
                float(transform.m21),
                float(transform.m22),
                float(transform.tX),
                float(transform.tY),
            )
        except Exception:
            pass
        try:
            values = list(transform)
            if len(values) == 6:
                return tuple(float(value) for value in values)
        except Exception:
            pass

    return (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def affine_transform_from_values(values):
    transform = NSAffineTransform.transform()
    try:
        transform_struct = transform.transformStruct()
        (
            transform_struct.m11,
            transform_struct.m12,
            transform_struct.m21,
            transform_struct.m22,
            transform_struct.tX,
            transform_struct.tY,
        ) = values
        transform.setTransformStruct_(transform_struct)
    except Exception:
        pass
    return transform


def point_tuple(value):
    if value is None:
        return None
    try:
        return (float(value.x), float(value.y))
    except Exception:
        pass
    try:
        values = list(value)
        if len(values) >= 2:
            return (float(values[0]), float(values[1]))
    except Exception:
        pass
    return None


def anchor_position(layer, anchor_name):
    if layer is None:
        return None

    try:
        anchors = list(layer.anchors)
    except Exception:
        anchors = []

    for anchor in anchors:
        if str(safe_call(getattr(anchor, "name", None), "") or "") != anchor_name:
            continue
        for attribute_name in ("position", "pos"):
            position = point_tuple(safe_call(getattr(anchor, attribute_name, None)))
            if position is not None:
                return position
    return None


def transformed_point(values, point):
    if point is None:
        return None

    m11, m12, m21, m22, tx, ty = values
    x, y = point
    return (
        m11 * x + m21 * y + tx,
        m12 * x + m22 * y + ty,
    )


def values_with_translation(values, tx, ty):
    m11, m12, m21, m22, _old_tx, _old_ty = values
    return (m11, m12, m21, m22, tx, ty)


def values_aligned_to_entry(values, entry_point, target_point):
    if entry_point is None or target_point is None:
        return values

    m11, m12, m21, m22, _tx, _ty = values
    entry_x, entry_y = entry_point
    target_x, target_y = target_point
    return values_with_translation(
        values,
        target_x - (m11 * entry_x + m21 * entry_y),
        target_y - (m12 * entry_x + m22 * entry_y),
    )


def component_source_layer(component):
    component_layer_hint = safe_call(getattr(component, "componentLayer", None))
    component_layer = component_layer_hint
    name = component_name(component)
    if name:
        component_glyph = glyph_for_name(Glyphs.font, name)
        live_layer = layer_for_hint(component_glyph, component_layer_hint)
        if live_layer is not None:
            component_layer = live_layer

    return component_layer


def component_layer_path(component, seen, transform_values=None):
    component_layer = component_source_layer(component)
    source_path = layer_path(component_layer, seen)
    if source_path is None:
        return None

    if transform_values is None:
        transform_values = component_transform_values(component)

    transformed_path = source_path.copy()
    transformed_path.transformUsingAffineTransform_(
        affine_transform_from_values(transform_values)
    )
    return transformed_path


def layer_component_path(layer, seen):
    path = NSBezierPath.bezierPath()
    appended = False
    previous_exit = None

    try:
        components = list(layer.components)
    except Exception:
        components = []

    for component in components:
        component_layer = component_source_layer(component)
        transform_values = component_transform_values(component)
        entry_point = anchor_position(component_layer, "#entry")
        transform_values = values_aligned_to_entry(transform_values, entry_point, previous_exit)

        path_value = component_layer_path(component, seen, transform_values)
        if append_path(path, path_value):
            appended = True
        else:
            path_value = safe_call(getattr(component, "bezierPath", None))
            if append_path(path, path_value):
                appended = True

        exit_point = anchor_position(component_layer, "#exit")
        previous_exit = transformed_point(transform_values, exit_point)

    return path if appended else None


def layer_path(layer, seen=None):
    if layer is None:
        return None

    if seen is None:
        seen = set()
    layer_key = id(layer)
    if layer_key in seen:
        return None
    seen = set(seen)
    seen.add(layer_key)

    path = NSBezierPath.bezierPath()
    appended = False

    if append_path(path, layer_direct_path(layer)):
        appended = True
    if append_path(path, layer_component_path(layer, seen)):
        appended = True
    if appended:
        return path

    for attribute_name in ("bezierPath", "completeBezierPath"):
        value = safe_call(getattr(layer, attribute_name, None))
        if value is not None:
            return value
    return None


def image_for_layer(layer, width, height):
    image = NSImage.alloc().initWithSize_(NSMakeSize(width, height))
    image.lockFocus()
    try:
        rect = NSMakeRect(0, 0, width, height)
        NSColor.whiteColor().set()
        NSBezierPath.fillRect_(rect)
        NSColor.lightGrayColor().set()
        NSBezierPath.strokeRect_(rect)

        path = layer_path(layer)
        if path is None:
            return image

        path_bounds = path.bounds()
        if path_bounds.size.width <= 0 or path_bounds.size.height <= 0:
            return image

        margin = 18.0
        draw_rect = NSMakeRect(margin, margin, width - 2 * margin, height - 2 * margin)
        scale_x = draw_rect.size.width / path_bounds.size.width
        scale_y = draw_rect.size.height / path_bounds.size.height
        scale = min(scale_x, scale_y)

        transform = NSAffineTransform.transform()
        target_x = draw_rect.origin.x + (draw_rect.size.width - path_bounds.size.width * scale) / 2.0
        target_y = draw_rect.origin.y + (draw_rect.size.height - path_bounds.size.height * scale) / 2.0
        transform.translateXBy_yBy_(target_x, target_y)
        transform.scaleXBy_yBy_(scale, scale)
        transform.translateXBy_yBy_(-path_bounds.origin.x, -path_bounds.origin.y)

        drawn_path = path.copy()
        drawn_path.transformUsingAffineTransform_(transform)
        NSColor.blackColor().set()
        drawn_path.fill()
    finally:
        image.unlockFocus()
    return image


class DblIntegralNeedlepointPreview(object):

    def __init__(self):
        self.font = Glyphs.font
        if self.font is None:
            Glyphs.showMacroWindow()
            print_warning("No font open.")
            return

        self.image_width = 320
        self.image_height = 320
        self.w = vanilla.FloatingWindow(WINDOW_SIZE, "dblIntegral Needlepoint Preview")
        self.w.title = vanilla.TextBox((15, 12, -15, 18), "%s live layer preview" % GLYPH_NAME)

        self.image_views = []
        panel_gap = 18
        label_top = 42
        image_top = 66
        panel_width = (WINDOW_SIZE[0] - panel_gap * (len(PREVIEW_MASTERS) + 1)) // len(PREVIEW_MASTERS)
        image_size = min(panel_width, WINDOW_SIZE[1] - image_top - 28)

        for index, (master_name_value, label) in enumerate(PREVIEW_MASTERS):
            x = panel_gap + index * (panel_width + panel_gap)
            setattr(
                self.w,
                "label%i" % index,
                vanilla.TextBox((x, label_top, panel_width, 18), "%s: %s" % (label, master_name_value)),
            )
            image_view = vanilla.ImageView((x, image_top, image_size, image_size))
            setattr(self.w, "image%i" % index, image_view)
            self.image_views.append(image_view)

        self.w.status = vanilla.TextBox((15, -24, -15, 16), "Ready")
        self.update_images()
        self.w.open()
        self.w.makeKey()

        self.timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            REDRAW_INTERVAL,
            self,
            "timerCallback:",
            None,
            True,
        )

        Glyphs.showMacroWindow()
        print("dblIntegral Needlepoint Preview")
        print("Script version: %s" % SCRIPT_VERSION)
        print("Redraw interval: %.2fs" % REDRAW_INTERVAL)

    def set_status(self, text):
        try:
            self.w.status.set(text)
        except Exception:
            pass

    def update_images(self):
        glyph = glyph_for_name(self.font, GLYPH_NAME)
        if glyph is None:
            self.set_status("Missing glyph: %s" % GLYPH_NAME)
            return

        missing = []
        for index, (master_name_value, label) in enumerate(PREVIEW_MASTERS):
            master = master_for_name(self.font, master_name_value)
            if master is None:
                missing.append(master_name_value)
                continue
            layer = layer_for_master(glyph, master)
            image = image_for_layer(layer, self.image_width, self.image_height)
            self.image_views[index].getNSImageView().setImage_(image)

        if missing:
            self.set_status("Missing master: %s" % ", ".join(missing))
        else:
            self.set_status("Live")

    def timerCallback_(self, timer):
        try:
            visible = bool(self.w.getNSWindow().isVisible())
        except Exception:
            visible = False
        if not visible:
            try:
                timer.invalidate()
            except Exception:
                pass
            return
        self.update_images()


try:
    _dblIntegralNeedlepointPreview.timer.invalidate()
except Exception:
    pass

_dblIntegralNeedlepointPreview = DblIntegralNeedlepointPreview()
