from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables as ot
from fontTools.varLib.instancer import instantiateVariableFont
from instantiate_somerville import instantiate_math
from pathlib import Path
f=TTFont('/Users/juliusross/Documents/fontoutputs/SomervilleMathVF.ttf')
coords={a.axisTag:a.defaultValue for a in f['fvar'].axes}
instantiate_math(f,coords)
f=instantiateVariableFont(f,coords,inplace=True)
if 'BASE' in f:del f['BASE']
k=f['MATH'].table.MathGlyphInfo.MathKernInfo
records=dict(zip(k.MathKernCoverage.glyphs,k.MathKernInfoRecords))
def kern(v):
 t=ot.MathKern();t.HeightCount=0;t.CorrectionHeight=[]
 r=ot.MathValueRecord();r.Value=v;r.DeviceTable=None;t.KernValue=[r];return t
lefts=set()
v=f['MATH'].table.MathVariants
for u in [0x28,0x5b,0x7b]:
 name=f.getBestCmap()[u]
 construction=v.VertGlyphConstruction[v.VertGlyphCoverage.glyphs.index(name)]
 lefts.update(r.VariantGlyph for r in construction.MathGlyphVariantRecord)
 if construction.GlyphAssembly:lefts.update(r.glyph for r in construction.GlyphAssembly.PartRecords)
for n in lefts|{'M'}:
 if n not in records:
  r=ot.MathKernInfoRecord()
  for side in ['TopLeft','BottomLeft','TopRight','BottomRight']:setattr(r,side+'MathKern',None)
  records[n]=r
 r=records[n]
 if n in lefts:r.TopLeftMathKern=kern(-600);r.BottomLeftMathKern=kern(-200)
 if n=='M':r.BottomRightMathKern=kern(100);r.TopRightMathKern=kern(200)
items=sorted(records.items(),key=lambda it:f.getGlyphID(it[0]))
k.MathKernCoverage.glyphs=[n for n,r in items];k.MathKernInfoRecords=[r for n,r in items];k.MathKernCount=len(items)
f.save('/tmp/somerville-fenced-prescripts/tests/FenceProbe.ttf')
print('Test font with asymmetric corner kerns generated')
