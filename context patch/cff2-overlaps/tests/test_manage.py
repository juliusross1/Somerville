"""Installer transactions use a disposable tree; never touch installed ConTeXt."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('manage',Path(__file__).parents[1]/'manage.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.pkg=self.root/'patch';self.tree=self.root/'tree'
        self.base=self.tree/'texmf-context/tex/context/base/mkxl';self.base.mkdir(parents=True)
        self.fmt=self.tree/'texmf-cache/luametatex-cache/context/test/formats/luametatex';self.fmt.mkdir(parents=True)
        (self.fmt/'cont-en.fmt').write_bytes(b'previous fmt');(self.fmt/'cont-en.lui').write_bytes(b'previous lui')
        (self.pkg/'original').mkdir(parents=True);(self.pkg/'patched').mkdir()
        for name in m.SOURCE_FILES:
            (self.base/name).write_text('original '+name)
            (self.pkg/'original'/name).write_text('original '+name)
            (self.pkg/'patched'/name).write_text('patched '+name)
        for name in m.SUPPORT_FILES[:2]:(self.pkg/name).write_text('support '+name)
        self.exe=self.tree/'texmf-osx-arm64/bin/context';self.exe.parent.mkdir(parents=True);self.exe.touch()
        self.py=self.root/'python';self.py.touch()
        self.args=SimpleNamespace(context_tree=self.tree,python=self.py)
        self.addCleanup(patch.stopall)
        patch.object(m,'PACKAGE',self.pkg).start();patch.object(m,'STATE',self.pkg/'active-install.json').start()
        self.run=patch.object(m.subprocess,'run',side_effect=self.build).start()
        self.before=self.snapshot()
    def snapshot(self):
        return {str(p.relative_to(self.tree)):p.read_bytes() for p in self.tree.rglob('*') if p.is_file()}
    def build(self,cmd,**kwargs):
        if cmd[0]==str(self.py):return subprocess.CompletedProcess(cmd,0)
        (self.fmt/'cont-en.fmt').write_bytes(b'new fmt')
        (self.fmt/'cont-en.lui').write_bytes(b'new lui')
        (self.fmt/'cont-en.log').write_text('new companion')
        return subprocess.CompletedProcess(cmd,0)
    def test_apply_undo_exact(self):
        m.apply(self.args)
        self.assertEqual((self.base/'font-cff.lmt').read_text(),'patched font-cff.lmt')
        m.undo(self.args);self.assertEqual(self.snapshot(),self.before);self.assertFalse(m.STATE.exists())
    def test_baseline_mismatch_no_mutation(self):
        (self.base/'font-cff.lmt').write_text('user change');before=self.snapshot()
        with self.assertRaisesRegex(RuntimeError,'Baseline mismatch'):m.apply(self.args)
        self.assertEqual(self.snapshot(),before);self.assertFalse(m.STATE.exists())
    def test_existing_support_no_mutation(self):
        (self.base/'font-cff-overlaps.lua').write_text('user change');before=self.snapshot()
        with self.assertRaisesRegex(RuntimeError,'already exists'):m.apply(self.args)
        self.assertEqual(self.snapshot(),before)
    def test_failed_build_removes_new_companions(self):
        def fail(cmd,**kwargs):
            self.build(cmd,**kwargs)
            if cmd[0]!=str(self.py):raise subprocess.CalledProcessError(1,cmd)
        self.run.side_effect=fail
        with self.assertRaises(subprocess.CalledProcessError):m.apply(self.args)
        self.assertEqual(self.snapshot(),self.before);self.assertFalse(m.STATE.exists())
    def test_noop_build_rejected(self):
        self.run.side_effect=lambda cmd,**kwargs:subprocess.CompletedProcess(cmd,0)
        with self.assertRaisesRegex(RuntimeError,'did not update'):m.apply(self.args)
        self.assertEqual(self.snapshot(),self.before);self.assertFalse(m.STATE.exists())
    def test_undo_refuses_user_change(self):
        m.apply(self.args);(self.base/'font-cff.lmt').write_text('later edit');before=self.snapshot()
        with self.assertRaisesRegex(RuntimeError,'Changed since'):m.undo(self.args)
        self.assertEqual(self.snapshot(),before);self.assertTrue(m.STATE.exists())
    def test_undo_refuses_corrupt_backup(self):
        m.apply(self.args);manifest=json.loads(m.STATE.read_text())
        Path(manifest['files'][0]['backup']).write_text('corrupt')
        before=self.snapshot()
        with self.assertRaisesRegex(RuntimeError,'Backup checksum'):m.undo(self.args)
        self.assertEqual(self.snapshot(),before)
    def test_undo_recoverable_after_copy_failure(self):
        m.apply(self.args);copy=shutil.copy2
        def fail(src,dest,*a,**kw):
            if Path(dest).name=='font-cff.lmt':raise OSError('injected restore failure')
            return copy(src,dest,*a,**kw)
        with patch.object(m.shutil,'copy2',side_effect=fail):
            with self.assertRaises(OSError):m.undo(self.args)
        self.assertEqual(json.loads(m.STATE.read_text())['status'],'undo-incomplete')
        m.undo(self.args);self.assertEqual(self.snapshot(),self.before)
    def test_failed_apply_recovery_after_rollback_copy_failure(self):
        copy=shutil.copy2
        def fail_build(cmd,**kwargs):
            self.build(cmd,**kwargs)
            if cmd[0]!=str(self.py):raise subprocess.CalledProcessError(1,cmd)
        def fail_restore(src,dest,*a,**kw):
            if Path(src).parent.parent.name=='backups' and Path(dest).name=='font-cff.lmt':
                raise OSError('injected rollback failure')
            return copy(src,dest,*a,**kw)
        self.run.side_effect=fail_build
        with patch.object(m.shutil,'copy2',side_effect=fail_restore):
            with self.assertRaises(OSError):m.apply(self.args)
        self.assertEqual(json.loads(m.STATE.read_text())['status'],'rollback-incomplete')
        m.undo(self.args);self.assertEqual(self.snapshot(),self.before)

    def test_apply_refuses_second_application(self):
        m.apply(self.args);before=self.snapshot()
        with self.assertRaisesRegex(RuntimeError,'already recorded'):m.apply(self.args)
        self.assertEqual(self.snapshot(),before)

    def install_v1(self):
        with patch.object(m,'SOURCE_FILES',('font-cff.lmt','font-shp.lmt')):
            m.apply(self.args)
        for name in m.SOURCE_FILES:
            (self.pkg/'patched'/name).write_text('revision two '+name)
        (self.pkg/'font-cff-overlaps.lua').write_text('revision two module')
        return json.loads(m.STATE.read_text())

    def test_upgrade_retains_original_undo_baseline(self):
        old=self.install_v1()
        m.upgrade(self.args)
        manifest=json.loads(m.STATE.read_text())
        self.assertEqual(manifest['revision'],2)
        self.assertEqual(manifest['backup'],old['backup'])
        self.assertEqual((self.base/'lpdf-emb.lmt').read_text(),'revision two lpdf-emb.lmt')
        m.undo(self.args)
        self.assertEqual(self.snapshot(),self.before)

    def test_upgrade_failed_build_restores_previous_revision(self):
        old=self.install_v1();before=self.snapshot()
        def fail(cmd,**kwargs):
            self.build(cmd,**kwargs)
            if cmd[0]!=str(self.py):
                (self.fmt/'cont-en.extra').write_text('failed companion')
                raise subprocess.CalledProcessError(1,cmd)
        self.run.side_effect=fail
        with self.assertRaises(subprocess.CalledProcessError):m.upgrade(self.args)
        self.assertEqual(self.snapshot(),before)
        self.assertEqual(json.loads(m.STATE.read_text()),old)

    def test_upgrade_refuses_changed_previous_revision(self):
        self.install_v1();(self.base/'font-cff.lmt').write_text('user edit');before=self.snapshot()
        with self.assertRaisesRegex(RuntimeError,'Changed since'):m.upgrade(self.args)
        self.assertEqual(self.snapshot(),before)

    def test_upgrade_refuses_changed_new_source(self):
        self.install_v1();(self.base/'lpdf-emb.lmt').write_text('user edit');before=self.snapshot()
        with self.assertRaisesRegex(RuntimeError,'Baseline mismatch'):m.upgrade(self.args)
        self.assertEqual(self.snapshot(),before)

    def test_upgrade_noop_format_restores_previous_revision(self):
        old=self.install_v1();before=self.snapshot()
        self.run.side_effect=lambda cmd,**kwargs:subprocess.CompletedProcess(cmd,0)
        with self.assertRaisesRegex(RuntimeError,'did not update'):m.upgrade(self.args)
        self.assertEqual(self.snapshot(),before)
        self.assertEqual(json.loads(m.STATE.read_text()),old)

    def test_upgrade_incomplete_rollback_can_undo_original(self):
        self.install_v1();copy=shutil.copy2
        def fail_build(cmd,**kwargs):
            self.build(cmd,**kwargs)
            if cmd[0]!=str(self.py):raise subprocess.CalledProcessError(1,cmd)
        def fail_restore(src,dest,*a,**kw):
            if Path(src).parent.name.startswith('upgrade-') and Path(dest).name=='font-cff.lmt':
                raise OSError('injected upgrade rollback failure')
            return copy(src,dest,*a,**kw)
        self.run.side_effect=fail_build
        with patch.object(m.shutil,'copy2',side_effect=fail_restore):
            with self.assertRaises(OSError):m.upgrade(self.args)
        self.assertEqual(json.loads(m.STATE.read_text())['status'],'rollback-incomplete')
        m.undo(self.args)
        self.assertEqual(self.snapshot(),self.before)

    def test_upgrade_failure_preserves_preexisting_untracked_companion(self):
        self.install_v1();extra=self.fmt/'cont-en.extra';extra.write_text('later user companion')
        before=self.snapshot()
        def fail_build(cmd,**kwargs):
            self.build(cmd,**kwargs)
            if cmd[0]!=str(self.py):
                extra.write_text('build overwrite')
                raise subprocess.CalledProcessError(1,cmd)
        self.run.side_effect=fail_build
        with self.assertRaises(subprocess.CalledProcessError):m.upgrade(self.args)
        self.assertEqual(self.snapshot(),before)

    def test_upgrade_undo_preserves_preexisting_untracked_companion(self):
        self.install_v1();extra=self.fmt/'cont-en.extra';extra.write_text('later user companion')
        def build(cmd,**kwargs):
            result=self.build(cmd,**kwargs)
            if cmd[0]!=str(self.py):extra.write_text('build overwrite')
            return result
        self.run.side_effect=build
        m.upgrade(self.args);m.undo(self.args)
        expected=dict(self.before)
        expected[str(extra.relative_to(self.tree))]=b'later user companion'
        self.assertEqual(self.snapshot(),expected)

if __name__=='__main__':unittest.main()
