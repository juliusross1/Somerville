#!/usr/bin/env python3
"""Reproduce integration checks in a fresh copied ConTeXt tree, never the installed tree.

Use the project's Python with fontTools and skia-pathops. The supplied --scratch
directory must not exist; --output receives the compact reproducible evidence.
"""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys

from e2e_fixture import build
from audit_pdf import audit, read_pdf

PACKAGE = Path(__file__).resolve().parents[1]


def run(args):
    assert not args.refresh_helper or args.resume, '--refresh-helper requires --resume'
    assert args.resume or not args.scratch.exists(), '--scratch must be a new directory'
    assert args.tree.resolve() != args.scratch.resolve(), 'Refusing to modify the source tree'
    args.scratch.mkdir(parents=True,exist_ok=args.resume)
    args.output.mkdir(parents=True,exist_ok=True)
    tree = args.scratch/'tex'
    tree.mkdir(exist_ok=args.resume)
    for name in ('texmf','texmf-context','texmf-osx-arm64'):
        if not args.resume: shutil.copytree(args.tree/name,tree/name,symlinks=True)
    for name in ('texmf-cache','texmf-fonts','texmf-local','texmf-project','texmf-modules'):
        (tree/name).mkdir(exist_ok=True)
    base = tree/'texmf-context/tex/context/base/mkxl'
    executable = tree/'texmf-osx-arm64/bin/context'
    env = dict(os.environ)
    env['PATH'] = str(executable.parent)+os.pathsep+env.get('PATH','')
    env['TEXMFCACHE'] = str(tree/'texmf-cache')
    env['CONTEXT_CFF2_OVERLAPS_PYTHON'] = sys.executable

    def invoke(folder,filename,environment=env,expect=0):
        folder.mkdir(exist_ok=True)
        log = folder/(filename+'.console.log')
        with log.open('w') as out:
            p=subprocess.run([str(executable),'--once','--nonstopmode',filename],cwd=folder,env=environment,
                             stdout=out,stderr=subprocess.STDOUT)
        assert (p.returncode==0)==(expect==0), f'Unexpected status {p.returncode}; see {log}'
        return log.read_text()

    def make(label):
        with (args.output/(label+'-make.log')).open('w') as out:
            subprocess.run([str(executable),'--make','en'],cwd=args.output,env=env,
                           stdout=out,stderr=subprocess.STDOUT,check=True)

    def install(which):
        for name in ('font-cff.lmt','font-shp.lmt','lpdf-emb.lmt'):
            shutil.copy2(PACKAGE/which/name,base/name)

    fixture = args.output/'fixtures'
    if not args.resume: build(fixture,args.source)
    tex = (fixture/'e2e.tex').read_text()
    baseline,patched = args.output/'baseline',args.output/'patched'
    for folder in (baseline,patched):
        folder.mkdir(exist_ok=True)
        (folder/'e2e.tex').write_text(tex)
    if not args.resume:
        install('original');make('baseline');invoke(baseline,'e2e.tex')
        install('patched')
        for name in ('font-cff-overlaps.lua','font-cff-overlaps.py'):
            shutil.copy2(PACKAGE/name,base/name)
        (base/'font-cff-overlaps-config.json').write_text(json.dumps({'python':sys.executable}))
        make('patched')
        cold = invoke(patched,'e2e.tex')
    elif args.refresh_helper:
        changed=any((PACKAGE/'patched'/n).read_bytes()!=(base/n).read_bytes()
                    for n in ('font-cff.lmt','font-shp.lmt','lpdf-emb.lmt'))
        if changed:install('patched')
        for name in ('font-cff-overlaps.lua','font-cff-overlaps.py'):
            shutil.copy2(PACKAGE/name,base/name)
        if changed:make('patched-refresh')
        # Preserve legitimate v1 full caches for the promotion regression below.
        legacy=args.scratch/'legacy-v1-cache';legacy.mkdir(exist_ok=True)
        # This is the disposable clone's cache, never the installed cache.
        for cached in (tree/'texmf-cache').rglob('*cff2overlaps*'):
            if cached.is_file():
                if 'cff2overlapsv1' in cached.name:shutil.copy2(cached,legacy/cached.name)
                cached.unlink()
        cold=invoke(patched,'e2e.tex')
    else:
        coldlog=patched/'cold.console.log'
        cold=(coldlog if coldlog.exists() else patched/'e2e.tex.console.log').read_text()
    (patched/'cold.console.log').write_text(cold)
    assert cold.count('helper wall time')==3, 'Expected one helper invocation per axis instance'
    (args.output/'audit.json').write_text(json.dumps(audit(baseline/'e2e.pdf',patched/'e2e.pdf',fixture/'variable.otf'),indent=2)+'\n')
    warm = invoke(patched,'e2e.tex')
    (patched/'warm.console.log').write_text(warm)
    assert 'helper wall time' not in warm, 'Warm font cache unexpectedly called the helper'
    shutil.copy2(fixture/'variable.otf',fixture/'flatten-variable.otf')
    (patched/'flatten.tex').write_text(r'\enabledirectives[fonts.cff.flatten]'+'\n'+tex.replace('/variable.otf','/flatten-variable.otf'))
    flatten = invoke(patched,'flatten.tex')
    assert flatten.count('helper wall time')==3
    (args.output/'flatten-audit.json').write_text(json.dumps(audit(baseline/'e2e.pdf',patched/'flatten.pdf',fixture/'variable.otf'),indent=2)+'\n')
    shutil.copy2(fixture/'variable.otf',fixture/'failure-variable.otf')
    (patched/'failure.tex').write_text(tex.replace('/variable.otf','/failure-variable.otf'))
    badenv = dict(env,CONTEXT_CFF2_OVERLAPS_PYTHON='/nonexistent/cff2-overlap-python')
    before = set((tree/'texmf-cache').rglob('*failurevariable*cff2overlaps*'))
    failure=invoke(patched,'failure.tex',badenv,expect=1)
    (patched/'failure-negative.console.log').write_text(failure)
    after = set((tree/'texmf-cache').rglob('*failurevariable*cff2overlaps*'))
    assert before==after, 'Failed CFF2 conversion poisoned the stream cache'
    recovered=invoke(patched,'failure.tex')
    (patched/'recovery.console.log').write_text(recovered)
    assert recovered.count('helper wall time')==3
    (args.output/'recovery-audit.json').write_text(json.dumps(audit(baseline/'e2e.pdf',patched/'failure.pdf',fixture/'variable.otf'),indent=2)+'\n')
    for name in ('static-cff1.otf','static-ttf.ttf'):
        shutil.copy2(fixture/name,fixture/('cold-'+name))
    controls = r'\starttext'+''.join(r'{\definedfont[file:%s at 30pt]AUV\char"2A01}\par'%(Path('../fixtures')/name)
                                    for name in ('cold-static-cff1.otf','cold-static-ttf.ttf'))+r'\stoptext'
    (patched/'controls.tex').write_text(controls)
    invoke(patched,'controls.tex',badenv)
    # One font/axis location used across documents. Newly requested glyphs must
    # extend the cache without reprocessing or losing already corrected ones.
    shutil.copy2(fixture/'variable.otf',fixture/'increment-variable.otf')
    header=r'\definefontfeature[increment][default][axis={wdth=95,wght=360,opsz=5},wipemath=no]'+ '\n'+r'\starttext{\definedfont[file:../fixtures/increment-variable.otf*increment at 30pt]'
    tail=r'}\stoptext'
    incremental=[]
    for label,letters,expected in [('first','U',[2]),('second','V',[1]),('both','UV',[])]:
        filename='increment-'+label+'.tex'
        (patched/filename).write_text(header+letters+tail)
        log=invoke(patched,filename)
        counts=list(map(int,re.findall(r'resolved (\d+) glyphs',log)))
        assert counts==expected, f'Incremental {label} helper glyph counts {counts}, expected {expected}'
        incremental.append({'stage':label,'helper_glyph_counts':counts})
    def subset(name):
        fs,_=read_pdf(patched/(name+'.pdf'))
        return next(f['glyphs'] for f in fs if f['family'].startswith('CFF2OverlapFixture'))
    u,v,both=(subset('increment-'+x) for x in ('first','second','both'))
    assert u['cid00001'].value==both['cid00001'].value
    assert v['cid00001'].value==both['cid00002'].value
    generic=r'\ctxlua{local d=fonts.handlers.otf.loadstreamdata(fonts.hashes.identifiers[font.current()]); assert(d.cff2complete,"generic caller did not receive a complete font")}'
    (patched/'increment-generic.tex').write_text(header+generic+'UV'+tail)
    log=invoke(patched,'increment-generic.tex')
    from fontTools.ttLib import TTFont
    glyphcount=TTFont(fixture/'variable.otf')['maxp'].numGlyphs
    counts=list(map(int,re.findall(r'resolved (\d+) glyphs',log)))
    assert counts==[glyphcount-3], f'Generic caller did not fill only missing glyphs: {counts}'
    incremental.append({'stage':'generic-all','helper_glyph_counts':counts})
    # The full cache must also cover a subsequent partial consumer.
    log=invoke(patched,'increment-both.tex')
    assert 'helper wall time' not in log
    (args.output/'incremental-audit.json').write_text(json.dumps({'passed':True,'stages':incremental,
         'cached_U_and_V_outlines_unchanged':True,'partial_after_generic_helper_calls':0},indent=2)+'\n')
    legacy=args.scratch/'legacy-v1-cache'
    promotion='not available in this clone; covered by mocked cache regression'
    previous=list(legacy.glob('variableotf-*cff2overlapsv1*')) if legacy.exists() else []
    if previous:
        cachefiles=list((tree/'texmf-cache').rglob('variableotf-*cff2overlapsv2*'))
        assert cachefiles,'No v2 source-font caches found before promotion test'
        directory=cachefiles[0].parent
        for cached in cachefiles:cached.unlink()
        for cached in previous:shutil.copy2(cached,directory/cached.name)
        log=invoke(patched,'e2e.tex')
        (patched/'v1-promotion.console.log').write_text(log)
        assert 'helper wall time' not in log,'Valid v1 full cache was not promoted without processing'
        (args.output/'v1-promotion-audit.json').write_text(json.dumps(audit(baseline/'e2e.pdf',patched/'e2e.pdf',fixture/'variable.otf'),indent=2)+'\n')
        promotion='passed: existing complete v1 caches promoted without helper calls'
    (args.output/'run-summary.json').write_text(json.dumps({'passed':True,'cold_helper_calls':3,'warm_helper_calls':0,
        'flatten_helper_calls':3,'negative_helper_failure':'nonzero exit, no stream cache entry',
        'recovery_helper_calls':3,'cff1_ttf_without_helper':'passed','isolated_tree':str(tree),
        'helper_sha256':hashlib.sha256((base/'font-cff-overlaps.py').read_bytes()).hexdigest(),
        'incremental_cache':'U then V then UV, generic completion then UV: passed',
        'v1_promotion':promotion},indent=2)+'\n')
    print(args.output/'run-summary.json')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tree',type=Path,required=True,help='Read-only input ConTeXt tex directory')
    p.add_argument('--scratch',type=Path,required=True,help='New directory for the private tree/cache')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--source',type=Path,required=True,help='CFF2 OTF supplying the fixture outlines')
    p.add_argument('--resume',action='store_true',help='Resume an existing completed cold run after an audit/harness correction')
    p.add_argument('--refresh-helper',action='store_true',help='With --resume: copy latest helper and clear only disposable CFF2 stream caches')
    a=p.parse_args()
    a.tree=a.tree.resolve();a.scratch=a.scratch.resolve();a.output=a.output.resolve();a.source=a.source.resolve()
    run(a)
