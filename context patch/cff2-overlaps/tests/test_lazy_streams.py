"""Run actual patched font-shp with disposable sfnt files and mock I/O caches.

Only the expensive parser is stubbed, to expose exactly which actual glyph IDs
it is asked to correct. No installed ConTeXt source or cache is modified.
"""
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest

PACKAGE=Path(__file__).parents[1]
MTXRUN=shutil.which('mtxrun')

@unittest.skipUnless(MTXRUN,'mtxrun unavailable')
class LazyStreamsTests(unittest.TestCase):
    def test_lazy_cache_growth_generic_fallback_v1_promotion_and_controls(self):
        with tempfile.TemporaryDirectory(prefix='cff2-lazy-test-') as tmp:
            root=Path(tmp)
            for name in ('subset.otf','legacy.otf','failed.otf'):
                (root/name).write_bytes(b'OTTO'+struct.pack('>HHHH',1,0,0,0)+b'CFF2'+struct.pack('>III',0,0,0))
            (root/'control.otf').write_bytes(b'OTTO'+struct.pack('>HHHH',1,0,0,0)+b'CFF '+struct.pack('>III',0,0,0))
            script=root/'exercise.lua'
            script.write_text('local root='+json.dumps(str(root))+'\nlocal packagepath='+json.dumps(str(PACKAGE.resolve()))+'\n'+r'''
local M=dofile(packagepath..'/font-cff-overlaps.lua')
local stores,calls,fail={}, {}, false
containers={
 define=function(_,name) stores[name]=stores[name] or {};return stores[name] end,
 read=function(cache,key) return cache[key] end,
 write=function(cache,key,data) cache[key]=data end,
}
local readers={helpers={cleanname=function(s) return (s:gsub('[^%w]','')):lower() end}}
readers.cff2overlapmodule=function() return M end
readers.loadshapes=function(filename,sub,instance,streams,hints)
 assert(streams==true)
 local request=M.requested
 local copied={};if request then for gid in next,request do copied[gid]=true end end
 calls[#calls+1]={requested=request and copied or false,filename=filename}
 if fail then error('injected parser failure') end
 local glyphs={}
 for gid=0,5 do glyphs[gid]={stream=(not request or request[gid]) and ('fixed'..gid) or ('raw'..gid)} end
 return {glyphs=glyphs,fontheader={units=1240},names={family='fake'},format='opentype'}
end
fonts={handlers={otf={version=3.158,readers=readers},afm={},pfb={}},hashes={identifiers={}}}
local function reload() dofile(packagepath..'/patched/font-shp.lmt') end
local function font(name)
 return {properties={filename=root..'/'..name},shared={rawdata={metadata={subfontindex=0}}},characters={}}
end
local function details(indices,used,descriptions)
 return {indices=indices,used=used or {},rawdata={descriptions=descriptions or {}}}
end
local function exactset(t,expected)
 local remaining={};for _,gid in ipairs(expected) do remaining[gid]=true end
 for gid in next,t do assert(remaining[gid],'unexpected gid '..gid);remaining[gid]=nil end
 assert(not next(remaining),'missing requested gid')
end
reload()
local f=font('subset.otf')
local a=fonts.handlers.otf.loadstreamdata(f,details({[2]=1}))
assert(#calls==1);exactset(calls[1].requested,{0,2})
assert(a.streams[2]=='fixed2' and a.streams[3]=='raw3')
assert(not a.cff2complete and a.cff2resolved[0] and a.cff2resolved[2] and not a.cff2resolved[3])
assert(M.requested==nil)
-- Growing the subset parses/corrects only the missing glyph. Fresh raw glyph2
-- must not overwrite the already-corrected persistent/in-memory stream.
local b=fonts.handlers.otf.loadstreamdata(f,details({[3]=1}))
assert(#calls==2);exactset(calls[2].requested,{3})
assert(b.streams[2]=='fixed2' and b.streams[3]=='fixed3')
fonts.handlers.otf.loadstreamdata(f,details({[2]=1,[3]=2}));assert(#calls==2)
-- A fresh module instance simulates a later process reading the persistent cache.
reload();local c=fonts.handlers.otf.loadstreamdata(f,details({[2]=1,[3]=2}));assert(#calls==2)
-- An unspecified subset is a generic consumer, and must see a fully corrected
-- font. It resolves all still-missing IDs and remembers completeness.
local all=fonts.handlers.otf.loadstreamdata(f)
assert(#calls==3);exactset(calls[3].requested,{1,4,5});assert(all.cff2complete)
for gid=0,5 do assert(all.streams[gid]=='fixed'..gid and all.cff2resolved[gid]) end
fonts.handlers.otf.loadstreamdata(f);assert(#calls==3)
-- Duplicate-index semantics match collectindices, without allocating through
-- or removing the original 'used' table's metatable.
local mt={__index=function() error('used lookup allocated a new CID') end}
local used=setmetatable({[1001]=true},mt)
local selected=M.selection(details({[1001]=1},used,{a={index=1001,dupindex=2},b={index=1002,dupindex=3}}))
exactset(selected,{0,2});assert(getmetatable(used)==mt)
exactset(M.selection(details({[1001]=1},{},{a={index=1001,dupindex=2}})),{0,1001})
-- v1 was always a complete correction. It is promoted without parsing and
-- without modifying the legacy cache object (or invalidating old undo caches).
local lf=font('legacy.otf');local attr=lfs.attributes(lf.properties.filename)
local old={time=attr.modification,size=attr.size,streams={}}
for gid=0,5 do old.streams[gid]='legacy-fixed'..gid end
stores.streams['legacyotf-0-0-cff2overlapsv1']=old
local promoted=fonts.handlers.otf.loadstreamdata(lf,details({[4]=1}))
assert(#calls==3 and promoted.cff2complete and promoted.streams[4]=='legacy-fixed4')
assert(old.cff2complete==nil and old.cff2resolved==nil)
assert(stores.streams['legacyotf-0-0-cff2overlapsv2']==promoted)
-- Non-CFF2 follows the original all-stream path and original cache key.
local control=fonts.handlers.otf.loadstreamdata(font('control.otf'),details({[1]=1}))
assert(#calls==4 and calls[4].requested==false and not control.cff2resolved)
assert(stores.streams['controlotf-0-0-0']==control)
-- A changed source file must invalidate even a complete in-memory/v1 cache.
local append=assert(io.open(lf.properties.filename,'ab'));append:write('changed');append:close()
local changed=fonts.handlers.otf.loadstreamdata(lf,details({[4]=1}))
assert(#calls==5);exactset(calls[5].requested,{0,4});assert(not changed.cff2complete)
-- If parsing fails, restore scoped selection, retain earlier corrected cache,
-- and do not publish partially regenerated data. Retrying can still succeed.
local ff=font('failed.otf');fonts.handlers.otf.loadstreamdata(ff,details({[1]=1}));assert(#calls==6)
fail=true
local ok=pcall(fonts.handlers.otf.loadstreamdata,ff,details({[2]=1}))
assert(not ok and M.requested==nil and #calls==7)
local cached=stores.streams['failedotf-0-0-cff2overlapsv2']
assert(cached.cff2resolved[1] and not cached.cff2resolved[2] and cached.streams[1]=='fixed1')
fail=false
local retried=fonts.handlers.otf.loadstreamdata(ff,details({[2]=1}));assert(#calls==8)
assert(retried.streams[1]=='fixed1' and retried.streams[2]=='fixed2')
-- Unknown requested IDs must never be marked resolved, even when an earlier
-- cache says the real font is complete. Reject before publishing a new cache.
assert(not M.covers({cff2complete=true,streams={}}, {[99]=true}))
local before_unknown=stores.streams['subsetotf-0-0-cff2overlapsv2']
local unknown_ok=pcall(fonts.handlers.otf.loadstreamdata,f,details({[99]=1}))
assert(not unknown_ok and M.requested==nil)
assert(stores.streams['subsetotf-0-0-cff2overlapsv2']==before_unknown)
assert(not before_unknown.cff2resolved[99])
assert(not pcall(M.merge,nil,{streams={}}, {[99]=true},false))
-- Nested scoped requests restore their caller even on errors.
local outer={[91]=true};M.requested=outer
assert(not pcall(M.withrequested,{[92]=true},function() error('nested') end))
assert(M.requested==outer);M.requested=nil
print('lazy cache / growth / generic all / v1 promotion / dupindex / controls / source invalidation / failure assertions passed')
''')
            run=subprocess.run([MTXRUN,'--script',str(script)],capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            self.assertIn('assertions passed',run.stdout)

if __name__=='__main__':unittest.main()
