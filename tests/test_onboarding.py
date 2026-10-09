import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import test_workbench as helpers

wb = helpers.wb
installer = helpers.installer
TEMPLATE = helpers.SCRIPT.parent.parent / "references/project-manual-template.md"


class OnboardingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.first = self.base / "fictional-literature"
        self.second = self.base / "fictional-empirical"

    def configure(self, root, name, language, detail, target):
        wb.initialize(root, name)
        manual = root / "PROJECT_MANUAL.md"
        original = manual.read_text(encoding="utf-8")
        configured = original.replace("- 输出语言：待定", "- 输出语言：" + language) \
            .replace("- 输出详略：待定", "- 输出详略：" + detail) \
            .replace("- 当前目标：待定", "- 当前目标：" + target)
        manual.write_text(configured, encoding="utf-8", newline="\n")
        return manual

    def run_cli(self, skill, *args):
        result = subprocess.run([sys.executable, "-B", "-X", "utf8", str(skill / "scripts/workbench.py"), *args],
                                capture_output=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def test_new_project_initializes_full_template_before_records(self):
        wb.initialize(self.first, "虚构项目A")
        manual = self.first / "PROJECT_MANUAL.md"
        self.assertEqual(manual.read_bytes(), TEMPLATE.read_bytes())
        config_before = (self.first / "config.json").read_bytes()
        manual_before = manual.read_bytes()
        identifier = wb.record(self.first, {"kind": "checkpoint", "status": "计划中", "title": "只设置下一步",
                                           "body": "选题待定，先整理练习资料。", "next_step": "核对资料位置"})
        resumed = wb.resume(self.first)
        self.assertIn(identifier, resumed["checkpoint"])
        self.assertEqual(resumed["mode"], "lightweight")
        self.assertEqual(resumed["project_preferences"]["path"], "PROJECT_MANUAL.md")
        self.assertTrue(resumed["project_preferences"]["optional"])
        self.assertEqual(manual_before, manual.read_bytes())
        self.assertEqual(config_before, (self.first / "config.json").read_bytes())
        self.assertIn("- 研究问题：待定", manual.read_text(encoding="utf-8"))

    def test_missing_installed_template_fails_before_creating_project(self):
        skill = installer.install(self.base / "incomplete-installation")
        (skill / "references/project-manual-template.md").unlink()
        result = subprocess.run([sys.executable, "-B", "-X", "utf8", str(skill / "scripts/workbench.py"),
                                 "init", "--root", str(self.first), "--name", "虚构未创建项目"],
                                capture_output=True, encoding="utf-8")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.first.exists())

    def test_two_projects_use_same_installation_without_manual_or_history_leak(self):
        skill = installer.install(self.base / "installed-skills")
        first_manual = self.configure(self.first, "虚构文献项目", "中文", "简洁", "比较虚构步道体验概念")
        second_manual = self.configure(self.second, "虚构实证项目", "英文", "详细", "核对虚构材料甲的测量流程")
        originals = {self.first: first_manual.read_bytes(), self.second: second_manual.read_bytes()}
        for index, root in enumerate((self.first, self.second)):
            payload = root / "input.json"
            payload.write_text(wb.encode({"kind": "checkpoint", "status": "计划中", "title": "下一步" + str(index),
                                         "body": "仍在准备虚构练习。", "next_step": "检查本项目资料"}), encoding="utf-8")
            self.run_cli(skill, "record", "--root", str(root), "--input", str(payload))
            result = self.run_cli(skill, "resume", "--root", str(root))
            resumed = json.loads(result.stdout)
            self.assertEqual(resumed["project_preferences"]["path"], "PROJECT_MANUAL.md")
            self.assertIn("下一步" + str(index), resumed["checkpoint"])
            self.assertNotIn("下一步" + str(1 - index), resumed["checkpoint"])
            selected = root / resumed["project_preferences"]["path"]
            self.assertEqual(originals[root], selected.read_bytes())
            expected = "中文" if root == self.first else "英文"
            self.assertIn("- 输出语言：" + expected, selected.read_text(encoding="utf-8"))
        self.assertEqual(originals[self.first], first_manual.read_bytes())
        self.assertEqual(originals[self.second], second_manual.read_bytes())
        self.assertEqual(len(wb.load(self.first)[1]), 1)
        self.assertEqual(len(wb.load(self.second)[1]), 1)

    def test_missing_or_partial_legacy_manual_does_not_block_record_or_resume(self):
        for index, root in enumerate((self.first, self.second)):
            with self.subTest(manual="missing" if index == 0 else "partial"):
                wb.initialize(root, "虚构旧项目")
                manual = root / "PROJECT_MANUAL.md"
                if index == 0:
                    manual.unlink()
                    before = None
                else:
                    before = "# 旧的手写约定\r\n\r\n- 输出语言：中文\r\n这是用户保留的自由段落。\r\n".encode("utf-8")
                    manual.write_bytes(before)
                legacy_id = "a" * 32
                legacy = root / "events" / (legacy_id + ".json")
                legacy.write_text(wb.encode({"id": legacy_id, "created_at": "2026-01-01T00:00:00+00:00", "schema_version": 1,
                                             "record": {"kind": "progress", "status": "计划中", "title": "旧版虚构练习",
                                                        "body": "旧版事件原字节保留。"}}), encoding="utf-8")
                legacy_before = legacy.read_bytes()
                config_before = (root / "config.json").read_bytes()
                identifier = wb.record(root, {"kind": "checkpoint", "status": "计划中", "title": "先记下一步",
                                              "body": "研究范围待定。", "next_step": "补充本次需要的资料"})
                event_before = (root / "events" / (identifier + ".json")).read_bytes()
                result = wb.resume(root)
                self.assertEqual(result["mode"], "lightweight")
                self.assertTrue(result["project_preferences"]["optional"])
                self.assertEqual(config_before, (root / "config.json").read_bytes())
                self.assertEqual(event_before, (root / "events" / (identifier + ".json")).read_bytes())
                self.assertEqual(legacy_before, legacy.read_bytes())
                self.assertEqual(len(wb.load(root)[1]), 2)
                if before is None:
                    self.assertFalse(manual.exists())
                else:
                    self.assertEqual(before, manual.read_bytes())

    def test_modified_preferences_and_free_text_survive_backup_restore_as_bytes(self):
        manual = self.configure(self.first, "虚构项目", "中文", "简洁", "练习资料整理")
        first_id = wb.record(self.first, {"kind": "checkpoint", "status": "计划中", "title": "准备练习",
                                          "body": "题目待定。", "next_step": "核对资料位置"})
        event_before = (self.first / "events" / (first_id + ".json")).read_bytes()
        changed = manual.read_text(encoding="utf-8").replace("- 输出语言：中文", "- 输出语言：英文") \
            .replace("- 输出详略：简洁", "- 输出详略：详细") + "\n用户自由补充：保留这段文字。\n"
        # 同时检查手工文件的 CRLF 保存，不把规范化后的文本误当作原字节。
        manual.write_bytes(changed.replace("\n", "\r\n").encode("utf-8"))
        saved = manual.read_bytes()
        archive = self.base / "snapshot.json"
        wb.backup(self.first, archive)
        payload = wb.read_json(archive)
        self.assertIn("PROJECT_MANUAL.md", payload["files"])
        wb.restore(archive, self.second)
        self.assertEqual(saved, (self.second / "PROJECT_MANUAL.md").read_bytes())
        self.assertEqual(event_before, (self.second / "events" / (first_id + ".json")).read_bytes())
        result = wb.resume(self.second)
        selected = self.second / result["project_preferences"]["path"]
        self.assertIn("- 输出语言：英文", selected.read_text(encoding="utf-8"))
        self.assertIn("- 输出详略：详细", selected.read_text(encoding="utf-8"))
        self.assertEqual(saved, manual.read_bytes())

    def test_reinstall_in_new_location_does_not_modify_project_manual_or_events(self):
        manual = self.configure(self.first, "虚构项目", "中文", "简洁", "整理虚构材料")
        first_id = wb.record(self.first, {"kind": "checkpoint", "status": "计划中", "title": "保存断点",
                                          "body": "题目待定。", "next_step": "继续练习"})
        original = manual.read_bytes()
        history = (self.first / "events" / (first_id + ".json")).read_bytes()
        old = installer.install(self.base / "old-installation")
        with self.assertRaises(FileExistsError):
            installer.install(self.base / "old-installation")
        new = installer.install(self.base / "new-installation")
        self.assertNotEqual(old, new)
        result = self.run_cli(new, "resume", "--root", str(self.first))
        self.assertEqual(json.loads(result.stdout)["mode"], "lightweight")
        wb.render(self.first)
        self.assertEqual(original, manual.read_bytes())
        self.assertEqual(history, (self.first / "events" / (first_id + ".json")).read_bytes())
        fresh = self.base / "new-project-from-new-install"
        self.run_cli(new, "init", "--root", str(fresh), "--name", "另一虚构项目")
        self.assertEqual(TEMPLATE.read_bytes(), (fresh / "PROJECT_MANUAL.md").read_bytes())
        self.assertEqual(original, manual.read_bytes())

    def test_resume_returns_preferences_entry_without_reading_manual_or_events(self):
        self.configure(self.first, "虚构项目", "中文", "简洁", "整理资料")
        wb.record(self.first, {"kind": "checkpoint", "status": "计划中", "title": "断点",
                               "body": "保留待定字段。", "next_step": "核对资料"})
        original_open = Path.open
        opened = []

        def selective_open(path, *args, **kwargs):
            opened.append(path)
            self.assertEqual(path, self.first / "ACTIVE_CONTEXT.md")
            return original_open(path, *args, **kwargs)

        with patch.object(Path, "open", selective_open), \
                patch.object(wb, "load", side_effect=AssertionError("resume must not read event library")):
            result = wb.resume(self.first)
        self.assertEqual(opened, [self.first / "ACTIVE_CONTEXT.md"])
        self.assertEqual(result["project_preferences"]["path"], "PROJECT_MANUAL.md")


if __name__ == "__main__":
    unittest.main()
