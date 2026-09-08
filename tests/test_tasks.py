import subprocess
import sys
import unittest
import test_workbench

wb = test_workbench.wb


class TaskTests(unittest.TestCase):
    setUp = test_workbench.WorkbenchTests.setUp

    def task(self, state="todo", **fields):
        return dict(self.data, kind="task", task_state=state, **fields)

    def test_completion_preserves_history_and_filters_current(self):
        first = wb.record(self.root, self.task())
        original = (self.root / "events" / (first + ".json")).read_bytes()
        second = wb.record(self.root, self.task("done", supersedes=first, evidence=["虚构测试产物"]))
        rows = wb.load(self.root)[1]
        self.assertEqual(wb.tasks(rows), [])
        self.assertEqual([r["id"] for r in wb.tasks(rows, "done")], [second])
        self.assertEqual(original, (self.root / "events" / (first + ".json")).read_bytes())
        self.assertNotIn(first, (self.root / "TASKS.md").read_text(encoding="utf-8"))
        self.assertIn(first, (self.root / "WORKLOG.md").read_text(encoding="utf-8"))

    def test_cancel_and_reopen(self):
        first = wb.record(self.root, self.task("cancelled"))
        second = wb.record(self.root, self.task("todo", supersedes=first))
        self.assertEqual([r["id"] for r in wb.tasks(wb.load(self.root)[1])], [second])

    def test_legacy_tasks_are_not_assumed_complete(self):
        identifier = wb.record(self.root, dict(self.data, kind="task"))
        self.assertEqual(wb.tasks(wb.load(self.root)[1], "unspecified")[0]["id"], identifier)
        self.assertEqual(len(wb.tasks(wb.load(self.root)[1])), 1)

    def test_invalid_state_and_unsubstantiated_completion(self):
        for data in (self.task("wrong"), self.task("done"), dict(self.data, task_state="todo")):
            with self.subTest(data=data), self.assertRaises(ValueError):
                wb.record(self.root, data)
        self.assertEqual(wb.load(self.root)[1], [])

    def test_resume_is_bounded_and_does_not_embed_papers(self):
        progress = wb.record(self.root, dict(self.data, body="进展" * 10000))
        wb.record(self.root, dict(self.data, kind="checkpoint", body="目标" * 10000, next_step="下一步" * 10000))
        paper = dict(source="虚构", reading_basis="abstract", summary="不可出现在断点的全文" * 10000, limitations="测试")
        wb.record(self.root, dict(self.data, kind="paper", paper=paper))
        active = (self.root / "ACTIVE_CONTEXT.md").read_text(encoding="utf-8")
        self.assertLess(len(active), 3000)
        self.assertNotIn("不可出现在断点的全文", active)
        self.assertIn(progress, active)
        self.assertEqual(wb.audit(self.root)["stale_views"], [])

    def test_tasks_cli_returns_json_array(self):
        wb.record(self.root, self.task("in_progress"))
        result = subprocess.run([sys.executable, "-X", "utf8", str(test_workbench.SCRIPT), "tasks",
                                 "--root", str(self.root)], capture_output=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(wb.json.loads(result.stdout)), 1)
