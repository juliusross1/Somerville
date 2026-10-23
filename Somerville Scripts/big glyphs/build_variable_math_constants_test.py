"""Build an experimental variable-MATH font. Requires fontTools.

MathValueRecord.DeviceTable contains a VariationIndex (format 0x8000) pointing
into GDEF.VarStore. This experimentally extends MATH's device-offset usage;
consumers must support that interpretation to display the varying constants.
Existing GDEF variation indices and all base MATH values are preserved.
MATH changes are driven only by INSL, from 0 to 100. Fraction shifts and gaps
increase by one em at INSL=100 to make the spacing changes conspicuous.
"""

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables import otTables
from fontTools.varLib.builder import buildVarRegion, buildVarRegionList, buildVarData, buildVarDevTable, buildVarStore
from fontTools.varLib.varStore import VarStoreInstancer
from fontTools.varLib.models import normalizeLocation, piecewiseLinearMap


def build(source, output):
    source = Path(source)
    output = Path(output)
    if source.resolve() == output.resolve():
        raise ValueError('The experimental output must differ from the source.')
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    font = TTFont(source, recalcTimestamp=False)
    axes = font['fvar'].axes
    axis_tags = [a.axisTag for a in axes]
    insl = next(a for a in axes if a.axisTag == 'INSL')
    if (insl.minValue, insl.defaultValue, insl.maxValue) != (0, 0, 100):
        raise ValueError('This experiment expects INSL minimum/default/maximum 0/0/100.')
    fraction_spacing_delta = font['head'].unitsPerEm
    constants = font['MATH'].table.MathConstants
    old_constants = deepcopy(constants)
    old_gdef = deepcopy(font['GDEF'].table) if 'GDEF' in font else None
    if 'GDEF' not in font:
        font['GDEF'] = newTable('GDEF')
        font['GDEF'].table = otTables.GDEF()
    gdef = font['GDEF'].table
    gdef.Version = max(getattr(gdef, 'Version', 0), 0x00010003)
    store = getattr(gdef, 'VarStore', None)
    if store is None:
        store = buildVarStore(buildVarRegionList([], axis_tags), [])
        gdef.VarStore = store
    region_index = len(store.VarRegionList.Region)
    outer_index = len(store.VarData)
    if outer_index >= 65535:
        raise ValueError('No free variation outer index.')
    store.VarRegionList.Region.append(buildVarRegion({'INSL': (0, 1, 1)}, axis_tags))
    store.VarRegionList.RegionCount = len(store.VarRegionList.Region)
    entries = []
    fixed = {}
    for name, value in vars(constants).items():
        if not isinstance(value, otTables.MathValueRecord):
            fixed[name] = value
            continue
        if value.DeviceTable is not None:
            raise ValueError('%s already has device/variation data.' % name)
        base = value.Value
        # Deliberately dramatic: triple nonzero magnitudes, with at least a
        # 200-unit change. Negative kerns become more negative; zeros grow.
        delta = (1 if base >= 0 else -1) * 2 * max(abs(base), 100)
        if (name.startswith('Fraction') and name != 'FractionRuleThickness') or name.startswith('SkewedFraction'):
            delta = fraction_spacing_delta
        if not -32768 <= base + delta <= 32767:
            raise ValueError('%s would exceed int16 range.' % name)
        index = (outer_index << 16) | len(entries)
        value.DeviceTable = buildVarDevTable(index)
        entries.append(dict(constant=name, origin=base, delta=delta,
                            at_insl_100=base + delta, variation_index=index))
    store.VarData.append(buildVarData([region_index], [[e['delta']] for e in entries], optimize=False))
    store.VarDataCount = len(store.VarData)
    # Distinct names avoid confusion with the production font in font menus.
    for record in font['name'].names:
        if record.nameID in (1, 3, 4, 6, 16, 21):
            original = record.toUnicode()
            suffix = '-INSLMATHTest' if record.nameID == 6 else ' INSL MATH Test'
            record.string = (original + suffix).encode(record.getEncoding())
    output.parent.mkdir(parents=True, exist_ok=True)
    font.save(output)

    check = TTFont(output)
    new_constants = check['MATH'].table.MathConstants
    loaded_store = check['GDEF'].table.VarStore
    for normalized, fraction in [(0.0, 0.0), (0.5, 0.5), (1.0, 1.0)]:
        instancer = VarStoreInstancer(loaded_store, check['fvar'].axes, {'INSL': normalized})
        for entry in entries:
            value = getattr(new_constants, entry['constant'])
            device = value.DeviceTable
            assert device.DeltaFormat == 0x8000
            index = (device.StartSize << 16) | device.EndSize
            assert value.Value == getattr(old_constants, entry['constant']).Value
            assert value.Value + instancer[index] == entry['origin'] + fraction * entry['delta']
    # Moving weight alone must no longer change MATH constants; varying weight
    # alongside INSL must not alter the INSL adjustment either.
    for weight_normalized in (0.0, 0.5, 1.0):
        for insl_normalized in (0.0, 0.5, 1.0):
            instancer = VarStoreInstancer(
                loaded_store, check['fvar'].axes,
                {'wght': weight_normalized, 'INSL': insl_normalized},
            )
            for entry in entries:
                assert instancer[entry['variation_index']] == insl_normalized * entry['delta']
    for name, value in fixed.items():
        assert getattr(new_constants, name) == value
    # Remove just the additions from a copy and compare existing GDEF content.
    if old_gdef is not None and getattr(old_gdef, 'VarStore', None) is not None:
        restored = deepcopy(check['GDEF'].table)
        restored.VarStore.VarData = restored.VarStore.VarData[:outer_index]
        restored.VarStore.VarDataCount = outer_index
        restored.VarStore.VarRegionList.Region = restored.VarStore.VarRegionList.Region[:region_index]
        restored.VarStore.VarRegionList.RegionCount = region_index
        assert restored == old_gdef, 'Existing GDEF data changed'
    original = TTFont(source)
    for tag in original.keys():
        if tag not in ('GlyphOrder', 'head', 'MATH', 'GDEF', 'name'):
            assert original.getTableData(tag) == check.getTableData(tag), tag
    assert source_hash == hashlib.sha256(source.read_bytes()).hexdigest()
    limits = {a.axisTag: (a.minValue, a.defaultValue, a.maxValue) for a in axes}
    samples = []
    for user_insl in (0.0, 50.0, 100.0):
        location = normalizeLocation({'INSL': user_insl}, limits)
        if 'avar' in check:
            location = {tag: piecewiseLinearMap(v, check['avar'].segments.get(tag, {})) for tag, v in location.items()}
        instancer = VarStoreInstancer(loaded_store, axes, location)
        samples.append({'INSL': user_insl, 'values': {e['constant']: e['origin'] + instancer[e['variation_index']] for e in entries}})
    report = dict(source=str(source), source_sha256=source_hash, output=str(output),
                  mechanism='MATH MathValueRecord DeviceTable -> VariationIndex 0x8000 -> GDEF.VarStore',
                  variation_axis='INSL', axis_default=insl.defaultValue, axis_maximum=insl.maxValue,
                  fraction_spacing_delta=fraction_spacing_delta,
                  constants=entries, unchanged_plain_constants=fixed, samples=samples,
                  validation='Save/reopen, INSL 0/50/100, independence from wght, existing GDEF data and all unrelated tables checked.')
    report_path = output.with_suffix('.json')
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    print('Created', output)
    print('Variable constants:', len(entries), '; unchanged plain constants:', len(fixed))
    print('Validation passed. Report:', report_path)


if __name__ == '__main__':
    repo = Path(__file__).resolve().parents[2]
    default_source = repo / 'test_documents/Somerville/firefox/SomervilleVF-withMathtable-original.ttf'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', nargs='?', type=Path, default=default_source)
    parser.add_argument('--output', type=Path, default=default_source.with_name('SomervilleVF-withMathtable.ttf'))
    args = parser.parse_args()
    build(args.source, args.output)
