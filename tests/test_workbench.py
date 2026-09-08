import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills/research-workbench/scripts/workbench.py"
sys.path.insert(0, str(SCRIPT.parent))


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


wb = module("workbench", SCRIPT)
installer = module("installer", REPO / "scripts/install.py")


class WorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "中文 workbench"
        wb.initialize(self.root, "演示课题")
        self.data = {"kind": "progress", "status": "计划中", "title": "基线", "body": "准备实验"}

    def test_init_refuses_overwrite(self):
        old = (self.root / "config.json").read_bytes()
        with self.assertRaises(FileExistsError):
            wb.initialize(self.root, "另一个项目")
        self.assertEqual(old, (self.root / "config.json").read_bytes())

    def test_record_and_projection(self):
        identifier = wb.record(self.root, self.data)
        self.assertIn(identifier, (self.root / "WORKLOG.md").read_text(encoding="utf-8"))
        self.assertEqual(wb.audit(self.root)["stale_views"], [])

    def test_revision_preserves_history(self):
        first = wb.record(self.root, self.data)
        original = (self.root / "events" / (first + ".json")).read_bytes()
        wb.record(self.root, dict(self.data, supersedes=first, body="已改计划"))
        _, rows = wb.load(self.root)
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(wb.current(rows)), 1)
        self.assertEqual(original, (self.root / "events" / (first + ".json")).read_bytes())
        with self.assertRaises(ValueError):
            wb.record(self.root, dict(self.data, supersedes=first))

    def test_invalid_inputs_do_not_write(self):
        invalid = [[], {}, dict(self.data, status="完成"), dict(self.data, status="已确认"),
                   dict(self.data, evidence="wrong"), dict(self.data, title=""),
                   dict(self.data, kind="checkpoint"), dict(self.data, extra=1),
                   dict(self.data, supersedes="missing"), dict(self.data, paper={})]
        for data in invalid:
            with self.subTest(data=data), self.assertRaises(ValueError):
                wb.record(self.root, data)
        self.assertEqual(list((self.root / "events").glob("*.json")), [])

    def test_paper_dual_output_same_source(self):
        paper = {"source": "虚构材料", "reading_basis": "abstract", "summary": "摘要信息", "limitations": "无全文"}
        identifier = wb.record(self.root, dict(self.data, kind="paper", paper=paper))
        note = wb.read_json(self.root / "notes" / (identifier + ".json"))
        self.assertEqual(note["record"]["paper"], paper)
        markdown = (self.root / "notes" / (identifier + ".md")).read_text(encoding="utf-8")
        self.assertIn("abstract", markdown)
        self.assertIn("未由工具确认", markdown)
        with self.assertRaises(ValueError):
            wb.record(self.root, dict(self.data, kind="paper", paper=dict(paper, reading_basis="read")))

    def test_checkpoint_resume(self):
        wb.record(self.root, dict(self.data, kind="checkpoint", next_step="检查数据"))
        result = subprocess.run([sys.executable, "-X", "utf8", str(SCRIPT), "resume", "--root", str(self.root)],
                                capture_output=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("检查数据", result.stdout)

    def test_manual_notes_preserved(self):
        target = self.root / "PERSONAL_NOTES.md"
        target.write_text("我的手写记录", encoding="utf-8")
        wb.record(self.root, self.data)
        self.assertEqual(target.read_text(encoding="utf-8"), "我的手写记录")

    def test_stale_view_detect_and_rebuild(self):
        (self.root / "CURRENT_STATUS.md").write_text("edited", encoding="utf-8")
        self.assertIn("CURRENT_STATUS.md", wb.audit(self.root)["stale_views"])
        wb.render(self.root)
        self.assertEqual(wb.audit(self.root)["stale_views"], [])

    def test_atomic_failure_keeps_original(self):
        target = self.root / "config.json"
        old = target.read_bytes()
        with patch.object(wb.os, "replace", side_effect=OSError("simulated")), self.assertRaises(OSError):
            wb.atomic_write(target, "broken")
        self.assertEqual(old, target.read_bytes())
        self.assertEqual(list(self.root.glob(".rwa-*")), [])

    def test_render_failure_keeps_saved_event(self):
        with patch.object(wb, "render", side_effect=OSError("simulated")), self.assertRaisesRegex(ValueError, "记录已保存"):
            wb.record(self.root, self.data)
        self.assertEqual(len(wb.load(self.root)[1]), 1)
        self.assertFalse((self.root / ".write.lock").exists())
        wb.render(self.root)
        self.assertEqual(wb.audit(self.root)["stale_views"], [])

    def test_lock_conflict_refuses_write(self):
        with wb.locked(self.root), self.assertRaises(ValueError):
            wb.record(self.root, self.data)
        self.assertEqual(len(wb.load(self.root)[1]), 0)

    def test_path_escape_rejected(self):
        with self.assertRaises(ValueError):
            wb.bounded(self.root, "../outside.txt")

    def test_symlink_escape_rejected(self):
        target = self.base / "outside"
        target.mkdir()
        try:
            (self.root / "notes").symlink_to(target, target_is_directory=True)
        except OSError:
            self.skipTest("OS does not permit creating symlinks")
        with self.assertRaises(ValueError):
            wb.bounded(self.root, "notes/escaped.md")

    def test_bad_event_reported(self):
        (self.root / "events/bad.json").write_text("{}", encoding="utf-8")
        with self.assertRaises(ValueError):
            wb.audit(self.root)

    def test_install_self_contained_and_no_overwrite(self):
        target = installer.install(self.base / "skills")
        self.assertTrue((target / "SKILL.md").is_file())
        with self.assertRaises(FileExistsError):
            installer.install(self.base / "skills")
        demo = self.base / "fresh"
        result = subprocess.run([sys.executable, "-X", "utf8", str(target / "scripts/workbench.py"),
                                 "init", "--root", str(demo), "--name", "独立安装测试"],
                                capture_output=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(wb.audit(demo)["events"], 0)

    def test_cli_bom_input_search_and_error_code(self):
        input_file = self.base / "record.json"
        input_file.write_text(json.dumps(self.data, ensure_ascii=False), encoding="utf-8-sig")
        base = [sys.executable, "-X", "utf8", str(SCRIPT)]
        result = subprocess.run(base + ["record", "--root", str(self.root), "--input", str(input_file)], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = subprocess.run(base + ["search", "--root", str(self.root), "--query", "基线"], capture_output=True, encoding="utf-8")
        self.assertIn("基线", result.stdout)
        result = subprocess.run(base + ["audit", "--root", str(self.base / "missing")], capture_output=True)
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
