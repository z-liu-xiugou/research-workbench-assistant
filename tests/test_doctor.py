import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_workbench as helpers

installer = helpers.installer
wb = helpers.wb


class DoctorTests(unittest.TestCase):
    setUp = helpers.WorkbenchTests.setUp

    def installation(self):
        # 使用安装副本，不把测试临时目录误当作仓库的技能根目录。
        return installer.install(self.base / "private-user-skills")

    def item(self, report, code):
        return next(item for item in report["checks"] if item["code"] == code)

    def snapshot(self):
        return {str(path.relative_to(self.base)): (path.read_bytes(), path.stat().st_mtime_ns)
                for path in self.base.rglob("*") if path.is_file()}

    def test_normal_installation_and_workbench(self):
        report = wb.doctor(self.root, self.installation())
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["exit_code"], 0)
        self.assertTrue(report["read_only"])
        self.assertEqual(self.item(report, "TOOL_VERSION")["target_version"], wb.VERSION)
        self.assertEqual(self.item(report, "WORKBENCH_CONFIG")["status"], "ok")
        # notes 只有实际生成文献笔记时才建立，空工作台不应因此报警。
        self.assertEqual(self.item(report, "NOTES_ACCESS")["status"], "skipped")

    def test_cli_installation_only_uses_running_skill(self):
        skill = self.installation()
        result = subprocess.run([sys.executable, "-B", "-X", "utf8", str(skill / "scripts/workbench.py"), "doctor"],
                                capture_output=True, encoding="utf-8")
        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsNone(report["locations"]["workbench_root"])
        self.assertEqual(self.item(report, "WORKBENCH_NOT_SELECTED")["status"], "skipped")

    def test_missing_literature_does_not_break_json_cli(self):
        skill = self.installation()
        (skill / "scripts/literature.py").unlink()
        result = subprocess.run([sys.executable, "-B", "-X", "utf8", str(skill / "scripts/workbench.py"),
                                 "doctor", "--root", str(self.root)], capture_output=True, encoding="utf-8")
        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(self.item(report, "SKILL_FILES")["missing"], ["scripts/literature.py"])
        self.assertEqual(self.item(report, "WORKBENCH_CONFIG")["status"], "ok")

    def test_missing_core_and_views_are_separate(self):
        skill = self.installation()
        (self.root / "events").rmdir()
        (self.root / "CURRENT_STATUS.md").unlink()
        report = wb.doctor(self.root, skill)
        paths = self.item(report, "WORKBENCH_PATHS")
        self.assertEqual(report["exit_code"], 2)
        self.assertEqual(paths["missing_core"], ["events"])
        self.assertEqual(paths["missing_views"], ["CURRENT_STATUS.md"])

    def test_missing_view_only_is_warning(self):
        skill = self.installation()
        (self.root / "ACTIVE_CONTEXT.md").unlink()
        report = wb.doctor(self.root, skill)
        self.assertEqual(report["exit_code"], 1)
        self.assertEqual(self.item(report, "WORKBENCH_CONFIG")["status"], "ok")

    def test_unwritable_directory_by_static_permission_observation(self):
        skill = self.installation()

        def access(path, mode):
            return not (Path(path) == self.root and mode == wb.os.W_OK)

        with patch.object(wb.os, "access", side_effect=access):
            report = wb.doctor(self.root, skill)
        self.assertEqual(report["exit_code"], 1)
        self.assertEqual(self.item(report, "WORKBENCH_ACCESS")["status"], "warning")
        self.assertIn("静态", self.item(report, "WORKBENCH_ACCESS")["message"])

    def test_unreadable_directory_is_error(self):
        skill = self.installation()
        with patch.object(wb.os, "access", return_value=False):
            report = wb.doctor(self.root, skill)
        self.assertEqual(report["exit_code"], 2)
        self.assertEqual(self.item(report, "WORKBENCH_ACCESS")["status"], "error")

    def test_lock_presence_requires_verification_and_preserves_locks(self):
        skill = self.installation()
        locks = [self.root / ".write.lock", skill.parent / ".research-workbench.install.lock"]
        for path in locks:
            path.write_text("private-lock-content", encoding="utf-8")
        before = self.snapshot()
        report = wb.doctor(self.root, skill)
        self.assertEqual(report["exit_code"], 1)
        for code in ("INSTALL_LOCK", "WORKBENCH_LOCK"):
            item = self.item(report, code)
            self.assertEqual(item["status"], "warning")
            self.assertIn("无法据此判断", item["message"])
            self.assertIn("先核实", item["advice"])
        self.assertNotIn("private-lock-content", wb.encode(report))
        self.assertEqual(before, self.snapshot())

    def test_bad_configuration_keeps_all_checks_and_hides_error_text(self):
        skill = self.installation()
        for content in ('{"private-config-secret":', '{"schema_version": 1, "name": "", "private-config-secret": 7}'):
            with self.subTest(content=content):
                (self.root / "config.json").write_text(content, encoding="utf-8")
                report = wb.doctor(self.root, skill)
                self.assertEqual(report["exit_code"], 2)
                self.assertEqual(self.item(report, "WORKBENCH_CONFIG")["status"], "error")
                self.assertEqual(self.item(report, "WORKBENCH_LOCK")["status"], "ok")
                self.assertNotIn("private-config-secret", wb.encode(report))

    def test_default_redaction_and_explicit_local_paths(self):
        skill = self.installation()
        (self.root / "config.json").write_text(wb.encode({"schema_version": 1, "name": "private-project-secret"}), encoding="utf-8")
        redacted = wb.encode(wb.doctor(self.root, skill))
        for value in (str(self.base), self.root.name, skill.parent.name, "private-project-secret"):
            self.assertNotIn(value, redacted)
        local = wb.doctor(self.root, skill, include_paths=True)
        self.assertFalse(local["redacted"])
        self.assertEqual(local["locations"]["workbench_root"], str(self.root))
        self.assertNotIn("private-project-secret", wb.encode(local))

    def test_failed_check_does_not_prevent_other_results_or_leak_path(self):
        skill = self.installation()
        original = wb.bounded

        def broken(root, relative):
            if root == self.root and relative == "events":
                raise OSError("private-error-secret at " + str(self.root))
            return original(root, relative)

        with patch.object(wb, "bounded", side_effect=broken):
            report = wb.doctor(self.root, skill)
        self.assertEqual(report["exit_code"], 2)
        self.assertEqual(self.item(report, "WORKBENCH_CONFIG")["status"], "ok")
        self.assertEqual(self.item(report, "WORKBENCH_LOCK")["status"], "ok")
        self.assertNotIn("private-error-secret", wb.encode(report))
        self.assertNotIn(str(self.root), wb.encode(report))

    def test_tool_version_is_read_statically_without_execution(self):
        skill = self.installation()
        (skill / "scripts/workbench.py").write_text('VERSION = "9.0.0"\nraise RuntimeError("must not execute")\n', encoding="utf-8")
        report = wb.doctor(self.root, skill)
        self.assertEqual(report["exit_code"], 1)
        self.assertEqual(self.item(report, "TOOL_VERSION")["target_version"], "9.0.0")

    def test_configuration_symlink_escape_is_not_read_or_exposed(self):
        skill = self.installation()
        external = self.base / "private-external-config.json"
        external.write_text('{"private-external-secret": "must not read"}', encoding="utf-8")
        target = self.root / "config.json"
        target.unlink()
        try:
            target.symlink_to(external)
        except OSError:
            self.skipTest("OS does not permit creating symlinks")
        with patch.object(wb, "read_json", wraps=wb.read_json) as read:
            report = wb.doctor(self.root, skill)
        read.assert_not_called()
        self.assertEqual(report["exit_code"], 2)
        self.assertEqual(self.item(report, "WORKBENCH_CONFIG")["status"], "error")
        self.assertNotIn("private-external-secret", wb.encode(report))
        self.assertNotIn(str(external), wb.encode(report))

    def test_doctor_never_writes_or_reads_events_or_rebuilds_views(self):
        skill = self.installation()
        (self.root / "events/private-record.json").write_text("private-research-secret", encoding="utf-8")
        before = self.snapshot()
        original = Path.open

        def read_only(path, mode="r", *args, **kwargs):
            self.assertFalse(any(flag in mode for flag in "wax+"), mode)
            self.assertNotEqual(path.parent, self.root / "events")
            return original(path, mode, *args, **kwargs)

        with patch.object(Path, "open", read_only), \
                patch.object(wb, "load", side_effect=AssertionError("must not read events")), \
                patch.object(wb, "render", side_effect=AssertionError("must not rebuild views")), \
                patch.object(wb, "atomic_write", side_effect=AssertionError("must not write")), \
                patch.object(wb, "locked", side_effect=AssertionError("must not lock")), \
                patch.object(wb.tempfile, "mkstemp", side_effect=AssertionError("must not probe")):
            report = wb.doctor(self.root, skill)
        self.assertEqual(report["exit_code"], 0)
        self.assertNotIn("private-research-secret", wb.encode(report))
        self.assertEqual(before, self.snapshot())

    def test_main_prints_one_parseable_report_with_matching_exit_code(self):
        skill = self.installation()
        (self.root / ".write.lock").touch()
        with patch.object(sys, "stdout", new_callable=io.StringIO) as output:
            exit_code = wb.main(["doctor", "--root", str(self.root), "--skill-dir", str(skill)])
        report = json.loads(output.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(exit_code, report["exit_code"])


if __name__ == "__main__":
    unittest.main()
