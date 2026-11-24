#!/usr/bin/env python3
"""Compare baseline nonzero-filled CFF2-derived outlines with patched evenodd-filled CFF1.

Also require exact control outlines and identical PDF advance-width arrays. This
operates on embedded glyphs, independently of the helper's request/response data.
"""
import argparse
import hashlib
import importlib.util
import io
import itertools
import json
import re
import zlib
from pathlib import Path

import pathops
from fontTools.cffLib import CFFFontSet
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont


def streams(pdf):
    for m in re.finditer(rb'\bstream\r?\n(.*?)\r?\nendstream', pdf, re.S):
        try:
            yield zlib.decompress(m[1])
        except zlib.error:
            yield m[1]


def read_pdf(path):
    fonts, widths = [], []
    pdf = Path(path).read_bytes()
    objects = {}
    for match in re.finditer(rb'(\d+)\s+0\s+obj\s*(.*?)\r?\nstream\r?\n(.*?)\r?\nendstream', pdf, re.S):
        dictionary, data = match[2], match[3]
        if not re.search(rb'/Type\s*/ObjStm\b', dictionary):
            continue
        first = int(re.search(rb'/First\s*(\d+)', dictionary)[1])
        count = int(re.search(rb'/N\s*(\d+)', dictionary)[1])
        try: data = zlib.decompress(data)
        except zlib.error: pass
        numbers = list(map(int, data[:first].split()))
        assert len(numbers) == count * 2
        for i in range(count):
            start = first+numbers[i*2+1]
            end = first+numbers[(i+1)*2+1] if i+1<count else len(data)
            objects[numbers[i*2]] = data[start:end]
    for raw in list(streams(pdf)) + list(objects.values()):
        for match in re.finditer(rb'/W\s+(\d+)\s+0\s+R', raw):
            widths.append(re.sub(rb'\s+', b' ', objects[int(match[1])]).strip().decode())
        for match in re.finditer(rb'/W\s*\[', raw):
            start = raw.index(b'[', match.start())
            end, depth = start, 1
            while depth:
                end += 1
                if raw[end] == 91: depth += 1
                if raw[end] == 93: depth -= 1
            widths.append(re.sub(rb'\s+', b' ', raw[start:end+1]).decode())
        if raw.startswith(b'\x01\x00'):
            f = CFFFontSet()
            f.decompile(io.BytesIO(raw), TTFont())
            t = f.topDictIndex[0]
            family = getattr(t, 'FamilyName', 'unknown')
            glyphs = {}
            for name in t.charset:
                p = RecordingPen()
                t.CharStrings[name].draw(p)
                glyphs[name] = p
            fonts.append({'kind': 'cff', 'family': family, 'glyphs': glyphs})
        elif raw.startswith((b'\x00\x01\x00\x00', b'true')):
            f = TTFont(io.BytesIO(raw))
            # The subset has no name table in ConTeXt's glyf embedding.
            glyphs = {}
            for name, glyph in f.getGlyphSet().items():
                p = RecordingPen()
                glyph.draw(p)
                glyphs[name] = p
            fonts.append({'kind': 'ttf', 'family': 'TTF control', 'glyphs': glyphs})
    return fonts, sorted(set(widths))


def region(record, evenodd):
    p = pathops.Path()
    p.fillType = pathops.FillType.EVEN_ODD if evenodd else pathops.FillType.WINDING
    record.replay(p.getPen())
    return pathops.simplify(p)


_helper_spec=importlib.util.spec_from_file_location('overlap_winding_reference',Path(__file__).resolve().parents[1]/'font-cff-overlaps.py')
_helper=importlib.util.module_from_spec(_helper_spec)
_helper_spec.loader.exec_module(_helper)


class RawRegion:
    """Original double-coordinate paths; no Skia boolean or classification."""
    def __init__(self,record,evenodd):
        segments=[]
        for op,points in record.value:
            if op in ('moveTo','lineTo','curveTo'):
                segments.append([v for point in points for v in point]+[{'moveTo':'m','lineTo':'l','curveTo':'c'}[op]])
        pen=BoundsPen(None);record.replay(pen)
        self.bounds=pen.bounds or (0,0,0,0)
        self.winding=_helper.CompiledWinding(segments)
        self.evenodd=evenodd
    def contains(self,point):
        n=self.winding(point)
        return bool(n%2) if self.evenodd else bool(n)


def raw_region(record, evenodd):
    return RawRegion(record,evenodd)


def grid_error(a,b,resolution=96):
    """Independent fill-rule sampling: never boolean-simplify the reference.

    This avoids PathOps' demonstrated floating-point boolean failure on an
    otherwise correct original italic D. Irrational offsets avoid sampling
    systematically on horizontal/vertical boundaries.
    """
    ax0,ay0,ax1,ay1=a.bounds;bx0,by0,bx1,by1=b.bounds
    x0,y0,x1,y1=min(ax0,bx0),min(ay0,by0),max(ax1,bx1),max(ay1,by1)
    if x0==x1 or y0==y1:return 0.0
    changed=0
    for iy in range(resolution):
        y=y0+(iy+.371239)*(y1-y0)/resolution
        for ix in range(resolution):
            point=(x0+(ix+.618731)*(x1-x0)/resolution,y)
            changed += a.contains(point)!=b.contains(point)
    return changed/(resolution*resolution)


def difference(a, b):
    diffs = []
    assert a['glyphs'].keys() == b['glyphs'].keys()
    for key in a['glyphs']:
        ar, br = region(a['glyphs'][key], False), region(b['glyphs'][key], True)
        delta = pathops.op(ar, br, pathops.PathOp.XOR)
        diffs.append({'glyph': key, 'xor_area': delta.area, 'reference_area': ar.area,
                      'relative_error': delta.area / max(ar.area, 1)})
    return diffs


def fingerprint(font):
    return hashlib.sha256(repr([(n, p.value) for n, p in font['glyphs'].items()]).encode()).hexdigest()


def against_source(bv, av, source):
    f = TTFont(source)
    locations = [{'wdth':95, 'wght':360, 'opsz':5}, {'wdth':104, 'wght':630, 'opsz':80},
                 {'wdth':113, 'wght':900, 'opsz':1200}]
    if len(f['fvar'].axes)>3:
        broad = {'wdth':104,'wght':630,'opsz':80,'MGHT':630,'ARLN':400,'ARHD':200,'STYA':60,'STYB':60,'INSL':50}
        axes = {a.axisTag:a for a in f['fvar'].axes}
        locations[1] = {k:min(axes[k].maxValue,max(axes[k].minValue,v)) for k,v in broad.items() if k in axes}
    refs = []
    for location in locations:
        shapes = {}
        for name, glyph in f.getGlyphSet(location=location).items():
            p = RecordingPen(); glyph.draw(p)
            r = raw_region(p, False)
            if p.value: shapes[name] = r
        refs.append(shapes)
    def error(a, b):
        return grid_error(a,b,48)
    # Every fixture starts with a plain capital A. Identify axis instances by
    # their original A, not by PDF's arbitrary font/subset ordering.
    choices = []
    for order in itertools.permutations(range(3)):
        score = sum(error(refs[j]['A'],raw_region(bv[i]['glyphs']['cid00001'],False)) for i,j in enumerate(order))
        choices.append((score,order))
    _, axes = min(choices)
    # Match the patched subset to the baseline subset by the original font's
    # selected axis location and its first glyph. This is independent of names.
    _, order = min((sum(error(refs[axes[i]]['A'],raw_region(av[j]['glyphs']['cid00001'],False)) for i,j in enumerate(order)),order)
                  for order in itertools.permutations(range(3)))
    details = []
    explicit = ['A','U','V','uni2A01']
    if 'uni2A01.s20' in f.getGlyphOrder():
        explicit += ['uni2A01','uni2A01.s01','uni2A01.s08','uni2A01.s20','uni2A01.ss16',
                     'uni2A01.ss16.s01','uni2A01.ss16.s08','uni2A01.ss16.s20','u1D437','u1D46B',
                     'u1D448','u1D449','uni2A01.s02']
    for i,j in enumerate(order):
        assert bv[i]['glyphs'].keys() == av[j]['glyphs'].keys()
        shapes = refs[axes[i]]
        for key, original in bv[i]['glyphs'].items():
            if key == '.notdef': continue
            original = raw_region(original,False)
            output = raw_region(av[j]['glyphs'][key],True)
            if original.bounds[0]==original.bounds[2] or original.bounds[1]==original.bounds[3]:
                assert output.bounds[0]==output.bounds[2] or output.bounds[1]==output.bounds[3]; continue
            bounds = original.bounds
            number=int(key[3:])
            nearest = [explicit[number-1]] if number<=len(explicit) else sorted(shapes, key=lambda n:sum(abs(x-y) for x,y in zip(shapes[n].bounds,bounds)))[:12]
            before_error,name = min((error(shapes[n],original),n) for n in nearest)
            after_error = grid_error(shapes[name],output)
            assert before_error < .06, f'Cannot identify baseline glyph {key} at {locations[axes[i]]}: {before_error}'
            assert after_error < .0002, f'Source mismatch: {name} {locations[axes[i]]}: {after_error}'
            details.append({'location':locations[axes[i]],'pdf_glyph':key,'source_glyph':name,
                            'before_grid_mismatch_fraction':before_error,'after_grid_mismatch_fraction':after_error})
    return details


def audit(before, after, source=None):
    bf, bw = read_pdf(before)
    af, aw = read_pdf(after)
    assert bw and bw == aw, 'PDF width arrays changed or were not found'
    assert len(bf) == len(af), 'Embedded font count changed'
    variable = lambda f: f['kind'] == 'cff' and f['family'].startswith('CFF2OverlapFixture')
    bv, av = [f for f in bf if variable(f)], [f for f in af if variable(f)]
    assert len(bv) == len(av) == 3, 'Expected default/intermediate/extreme CFF2 instances'
    for f in [f for f in bf if not variable(f)]:
        matches = [g for g in af if g['family'] == f['family'] and g['kind'] == f['kind']]
        assert len(matches) == 1 and fingerprint(matches[0]) == fingerprint(f), 'Control outline changed: '+f['family']
    if source:
        details = against_source(bv,av,source)
        return {'passed':True,'cff2_instances':3,'unchanged_control_fonts':len(bf)-3,
                'width_arrays_unchanged':len(bw),'maximum_grid_mismatch_fraction':max(x['after_grid_mismatch_fraction'] for x in details),
                'reference_validation':'96x96 original double-coordinate cubic standalone winding grid per glyph; no Skia boolean or classifier',
                'source_comparison':details}
    # PDF subset order is arbitrary. Match axis instances by geometric agreement.
    candidates = []
    for order in itertools.permutations(range(3)):
        ds = [difference(bv[i], av[j]) for i, j in enumerate(order)]
        candidates.append((sum(x['relative_error'] for d in ds for x in d), order, ds))
    score, order, ds = min(candidates)
    maximum = max(x['relative_error'] for d in ds for x in d)
    assert maximum < 0.0001, f'Filled region mismatch: maximum relative XOR area {maximum}'
    changed = sum(fingerprint(bv[i]) != fingerprint(av[j]) for i, j in enumerate(order))
    assert changed == 3, 'Expected all three CFF2 instances to have resolved overlaps'
    return {'passed': True, 'cff2_instances': 3, 'unchanged_control_fonts': len(bf)-3,
            'width_arrays_unchanged': len(bw), 'maximum_relative_xor_area': maximum,
            'instance_details': ds}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('before', type=Path)
    p.add_argument('after', type=Path)
    p.add_argument('--output', type=Path)
    p.add_argument('--source', type=Path, help='Original variable fixture; compares against independent FontTools interpolation')
    a = p.parse_args()
    report = json.dumps(audit(a.before, a.after, a.source), indent=2)
    if a.output: a.output.write_text(report+'\n')
    print(report)
