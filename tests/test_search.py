"""本地检索的输出边界与历史版本回归；不发送联网查询。"""
import contextlib
import io
import json
import unittest
import test_workbench
from test_workbench import wb


class SearchTests(unittest.TestCase):
    setUp = test_workbench.WorkbenchTests.setUp

    def test_default_page_is_bounded_and_search_is_read_only(self):
        for i in range(12):
            wb.record(self.root, dict(self.data, title="主题" + str(i), body="长正文" * 1000))
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        rows = wb.load(self.root)[1]
        page = wb.search_records(rows, "主题")
        self.assertEqual(page["total"], 12)
        self.assertEqual(len(page["items"]), 10)
        self.assertEqual(page["next_offset"], 10)
        self.assertTrue(all(len(item["summary"]) <= 240 for item in page["items"]))
        tail = wb.search_records(rows, "主题", offset=10)
        self.assertEqual(len(tail["items"]), 2)
        self.assertIsNone(tail["next_offset"])
        self.assertFalse({x["id"] for x in page["items"]} & {x["id"] for x in tail["items"]})
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_title_priority_casefold_and_filters(self):
        title_hit = wb.record(self.root, dict(self.data, title="Baseline", kind="experiment"))
        wb.record(self.root, dict(self.data, body="baseline"))
        wb.record(self.root, dict(self.data, title="baseline 候选", status="候选方案"))
        rows = wb.load(self.root)[1]
        self.assertEqual(wb.search_records(rows, " BASELINE ")["items"][1]["id"], title_hit)
        page = wb.search_records(rows, "baseline", kind="experiment", status="计划中")
        self.assertEqual([x["id"] for x in page["items"]], [title_hit])

    def test_current_search_and_exact_historical_show(self):
        old = wb.record(self.root, dict(self.data, title="旧标题"))
        new = wb.record(self.root, dict(self.data, supersedes=old, title="新标题"))
        newest = wb.record(self.root, dict(self.data, supersedes=new, title="最终标题"))
        rows = wb.load(self.root)[1]
        self.assertEqual(wb.search_records(rows, "旧标题")["total"], 0)
        result = wb.show_record(rows, old)
        self.assertEqual(result["event"]["record"]["title"], "旧标题")
        self.assertFalse(result["is_current"])
        self.assertEqual(result["latest_id"], newest)
        self.assertTrue(wb.show_record(rows, newest)["is_current"])

    def test_empty_results_and_validation(self):
        self.assertEqual(wb.search_records([], "没有")["items"], [])
        for kwargs in ({"query": " "}, {"query": "x", "limit": 0}, {"query": "x", "limit": 51},
                       {"query": "x", "offset": -1}, {"query": "x", "status": "invalid"}):
            with self.assertRaises(ValueError):
                wb.search_records([], **kwargs)
        for identifier in ("../config.json", "a" * 32):
            with self.assertRaises(ValueError):
                wb.show_record([], identifier)

    def test_full_page_and_cli_roundtrip(self):
        identifier = wb.record(self.root, self.data)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(wb.main(["search", "--root", str(self.root), "--query", "基线", "--full"]), 0)
        page = json.loads(output.getvalue())
        self.assertEqual(page["items"][0]["record"], self.data)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(wb.main(["show", "--root", str(self.root), "--id", identifier]), 0)
        self.assertEqual(json.loads(output.getvalue())["event"]["record"], self.data)

    def test_metadata_match_does_not_dump_paper(self):
        paper = {"source": "虚构", "reading_basis": "abstract", "summary": "特定关键词" * 1000, "limitations": "未读全文"}
        wb.record(self.root, dict(self.data, kind="paper", paper=paper))
        result = wb.search_records(wb.load(self.root)[1], "特定关键词", kind="paper")
        self.assertEqual(result["total"], 1)
        self.assertNotIn("paper", result["items"][0])
        self.assertLess(len(wb.encode(result)), 1500)
