"""Prove the production helper needs Python + skia-pathops, not FontTools."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HELPER=Path(__file__).parents[1]/'font-cff-overlaps.py'
BLOCKER='''
import importlib.abc,sys
class BlockFontTools(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname=='fontTools' or fullname.startswith('fontTools.'):
            raise ModuleNotFoundError('FontTools deliberately unavailable: '+fullname)
sys.meta_path.insert(0,BlockFontTools())
'''

def rect(x,y,w,h,reverse=False):
    points=[(x,y),(x+w,y),(x+w,y+h),(x,y+h)]
    if reverse:points.reverse()
    return [[*p,'m' if i==0 else 'l'] for i,p in enumerate(points)]

class NoFontToolsTests(unittest.TestCase):
    def test_module_load_and_membership_without_fonttools(self):
        script=BLOCKER+'''
import importlib.util
spec=importlib.util.spec_from_file_location('helper',sys.argv[1]);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
shape=[[0,0,'m'],[0,100,100,100,100,0,'c'],[100,-10,'l'],[0,-10,'l']]
assert h.robust_point_inside(shape,(50,74.875))
assert not h.robust_point_inside(shape,(-1,75))
assert h.resolve_segments([])==([],False)
assert not any(n=='fontTools' or n.startswith('fontTools.') for n in sys.modules)
'''
        run=subprocess.run([sys.executable,'-c',script,str(HELPER)],capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
    def test_real_cli_batch_without_fonttools(self):
        ring=rect(0,0,100,100)+rect(15,15,70,70,True)+rect(40,0,20,100)+rect(0,40,100,20)
        ovals=[[0,0,'m'],[0,100,100,100,100,0,'c'],[100,-100,0,-100,0,0,'c'],[50,0,'m'],[50,100,150,100,150,0,'c'],[150,-100,50,-100,50,0,'c']]
        request={'protocol':1,'glyphs':[{'id':0,'segments':[]},{'id':1,'segments':rect(0,0,100,100)}, {'id':2,'segments':ring},{'id':3,'segments':ovals}]}
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'input.json';dest=Path(d)/'output.json';source.write_text(json.dumps(request))
            script=BLOCKER+'''
import runpy
helper=sys.argv[1];sys.argv=sys.argv[1:]
runpy.run_path(helper,run_name='__main__')
'''
            run=subprocess.run([sys.executable,'-c',script,str(HELPER),str(source),str(dest)],capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            result=json.loads(dest.read_text());glyphs=result['glyphs']
            self.assertEqual(len(glyphs),4)
            self.assertFalse(glyphs[0]['changed']);self.assertEqual(glyphs[0]['segments'],[])
            self.assertFalse(glyphs[1]['changed'])
            self.assertTrue(glyphs[2]['changed']);self.assertEqual(sum(s[-1]=='m' for s in glyphs[2]['segments']),5)
            self.assertTrue(glyphs[3]['changed']);self.assertTrue(any(s[-1]=='c' for s in glyphs[3]['segments']))

if __name__=='__main__':unittest.main()
