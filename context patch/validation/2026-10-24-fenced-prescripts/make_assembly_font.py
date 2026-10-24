from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables as ot
f=TTFont('/opt/homebrew/Cellar/texlive/20260301/share/texmf-dist/fonts/opentype/public/lm-math/latinmodern-math.otf')
info=f['MATH'].table.MathGlyphInfo
if not info.MathKernInfo:
 k=ot.MathKernInfo();k.MathKernCoverage=ot.Coverage();k.MathKernCoverage.glyphs=[];k.MathKernInfoRecords=[];info.MathKernInfo=k
k=info.MathKernInfo;records=dict(zip(k.MathKernCoverage.glyphs,k.MathKernInfoRecords))
def kern(v):
 t=ot.MathKern();t.HeightCount=0;t.CorrectionHeight=[];r=ot.MathValueRecord();r.Value=v;r.DeviceTable=None;t.KernValue=[r];return t
v=f['MATH'].table.MathVariants
lefts=set()
for u in [40,91,123]:
 n=f.getBestCmap()[u];c=v.VertGlyphConstruction[v.VertGlyphCoverage.glyphs.index(n)]
 lefts.update(r.VariantGlyph for r in c.MathGlyphVariantRecord)
 assert c.GlyphAssembly
 lefts.update(r.glyph for r in c.GlyphAssembly.PartRecords)
 print('Assembly parts',n,[(r.glyph,r.PartFlags) for r in c.GlyphAssembly.PartRecords])
m=f.getBestCmap()[77]
for n in lefts|{m}:
 if n not in records:
  r=ot.MathKernInfoRecord()
  for side in ['TopLeft','BottomLeft','TopRight','BottomRight']:setattr(r,side+'MathKern',None)
  records[n]=r
 r=records[n]
 if n in lefts:r.TopLeftMathKern=kern(-600);r.BottomLeftMathKern=kern(-200)
 if n==m:r.BottomRightMathKern=kern(100);r.TopRightMathKern=kern(200)
items=sorted(records.items(),key=lambda it:f.getGlyphID(it[0]))
k.MathKernCoverage.glyphs=[n for n,r in items];k.MathKernInfoRecords=[r for n,r in items];k.MathKernCount=len(items)
f.save('/tmp/somerville-fenced-prescripts/tests/AssemblyProbe.otf')
