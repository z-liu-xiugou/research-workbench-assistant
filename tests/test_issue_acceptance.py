"""全部使用临时目录及虚构内容，检验 v0.1 Issue 的行为约束。"""
import json
from pathlib import Path
from unittest.mock import patch
import unittest
import test_workbench
from test_workbench import wb, module, REPO

scanner = module("public_scanner", REPO / "scripts/check_public_tree.py")


class IssueAcceptanceTests(unittest.TestCase):
    setUp = test_workbench.WorkbenchTests.setUp

    def test_schema_catalog_matches_runtime(self):
        directory = REPO / "skills/research-workbench/references/schemas"
        record_schema = wb.read_json(directory / "record-v2.schema.json")
        self.assertEqual(record_schema["properties"]["kind"]["enum"], list(wb.KINDS))
        self.assertEqual(record_schema["properties"]["status"]["enum"], list(wb.STATUSES))
        self.assertEqual(wb.read_json(directory / "event-v2.schema.json")["properties"]["schema_version"]["const"], 2)
        self.assertEqual(wb.read_json(directory / "config-v1.schema.json")["properties"]["schema_version"]["const"], 1)

    def test_all_domains_and_examples_validate(self):
        examples = wb.read_json(REPO / "examples/record-v2-examples.json")
        for data in examples:
            wb.record(self.root, data)
        self.assertTrue({"fact", "task", "decision", "issue", "experiment", "artifact"} <= {r["kind"] for r in examples})
        self.assertEqual(wb.audit(self.root)["evidence_warnings"], [])

    def test_config_version_and_unknown_fields(self):
        for config in ({"schema_version": True, "name": "演示"}, {"schema_version": 2, "name": "演示"},
                       {"schema_version": 1, "name": "演示", "private_path": "hidden"}):
            with self.assertRaises(ValueError):
                wb.validate_config(config)

    def test_active_statuses_require_evidence(self):
        for status in ("已确认", "进行中"):
            with self.assertRaises(ValueError):
                wb.record(self.root, dict(self.data, status=status))
        self.assertEqual(wb.load(self.root)[1], [])

    def test_invalid_evidence_does_not_append(self):
        for ref in ("unlocated claim", "file:missing.txt", "file:../escape.txt", "file:C:/private.txt", "event:" + "a" * 32,
                    "https://", "https://user:password@example.org", "doi:invalid"):
            with self.subTest(ref=ref), self.assertRaises(ValueError):
                wb.record(self.root, dict(self.data, status="进行中", evidence=[ref]))
        self.assertEqual(wb.load(self.root)[1], [])

    def test_ai_promotion_requires_explicit_confirmation_and_preserves_history(self):
        original = wb.record(self.root, dict(self.data, kind="fact", status="AI建议"))
        path = self.root / "events" / (original + ".json")
        before = path.read_bytes()
        promoted = dict(self.data, kind="fact", status="已确认", supersedes=original, evidence=["file:PERSONAL_NOTES.md"])
        with self.assertRaisesRegex(ValueError, "confirmation"):
            wb.record(self.root, promoted)
        identifier = wb.record(self.root, dict(promoted, confirmation={"by": "user", "reference": "虚构测试：用户确认此演示事实"}))
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(wb.current(wb.load(self.root)[1])[0]["id"], identifier)

    def test_event_evidence_and_missing_file_audit(self):
        original = wb.record(self.root, self.data)
        wb.record(self.root, dict(self.data, status="进行中", evidence=["event:" + original, "file:PERSONAL_NOTES.md", "https://example.org/evidence"]))
        (self.root / "PERSONAL_NOTES.md").unlink()
        self.assertEqual(len(wb.audit(self.root)["evidence_warnings"]), 1)
        wb.render(self.root)  # 证据移走不应使原始历史无法读取或恢复。

    def test_legacy_history_readable_but_not_silently_upgraded(self):
        identifier = wb.record(self.root, self.data)
        path = self.root / "events" / (identifier + ".json")
        row = wb.read_json(path)
        row["schema_version"] = 1
        row["record"]["status"] = "进行中"
        wb.atomic_write(path, wb.encode(row))
        before = path.read_bytes()
        wb.render(self.root)
        self.assertEqual(len(wb.audit(self.root)["evidence_warnings"]), 1)
        self.assertEqual(before, path.read_bytes())
        with self.assertRaises(ValueError):
            wb.record(self.root, dict(row["record"], supersedes=identifier))
        wb.record(self.root, dict(row["record"], supersedes=identifier, evidence=["file:PROJECT_MANUAL.md"]))
        self.assertEqual(wb.audit(self.root)["evidence_warnings"], [])
        self.assertEqual(before, path.read_bytes())

    def test_all_views_rebuild_without_touching_events(self):
        first = wb.record(self.root, dict(self.data, kind="decision", title="旧决策"))
        second = wb.record(self.root, dict(self.data, kind="decision", title="新决策", supersedes=first))
        wb.record(self.root, dict(self.data, kind="issue", title="待处理问题"))
        config, rows = wb.load(self.root)
        expected = wb.views(config, rows)
        originals = {p: p.read_bytes() for p in (self.root / "events").glob("*.json")}
        for name in expected:
            (self.root / name).unlink()
        wb.render(self.root)
        for name, content in expected.items():
            self.assertEqual((self.root / name).read_text(encoding="utf-8"), content)
        self.assertNotIn(first, expected["DECISIONS_AND_ISSUES.md"])
        self.assertIn(second, expected["CURRENT_STATUS.md"])
        self.assertIn(first, expected["WORKLOG.md"])
        for path, content in originals.items():
            self.assertEqual(path.read_bytes(), content)

    def test_event_replace_failure_has_no_partial_record(self):
        with patch.object(wb.os, "replace", side_effect=OSError("synthetic failure")), self.assertRaises(OSError):
            wb.record(self.root, self.data)
        self.assertEqual(list((self.root / "events").iterdir()), [])
        self.assertFalse((self.root / ".write.lock").exists())

    def test_resume_reads_only_checkpoint(self):
        wb.record(self.root, dict(self.data, kind="checkpoint", next_step="处理虚构数据"))
        real_open = Path.open
        opened = []
        def tracked_open(path, *args, **kwargs):
            opened.append(path.name)
            return real_open(path, *args, **kwargs)
        with patch.object(Path, "open", tracked_open), patch.object(wb, "load", side_effect=AssertionError("must not scan")):
            report = wb.resume(self.root)
        self.assertEqual(opened, ["ACTIVE_CONTEXT.md"])
        self.assertEqual(report["mode"], "lightweight")
        self.assertEqual(report["next_reads"], [])

    def test_resume_review_triggers(self):
        self.assertEqual(wb.resume(self.root)["reason"], "missing_checkpoint")
        wb.record(self.root, dict(self.data, kind="checkpoint", next_step="处理数据"))
        for reason in wb.REVIEW_REASONS:
            report = wb.resume(self.root, reason)
            self.assertEqual(report["mode"], "review_required")
            self.assertEqual(report["reason"], reason)
        with self.assertRaises(ValueError):
            wb.resume(self.root, "new_chat")
        (self.root / "ACTIVE_CONTEXT.md").unlink()
        self.assertEqual(wb.resume(self.root)["reason"], "missing_checkpoint")

    def test_resume_oversized_checkpoint_is_bounded(self):
        wb.atomic_write(self.root / "ACTIVE_CONTEXT.md", "x" * 20000)
        report = wb.resume(self.root)
        self.assertEqual(report["reason"], "checkpoint_conflict")
        self.assertEqual(len(report["checkpoint"]), 16000)

    def test_known_secret_patterns_and_no_value_leak(self):
        tokens = ["gh" + "p_" + "a" * 36, "sk" + "-proj-" + "b" * 40,
                  "AK" + "IA" + "A" * 16, "-----BEGIN " + "PRIVATE KEY-----",
                  "C:" + "/Users/fictional/private.txt"]
        for token in tokens:
            findings = scanner.inspect("fixture.txt", token)
            self.assertTrue(findings)
            self.assertNotIn(token, json.dumps(findings))
        self.assertFalse(scanner.inspect("README.md", "https://example.org A fictional example without credentials"))

    def test_public_tracked_tree_has_no_known_secrets(self):
        self.assertEqual(scanner.scan(REPO), [])

    def test_initialized_records_gitignored(self):
        import subprocess
        subprocess.run(["git", "init", str(self.root)], check=True, capture_output=True)
        result = subprocess.run(["git", "check-ignore", "config.json", "PERSONAL_NOTES.md", "events/example.json"],
                                cwd=self.root, capture_output=True, check=True)
        self.assertEqual(len(result.stdout.splitlines()), 3)
