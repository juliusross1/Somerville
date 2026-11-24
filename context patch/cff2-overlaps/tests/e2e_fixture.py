#!/usr/bin/env python3
"""Build reproducible local regression fonts and a ConTeXt input, without editing source fonts."""
from pathlib import Path
import argparse
import shutil

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.ttLib import TTFont


def build(output, source):
    output.mkdir(parents=True, exist_ok=True)
    f = TTFont(source)
    assert 'CFF2' in f and f.getBestCmap().get(0x2A01)
    f['CFF2'].cff.topDictIndex[0].FontMatrix = [1/f['head'].unitsPerEm, 0, 0, 1/f['head'].unitsPerEm, 0, 0]
    for record in f['name'].names:
        if record.nameID in (1, 3, 4, 6, 16, 25):
            record.string = ('CFF2OverlapFixture-' + str(record.nameID)).encode(record.getEncoding())
    gs, order, upm = f.getGlyphSet(), f.getGlyphOrder(), f['head'].unitsPerEm
    probes = [n for n in ('uni2A01','uni2A01.s01','uni2A01.s08','uni2A01.s20',
                          'uni2A01.ss16','uni2A01.ss16.s01','uni2A01.ss16.s08','uni2A01.ss16.s20',
                          'u1D437','u1D46B') if n in order]
    if len(probes)>1:
        for table in f['cmap'].tables:
            if table.isUnicode():
                table.cmap.update({0xE000+i:name for i,name in enumerate(probes)})
    f.save(output/'variable.otf')
    for ttf, family, destination in [(False, 'CFF1UnchangedControl', 'static-cff1.otf'), (True, 'TTFUnchangedControl', 'static-ttf.ttf')]:
        fb = FontBuilder(upm, isTTF=ttf)
        fb.setupGlyphOrder(order)
        fb.setupCharacterMap(f.getBestCmap())
        chars = {}
        for name in order:
            if ttf:
                pen = TTGlyphPen(gs)
                gs[name].draw(Cu2QuPen(pen, max_err=0.25, reverse_direction=True))
                chars[name] = pen.glyph()
            else:
                pen = T2CharStringPen(f['hmtx'][name][0], gs)
                gs[name].draw(pen)
                chars[name] = pen.getCharString()
        if ttf:
            fb.setupGlyf(chars)
        else:
            fb.setupCFF(family, {'FullName': family, 'FamilyName': family, 'Weight': 'Regular',
                               'FontMatrix': [1/upm, 0, 0, 1/upm, 0, 0]}, chars, {})
        fb.setupHorizontalMetrics(dict(f['hmtx'].metrics))
        fb.setupHorizontalHeader(ascent=1200, descent=-700)
        fb.setupNameTable({'familyName': family, 'styleName': 'Regular', 'uniqueFontIdentifier': family,
                          'fullName': family, 'psName': family})
        fb.setupOS2(sTypoAscender=1200, sTypoDescender=-700, usWinAscent=1200, usWinDescent=700)
        fb.setupPost()
        fb.save(output/destination)
    content = [r'\setupbodyfont[modern,10pt]', r'\setuppapersize[A4]',
               r'\setuppagenumbering[location=]', r'\starttext']
    # Baseline/patched work directories are siblings of fixtures. Relative font
    # paths avoid ConTeXt's font specification parser splitting spaces in the
    # repository's "context patch" absolute path.
    texfonts = Path('../fixtures')
    locations = [('default', 'wdth=95,wght=360,opsz=5'),
                 ('intermediate', 'wdth=104,wght=630,opsz=80'),
                 ('extreme', 'wdth=113,wght=900,opsz=1200')]
    if len(f['fvar'].axes)>3:
        broad = {'wdth':104,'wght':630,'opsz':80,'MGHT':630,'ARLN':400,'ARHD':200,'STYA':60,'STYB':60,'INSL':50}
        axes = {a.axisTag:a for a in f['fvar'].axes}
        locations[1] = ('intermediate', ','.join(f'{k}={min(axes[k].maxValue,max(axes[k].minValue,v)):g}'
                                               for k,v in broad.items() if k in axes))
    for label, axes in locations:
        content += [label + r' variable CFF2: \par',
                    r'\definefontfeature[e2e-%s][default][axis={%s},wipemath=no,expansion=no,protrusion=no]' % (label, axes),
                    r'{\definedfont[file:%s*e2e-%s at 38pt]AUV\char"2A01}\par\blank[big]' % (texfonts/'variable.otf', label)]
        if len(probes)>1:
            content.append(r'\page')
            for i,name in enumerate(probes):
                content += [label+' '+name+r'\par',
                            r'{\definedfont[file:%s*e2e-%s at 8pt]\char"%X}\par\blank[big]' % (texfonts/'variable.otf',label,0xE000+i)]
            content.append(r'\page')
    for label, filename in [('CFF1 unchanged control', 'static-cff1.otf'), ('TTF unchanged control', 'static-ttf.ttf')]:
        content += [label + r'\par', r'{\definedfont[file:%s at 38pt]AUV\char"2A01}\par\blank[big]' % (texfonts/filename)]
    content += [r'\page', r'Math layout using the variable CFF2 font:\par',
                r'\definefontfeature[e2e-math][mathematics][axis={wdth=95,wght=360,opsz=5},mathexpansion=no]',
                r'\definefontfeature[e2e-math-text][e2e-math][ssty=no]',
                r'\definefontfeature[e2e-math-script][e2e-math][ssty=1]',
                r'\definefontfeature[e2e-math-scriptscript][e2e-math][ssty=2]',
                r'\starttypescript[math][e2e]',
                r'\definefontsynonym[MathRoman][file:%s][features=e2e-math\mathsizesuffix]' % (texfonts/'variable.otf'),
                r'\stoptypescript', r'\definetypeface[e2e][mm][math][e2e][default]',
                r'\switchtobodyfont[e2e]', r'\m{U\bigoplus V}\par',
                r'\startformula U\bigoplus V\stopformula', r'\stoptext']
    (output/'e2e.tex').write_text('\n'.join(content)+'\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('output', type=Path)
    p.add_argument('--source', type=Path, default=Path('/tmp/somerville-cff-deep/frozen-cff2.otf'))
    a = p.parse_args()
    build(a.output.resolve(), a.source)
