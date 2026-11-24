"""Fill missing horizontal-arrow intermediate layers for export, without saving.

Run inside Glyphs 4 / Glyphs CLI (build.sh uses glyphs_export_prepare.py).
The allowlists below are deliberately hardcoded. Each glyph keeps its own
components and MATH metadata. Existing intermediate layers are never replaced.
"""

from time import perf_counter
from uuid import uuid4
from itertools import groupby

from objc import autorelease_pool


BOTH_AXES = (
    'leftArrow',  # ←
    'rightArrow',  # →
    'leftRightArrow',  # ↔
    'leftDoubleArrow',  # ⇐
    'rightDoubleArrow',  # ⇒
    'leftRightDoubleArrow',  # ⇔
    'leftStrokeArrow',  # ↚
    'rightStrokeArrow',  # ↛
    'leftRightStrokeArrow',  # ↮
    'leftDoubleStrokeArrow',  # ⇍
    'rightDoubleStrokeArrow',  # ⇏
    'leftRightDoubleStrokeArrow',  # ⇎
    'leftTwoheadedArrow',  # ↞
    'rightTwoheadedArrow',  # ↠
    'leftTailArrow',  # ↢
    'rightTailArrow',  # ↣
    'leftFrombarArrow',  # ↤
    'rightFrombarArrow',  # ↦
    'leftTabArrow',  # ⇤
    'rightTabArrow',  # ⇥
    'leftDoubleArrowFromBar',  # ⤆
    'rightDoubleArrowFromBar',  # ⤇
    'leftVerticalStrokeArrow',  # ⇷
    'rightVerticalStrokeArrow',  # ⇸
    'leftRightVerticalStrokeArrow',  # ⇹
    'leftDoubleVerticalStrokeArrow',  # ⇺
    'rightDoubleVerticalStrokeArrow',  # ⇻
    'rightTwoHeadedArrowWithVerticalStroke',  # ⤀
    'rightTwoHeadedArrowWithDoubleVerticalStroke',  # ⤁
    'leftDoubleArrowWithVerticalStroke',  # ⤂
    'rightDoubleArrowWithVerticalStroke',  # ⤃
    'leftRightDoubleArrowWithVerticalStroke',  # ⤄
    'rightTwoHeadedArrowFromBar',  # ⤅
    'rightArrowWithTailWithVerticalStroke',  # ⤔
    'rightArrowWithTailWithDoubleVerticalStroke',  # ⤕
    'rightTwoHeadedArrowWithTail',  # ⤖
    'rightTwoHeadedArrowWithTailWithVerticalStroke',  # ⤗
    'rightTwoHeadedArrowWithTailWithDoubleVerticalStroke',  # ⤘
    'rightOverLeftArrow',  # ⇄
    'leftAndRightArrow',  # ⇆
    'leftDoublePairedArrow',  # ⇇
    'rightDoublePairedArrow',  # ⇉
    'leftToBarOverRightToBarArrow',  # ↹
    'leftBarbUpHarpoon',  # ↼
    'leftBarbDownHarpoon',  # ↽
    'rightBarbUpHarpoon',  # ⇀
    'rightBarbdownHarpoon',  # ⇁
    'leftOverRightHarpoon',  # ⇋
    'rightOverLeftHarpoon',  # ⇌
    'leftBarbUpRightBarbDownHarpoon',  # ⥊
    'leftBarbDownRightBarbUpHarpoon',  # ⥋
    'leftBarbUpRightBarbUpHarpoon',  # ⥎
    'leftBarbDownRightBarbDownHarpoon',  # ⥐
    'leftHarpoonWithBarbUpToBar',  # ⥒
    'rightHarpoonWithBarbUpToBar',  # ⥓
    'leftHarpoonWithBarbDownToBar',  # ⥖
    'rightHarpoonWithBarbDownToBar',  # ⥗
    'leftHarpoonWithBarbUpFromBar',  # ⥚
    'rightHarpoonWithBarbUpFromBar',  # ⥛
    'leftHarpoonWithBarbDownFromBar',  # ⥞
    'rightHarpoonWithBarbDownFromBar',  # ⥟
    'leftHarpoonWithBarbUpAboveLeftHarpoonWithBarbDown',  # ⥢
    'rightHarpoonWithBarbUpAboveRightHarpoonWithBarbDown',  # ⥤
    'leftHarpoonWithBarbUpAboveRightHarpoonWithBarbUp',  # ⥦
    'leftHarpoonWithBarbDownAboveRightHarpoonWithBarbDown',  # ⥧
    'rightHarpoonWithBarbUpAboveLeftHarpoonWithBarbUp',  # ⥨
    'rightHarpoonWithBarbDownAboveLeftHarpoonWithBarbDown',  # ⥩
    'leftHarpoonWithBarbUpAboveLongDash',  # ⥪
    'leftHarpoonWithBarbDownBelowLongDash',  # ⥫
    'rightHarpoonWithBarbUpAboveLongDash',  # ⥬
    'rightHarpoonWithBarbDownBelowLongDash',  # ⥭
    'leftLongArrow',  # ⟵
    'rightLongArrow',  # ⟶
    'leftRightLongArrow',  # ⟷
    'leftLongDoubleArrow',  # ⟸
    'rightLongDoubleArrow',  # ⟹
    'leftRightLongDoubleArrow',  # ⟺
    'leftLongFromBarArrow',  # ⟻
    'rightLongFromBarArrow',  # ⟼
    'leftLongDoubleFromBarArrow',  # ⟽
    'rightLongDoubleFromBarArrow',  # ⟾
    'leftTwoHeadedArrowWithVerticalStroke',  # ⬴
    'leftTwoHeadedArrowWithDoubleVerticalStroke',  # ⬵
    'leftArrowWithTailWithVerticalStroke',  # ⬹
    'leftArrowWithTailWithDoubleVerticalStroke',  # ⬺
    'leftTwoHeadedArrowWithTail',  # ⬻
    'leftTwoHeadedArrowWithTailWithVerticalStroke',  # ⬼
    'leftTwoHeadedArrowWithTailWithDoubleVerticalStroke',  # ⬽
)

HEAD_ONLY = (
    'rightArrowWithDottedStem',  # ⤑
    'leftArrowWithDottedStem',  # ⬸
)

LENGTH_ONLY = (
    'leftArrowTail',  # ⤙
    'rightArrowTail',  # ⤚
    'leftDoubleArrowTail',  # ⤛
    'rightDoubleArrowTail',  # ⤜
)


# Include the corresponding docked stylistic variants when present.
VARIANT_SUFFIXES = ('', '.ss17')


def add_arrow_intermediates(font):
    # Batch notifications while thousands of export-only layers are created.
    # Always restore updates, including if a component fails to interpolate.
    font.disableUpdateInterface()
    try:
        return _add_arrow_intermediates(font)
    finally:
        font.enableUpdateInterface()


def _add_arrow_intermediates(font):
    started = perf_counter()
    axis_ids = [axis.axisId for axis in font.axes]
    by_tag = {axis.axisTag: axis.axisId for axis in font.axes}
    if not {'ARLN', 'ARHD'} <= by_tag.keys():
        raise ValueError('The arrow prefilter requires the ARLN and ARHD axes.')
    masters = {master.id: master for master in font.masters}

    def master_coordinates(master_id):
        return dict(zip(axis_ids, masters[master_id].axes))

    def coordinates(layer):
        raw = layer.attributes.get('coordinates')
        if raw is None:
            return None
        # Normalize sparse dictionaries with their associated master values.
        result = master_coordinates(layer.associatedMasterId)
        result.update(raw)
        return result

    def location(coords):
        # Compare full locations, independent of layer name, ID, and order.
        return tuple(float(coords[axis_id]) for axis_id in axis_ids)

    # Snapshot the template before adding anything, including to rightArrow.
    right = font.glyphs['rightArrow']
    if right is None:
        raise ValueError('The arrow prefilter requires rightArrow as its location template.')
    templates = []
    for layer in right.layers:
        coords = coordinates(layer)
        if not layer.isSpecialLayer or coords is None:
            continue
        baseline = master_coordinates(layer.associatedMasterId)
        changed = {tag for tag, axis_id in by_tag.items()
                   if coords[axis_id] != baseline[axis_id]}
        if changed and changed <= {'ARLN', 'ARHD'}:
            templates.append((layer.associatedMasterId, layer.name, coords, changed))
    if not templates:
        raise ValueError('rightArrow has no ARLN/ARHD intermediate locations.')

    added = []
    skipped = 0
    processed = 0
    missing = []
    print('Arrow prefilter: preparing horizontal arrows (source will not be saved).',
          flush=True)
    for names, axes in ((BOTH_AXES, {'ARLN', 'ARHD'}),
                        (HEAD_ONLY, {'ARHD'}), (LENGTH_ONLY, {'ARLN'})):
        for name in names:
            for suffix in VARIANT_SUFFIXES:
                glyph_name = name + suffix
                glyph = font.glyphs[glyph_name]
                if glyph is None:
                    if not suffix:
                        missing.append(glyph_name)
                    continue
                processed += 1
                existing = {location(coords) for layer in glyph.layers
                            if (coords := coordinates(layer)) is not None}
                count = 0
                for master_id, layer_name, coords, changed in templates:
                    if not changed <= axes:
                        continue
                    key = location(coords)
                    if key in existing:
                        skipped += 1
                        continue
                    master_layer = glyph.layers[master_id]
                    if master_layer is None:
                        raise ValueError('Missing master %s in %s' % (master_id, glyph_name))
                    if not master_layer.components:
                        raise ValueError('Expected component-based arrow: ' + glyph_name)
                    layer = master_layer.copy()
                    layer.layerId = str(uuid4()).upper()
                    layer.associatedMasterId = master_id
                    layer.attributes['coordinates'] = coords.copy()
                    layer.name = layer_name
                    glyph.layers.append(layer)
                    layer.setNeedsAlignment()
                    existing.add(key)
                    added.append((glyph_name, layer))
                    count += 1
                if count:
                    print('  %s: added %d layers' % (glyph_name, count), flush=True)

    # First finish the layer inventory, then resolve component interpolation.
    # Adding more layers invalidates interpolation caches; interleaving both
    # operations would rebuild those caches for every new layer.
    print('Arrow prefilter: aligning %d new layers...' % len(added), flush=True)
    aligned = 0
    by_location = sorted(added, key=lambda item: location(coordinates(item[1])))
    for key, group in groupby(by_location, key=lambda item: location(coordinates(item[1]))):
        # Keep one location's interpolation proxies alive for reuse across
        # arrows, then release native temporaries before the next location.
        with autorelease_pool():
            for glyph_name, layer in group:
                layer.alignComponents()
                aligned += 1
        print('Arrow prefilter: aligned %d/%d layers (%.2f seconds).'
              % (aligned, len(added), perf_counter() - started), flush=True)

    elapsed = perf_counter() - started
    print('Arrow prefilter: added %d layers across %d glyphs; '
          'skipped %d existing locations; %.2f seconds (not saved).'
          % (len(added), processed, skipped, elapsed), flush=True)
    if missing:
        print('Arrow prefilter: absent base glyphs skipped: ' + ', '.join(missing),
              flush=True)
    return added


if __name__ == '__main__':
    from GlyphsApp import Glyphs

    for font in Glyphs.fonts:
        add_arrow_intermediates(font)
