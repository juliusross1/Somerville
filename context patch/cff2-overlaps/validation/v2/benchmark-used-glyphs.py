from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
import hashlib,json,statistics,subprocess,sys,time
base=Path('/Users/juliusross/Documents/Somerville/context patch/cff2-overlaps')
helper=base/'font-cff-overlaps.py';helper_hash=hashlib.sha256(helper.read_bytes()).hexdigest()
font=Path('/Users/juliusross/Documents/fontoutputs/SomervilleMathVF.otf');f=TTFont(font);order=f.getGlyphOrder()
priority=['.notdef','space','A','D','U','V','u1D437','u1D46B','i','uni2A01']
priority += ['uni2A01.s%02d'%i for i in [1,3,5,8,10,12,15,18,20,2,4,6,7,9,11,13,14,16,17,19]]
priority += [n for n in order if n.startswith('uni2A01.ss16')]
priority = list(dict.fromkeys(n for n in priority if n in order))
results=[]
work=Path('/tmp/cff2-subset-bench');work.mkdir(exist_ok=True)
for location in ['default','broad']:
 requested = {'wdth':104,'wght':630,'MGHT':630,'opsz':80,'STYA':60,'STYB':60,'ARLN':200,'ARHD':200,'INSL':50}
 coordinates = {a.axisTag:(a.defaultValue if location == 'default' else min(a.maxValue,max(a.minValue,requested.get(a.axisTag,a.defaultValue)))) for a in f['fvar'].axes}
 gs=f.getGlyphSet(location=coordinates)
 glyphs=[]
 for gid,name in enumerate(order):
  pen=RecordingPen();gs[name].draw(pen)
  segments=[[*[v for xy in points for v in xy],{'moveTo':'m','lineTo':'l','curveTo':'c'}[op]] for op,points in pen.value if op not in ('closePath','endPath')]
  glyphs.append({'id':gid,'segments':segments})
 full={'protocol':1,'glyphs':glyphs}
 for size in [20,50,200,len(order)]:
  names=list(priority[:size])
  for i in range(size*2):
   if len(names)>=size:break
   name=order[min(len(order)-1,int(i*(len(order)-1)/max(1,size*2-1)))]
   if name not in names:names.append(name)
  for name in order:
   if len(names)>=size:break
   if name not in names:names.append(name)
  ids=[order.index(n) for n in names]
  request=work/f'{location}-{size}-request.json';out=work/f'{location}-{size}-response.json'
  request.write_text(json.dumps({'protocol':1,'glyphs':[full['glyphs'][i] for i in ids]}))
  runs=[]
  for repeat in range(3):
   started=time.monotonic();run=subprocess.run([sys.executable,str(helper),str(request),str(out)],capture_output=True,text=True);wall=time.monotonic()-started
   if run.returncode:raise RuntimeError(run.stderr)
   stats=json.loads(out.read_text())['stats'];runs.append({'wall_seconds':wall,'helper_seconds':stats['seconds'],'changed':stats['changed'],'unique_outlines':stats['unique_outlines']})
  entry={'location':location,'glyph_count':size,'names':names,'median_wall_seconds':statistics.median(r['wall_seconds'] for r in runs),'median_helper_seconds':statistics.median(r['helper_seconds'] for r in runs),'runs':runs};results.append(entry)
  print(location,size,'wall',entry['median_wall_seconds'],'helper',entry['median_helper_seconds'],flush=True)
  (base/'validation/v2/used-glyph-benchmark.json').write_text(json.dumps({'font':str(font),'font_sha256':hashlib.sha256(font.read_bytes()).hexdigest(),'helper_sha256':helper_hash,'python':sys.executable,'notes':'Fresh helper process for every measurement; all validation retained. Requests select representative upright/italic letters and circled-plus sizes, then distribute additional glyphs over the full glyph order. FontTools is used only here to read fixture names.','results':results},indent=2)+'\n')
assert hashlib.sha256(helper.read_bytes()).hexdigest()==helper_hash
