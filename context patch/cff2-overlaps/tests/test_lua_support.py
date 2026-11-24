"""Exercise actual Lua support through mtxrun, in disposable directories."""
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

PACKAGE=Path(__file__).parents[1]
MTXRUN=shutil.which('mtxrun')


def sfnt(tag):
    return b'OTTO'+struct.pack('>HHHH',1,0,0,0)+tag+struct.pack('>III',0,0,0)


@unittest.skipUnless(MTXRUN,'mtxrun unavailable')
class LuaSupportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="cff2 Lua ' quoted ");self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        shutil.copy2(PACKAGE/'font-cff-overlaps.lua',self.root/'font-cff-overlaps.lua')
        (self.root/'font-cff-overlaps-config.json').write_text(json.dumps({'python':sys.executable}))
    def lua(self,body,success=True):
        script=self.root/'exercise.lua'
        script.write_text('local root='+json.dumps(str(self.root))+'\nlocal m=dofile(root.."/font-cff-overlaps.lua")\n'+body)
        env=os.environ.copy();env.pop('CONTEXT_CFF2_OVERLAPS_PYTHON',None)
        run=subprocess.run([MTXRUN,'--script',str(script)],capture_output=True,text=True,env=env)
        self.assertEqual(run.returncode,0 if success else 1,run.stdout+run.stderr)
        return run.stdout+run.stderr
    def test_sfnt_and_ttc_faces(self):
        (self.root/'cff1.otf').write_bytes(sfnt(b'CFF '))
        (self.root/'cff2.otf').write_bytes(sfnt(b'CFF2'))
        (self.root/'truncated.otf').write_bytes(b'OTTO')
        # TTC's first face is CFF1, second is CFF2. No outline bytes needed
        # because detection only reads table-directory tags.
        (self.root/'mixed.ttc').write_bytes(b'ttcf'+struct.pack('>II',0x10000,2)+struct.pack('>II',20,48)+sfnt(b'CFF ')+sfnt(b'CFF2'))
        self.lua('''
assert(not m.iscff2(root..'/cff1.otf',0,28,1))
assert(m.iscff2(root..'/cff2.otf',0,28,1))
assert(not m.iscff2(root..'/truncated.otf',0,4,1))
assert(not m.iscff2(root..'/missing.otf',0,0,1))
assert(not m.iscff2(root..'/mixed.ttc',nil,76,1)) -- default first face
assert(not m.iscff2(root..'/mixed.ttc',0,76,1)) -- invalid TTC index
assert(not m.iscff2(root..'/mixed.ttc',1,76,1))
assert(m.iscff2(root..'/mixed.ttc',2,76,1))
assert(not m.iscff2(root..'/mixed.ttc',3,76,1))
assert(not m.iscff2(root..'/mixed.ttc',-1,76,1))
print('sfnt/TTC detection assertions passed')
''')
    def test_missing_helper_fails_instead_of_returning_outlines(self):
        output=self.lua("m.convert({{id=0,segments={}}})",success=False)
        self.assertIn('CFF2 overlap helper failed',output)
        self.assertIn('font-cff-overlaps.py',output)
    def test_malformed_response_rejected(self):
        (self.root/'font-cff-overlaps.py').write_text('import pathlib,sys\npathlib.Path(sys.argv[2]).write_text(\'{"protocol":1,"glyphs":[]}\')\n')
        output=self.lua("m.convert({{id=0,segments={}}})",success=False)
        self.assertIn('glyph count mismatch',output)
    def test_valid_empty_response_and_shellquoted_paths(self):
        (self.root/'font-cff-overlaps.py').write_text('import json,pathlib,sys\ng=json.loads(pathlib.Path(sys.argv[1]).read_text())["glyphs"]\nfor v in g:v["changed"]=False\npathlib.Path(sys.argv[2]).write_text(json.dumps({"protocol":1,"glyphs":g}))\n')
        self.lua('local r=m.convert({{id=0,segments={}}});assert(#r==1 and r[1].changed==false and #r[1].segments==0)')

if __name__=='__main__':unittest.main()
