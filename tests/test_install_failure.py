"""在临时目录模拟安装故障，确认不会留下可被误用的半成品。"""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_workbench import installer


class InstallFailureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dest = Path(self.temp.name)

    def test_partial_copy_failure_then_retry(self):
        def broken_copy(source, target, **kwargs):
            target.mkdir()
            (target / "partial.txt").write_text("partial", encoding="utf-8")
            raise OSError("simulated disk error")
        with patch.object(installer.shutil, "copytree", side_effect=broken_copy):
            with self.assertRaises(OSError):
                installer.install(self.dest)
        self.assertEqual(list(self.dest.iterdir()), [])
        self.assertTrue((installer.install(self.dest) / "SKILL.md").is_file())

    def test_concurrent_installer_refused(self):
        copy = installer.shutil.copytree
        def outer(source, target, **kwargs):
            with self.assertRaises(FileExistsError):
                installer.install(self.dest)
            with patch.object(installer.shutil, "copytree", copy):
                return copy(source, target, **kwargs)
        with patch.object(installer.shutil, "copytree", side_effect=outer):
            self.assertTrue(installer.install(self.dest).exists())

    def test_target_created_during_copy_preserved(self):
        copy = installer.shutil.copytree
        def interference(source, target, **kwargs):
            existing = self.dest / "research-workbench"
            existing.mkdir(exist_ok=True)
            (existing / "user.txt").write_text("keep", encoding="utf-8")
            with patch.object(installer.shutil, "copytree", copy):
                return copy(source, target, **kwargs)
        with patch.object(installer.shutil, "copytree", side_effect=interference):
            with self.assertRaises(FileExistsError):
                installer.install(self.dest)
        self.assertEqual((self.dest / "research-workbench/user.txt").read_text(), "keep")
        self.assertEqual(len(list(self.dest.iterdir())), 1)

    def test_publish_failure_cleans_staging(self):
        with patch.object(Path, "rename", side_effect=OSError("publish failed")):
            with self.assertRaises(OSError):
                installer.install(self.dest)
        self.assertEqual(list(self.dest.iterdir()), [])
