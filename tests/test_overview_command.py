"""按需总览只更新派生页面，保留人工文件、原始记录和失败前的旧页面。"""
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import test_workbench as helpers

wb = helpers.wb


class OverviewCommandTests(unittest.TestCase):
    setUp = helpers.WorkbenchTests.setUp

    def snapshot(self):
        return {path.relative_to(self.root).as_posix(): path.read_bytes()
                for path in self.root.rglob("*") if path.is_file()}

    def test_overview_is_optional_and_does_not_rewrite_records_or_manual(self):
        identifier = wb.record(self.root, dict(self.data, kind="checkpoint", next_step="查看虚构数据"))
        self.assertFalse((self.root / "OVERVIEW.html").exists())
        before = self.snapshot()
        result = wb.overview(self.root)
        after = self.snapshot()
        self.assertEqual(result["output"], "OVERVIEW.html")
        self.assertEqual(result["current_records"], 1)
        self.assertEqual(before, {name: value for name, value in after.items() if name != "OVERVIEW.html"})
        self.assertIn("events/" + identifier + ".json", after["OVERVIEW.html"].decode("utf-8"))
        self.assertEqual(wb.audit(self.root)["stale_views"], [])

    def test_regular_render_and_record_do_not_refresh_the_snapshot(self):
        wb.overview(self.root)
        previous = (self.root / "OVERVIEW.html").read_bytes()
        wb.record(self.root, self.data)
        wb.render(self.root)
        self.assertEqual(previous, (self.root / "OVERVIEW.html").read_bytes())
        self.assertEqual(wb.overview(self.root)["current_records"], 1)
        self.assertNotEqual(previous, (self.root / "OVERVIEW.html").read_bytes())

    def test_same_name_manual_html_is_preserved(self):
        output = self.root / "OVERVIEW.html"
        output.write_bytes(b"<html>hand-written overview</html>")
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "不是本工具生成"):
            wb.overview(self.root)
        self.assertEqual(before, self.snapshot())

    def test_existing_lock_is_preserved(self):
        with wb.locked(self.root):
            before = self.snapshot()
            with self.assertRaisesRegex(ValueError, "正在写入"):
                wb.overview(self.root)
            self.assertEqual(before, self.snapshot())
        self.assertFalse((self.root / "OVERVIEW.html").exists())

    def test_atomic_publish_failure_preserves_previous_snapshot(self):
        wb.overview(self.root)
        before = self.snapshot()
        with patch.object(wb.os, "replace", side_effect=OSError("simulated publish failure")):
            with self.assertRaises(OSError):
                wb.overview(self.root)
        self.assertEqual(before, self.snapshot())
        self.assertFalse(list(self.root.glob(".rwa-*")))

    def test_overview_is_excluded_from_backup_and_can_be_regenerated(self):
        wb.record(self.root, self.data)
        wb.overview(self.root)
        archive = self.base / "backup.json"
        wb.backup(self.root, archive)
        self.assertNotIn("OVERVIEW.html", wb.read_json(archive)["files"])
        restored = self.base / "restored"
        wb.restore(archive, restored)
        self.assertFalse((restored / "OVERVIEW.html").exists())
        wb.overview(restored)
        self.assertTrue((restored / "OVERVIEW.html").is_file())
        self.assertEqual(wb.load(self.root), wb.load(restored))

    def test_cli_reports_relative_page_path(self):
        with patch.object(sys, "stdout", new_callable=io.StringIO) as stream:
            code = wb.main(["overview", "--root", str(self.root)])
        report = json.loads(stream.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(report["output"], "OVERVIEW.html")
        self.assertNotIn(str(self.root), stream.getvalue())

    def test_overview_symlink_outside_workbench_is_rejected(self):
        outside = self.base / "outside.html"
        outside.write_bytes(b"do not overwrite")
        try:
            (self.root / "OVERVIEW.html").symlink_to(outside)
        except OSError:
            self.skipTest("OS does not permit creating symlinks")
        with self.assertRaisesRegex(ValueError, "越出工作台边界"):
            wb.overview(self.root)
        self.assertEqual(outside.read_bytes(), b"do not overwrite")


if __name__ == "__main__":
    unittest.main()
