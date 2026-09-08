import subprocess
import sys
import unittest
import test_workbench

wb = test_workbench.wb


class RelationTests(unittest.TestCase):
    setUp = test_workbench.WorkbenchTests.setUp

    def link(self, target):
        return {"target": target, "relation": "references", "reason": "虚构示例：用于比较基线"}

    def test_forward_and_reverse_queries(self):
        target = wb.record(self.root, self.data)
        source = wb.record(self.root, dict(self.data, kind="task", links=[self.link(target)]))
        rows = wb.load(self.root)[1]
        self.assertEqual(wb.related(rows, target)["incoming"][0]["source"], source)
        self.assertEqual(wb.related(rows, source)["outgoing"][0]["target"], target)
        self.assertEqual(wb.audit(self.root)["stale_views"], [])

    def test_target_revision_does_not_rewrite_old_reference(self):
        target = wb.record(self.root, self.data)
        wb.record(self.root, dict(self.data, links=[self.link(target)]))
        latest = wb.record(self.root, dict(self.data, supersedes=target))
        graph = wb.relationship_graph(wb.load(self.root)[1])
        old = next(node for node in graph["nodes"] if node["id"] == target)
        self.assertFalse(old["is_current"])
        self.assertEqual(old["latest_id"], latest)
        self.assertEqual(graph["edges"][0]["target"], target)
        self.assertIn(latest, (self.root / "RELATIONS.md").read_text(encoding="utf-8"))

    def test_source_revision_can_remove_link_without_erasing_history(self):
        target = wb.record(self.root, self.data)
        source = wb.record(self.root, dict(self.data, links=[self.link(target)]))
        wb.record(self.root, dict(self.data, supersedes=source))
        self.assertEqual(wb.relationship_graph(wb.load(self.root)[1])["edges"], [])
        original = wb.read_json(self.root / "events" / (source + ".json"))
        self.assertEqual(original["record"]["links"][0]["target"], target)

    def test_invalid_and_dangling_links_do_not_write(self):
        target = wb.record(self.root, self.data)
        for links in ("bad", [{}], [self.link("bad")], [self.link("0" * 32)],
                      [self.link(target), self.link(target)], [dict(self.link(target), relation="proves")]):
            with self.subTest(links=links), self.assertRaises(ValueError):
                wb.record(self.root, dict(self.data, links=links))
        self.assertEqual(len(wb.load(self.root)[1]), 1)

    def test_backup_restore_preserves_graph(self):
        target = wb.record(self.root, self.data)
        wb.record(self.root, dict(self.data, links=[self.link(target)]))
        archive = self.base / "backup.json"
        wb.backup(self.root, archive)
        restored = self.base / "restored"
        wb.restore(archive, restored)
        self.assertEqual(wb.relationship_graph(wb.load(self.root)[1]), wb.relationship_graph(wb.load(restored)[1]))

    def test_cli_related_and_missing_id(self):
        target = wb.record(self.root, self.data)
        base = [sys.executable, "-X", "utf8", str(test_workbench.SCRIPT), "related", "--root", str(self.root), "--id"]
        result = subprocess.run(base + [target], capture_output=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(wb.json.loads(result.stdout)["id"], target)
        result = subprocess.run(base + ["missing"], capture_output=True)
        self.assertEqual(result.returncode, 2)

    def test_paper_note_links_resolve_from_notes_directory(self):
        target = wb.record(self.root, self.data)
        paper = dict(source="虚构", reading_basis="abstract", summary="测试", limitations="不可引用")
        source = wb.record(self.root, dict(self.data, kind="paper", paper=paper, links=[self.link(target)]))
        content = (self.root / "notes" / (source + ".md")).read_text(encoding="utf-8")
        self.assertIn("../events/" + target + ".json", content)
