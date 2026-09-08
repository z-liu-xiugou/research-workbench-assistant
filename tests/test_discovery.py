import io
import json
import subprocess
import sys
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit
import test_workbench
import literature

wb = test_workbench.wb


def raw_item(doi="10.1234/test"):
    return {"DOI": doi, "title": ["<i>虚构</i>检索测试"], "author": [{"given": "Example", "family": "Author"}],
            "container-title": ["虚构刊物"], "published": {"date-parts": [[2024, 1, 1]]},
            "abstract": "<jats:p>虚构摘要 &amp; 不可引用</jats:p>", "type": "journal-article"}


def response(items=None):
    return {"message": {"items": [raw_item()] if items is None else items, "total-results": 100}}


class DiscoveryTests(unittest.TestCase):
    setUp = test_workbench.WorkbenchTests.setUp

    def discover(self, items=None):
        with patch.object(literature, "fetch_json", return_value=response(items)):
            return wb.discover(self.root, "公开示例", limit=10, year_start=2023, year_end=2025)

    def test_query_encoding_and_filter(self):
        with patch.object(literature, "fetch_json", return_value=response()) as fetch:
            batch = literature.search_crossref("风电 & forecasting", 3, 2020, 2025)
        url = fetch.call_args.args[0]
        params = parse_qs(urlsplit(url).query)
        self.assertEqual(params["query.bibliographic"], ["风电 & forecasting"])
        self.assertEqual(params["rows"], ["3"])
        self.assertIn("until-pub-date:2025-12-31", params["filter"][0])
        self.assertEqual(batch["items"][0]["authors"], ["Example Author"])
        self.assertNotIn("<jats", batch["items"][0]["abstract"])
        literature.validate_discovery(batch)

    def test_candidates_are_not_paper_notes(self):
        report = self.discover()
        self.assertEqual(report["added"], 1)
        rows = wb.load(self.root)[1]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["record"]["kind"], "discovery")
        self.assertEqual(wb.candidates(rows)[0]["state"], "pending")
        self.assertFalse((self.root / "notes").exists())
        self.assertEqual(wb.audit(self.root)["stale_views"], [])
        self.assertNotIn("虚构摘要", (self.root / "ACTIVE_CONTEXT.md").read_text(encoding="utf-8"))

    def test_dedupe_within_and_across_batches(self):
        report = self.discover([raw_item(), raw_item("10.1234/TEST")])
        self.assertEqual(report["added"], 1)
        self.assertEqual(report["duplicates"][0]["existing"], "batch")
        again = self.discover()
        self.assertEqual(again["added"], 0)
        self.assertEqual(again["duplicates"][0]["existing"], "candidate")
        self.assertEqual(len(wb.candidates(wb.load(self.root)[1], "all")), 1)
        self.assertEqual(len(wb.load(self.root)[1]), 2)  # 两次检索都留痕。

    def test_dedupe_against_existing_notes(self):
        paper = dict(source="虚构", reading_basis="abstract", summary="笔记", limitations="测试", doi="10.1234/test")
        wb.record(self.root, dict(self.data, kind="paper", paper=paper))
        report = self.discover()
        self.assertEqual(report["added"], 0)
        self.assertEqual(report["duplicates"][0]["existing"], "paper")

    def test_missing_metadata_not_invented_invalid_item_reported(self):
        minimal = {"DOI": "10.1234/minimal", "title": ["仅有题名"]}
        report = self.discover([minimal, {"title": ["没有DOI"]}, {"DOI": "10.1234/notitle"}])
        self.assertEqual(report["added"], 1)
        self.assertEqual(len(report["skipped"]), 2)
        candidate = wb.candidates(wb.load(self.root)[1])[0]
        self.assertEqual(candidate["authors"], [])
        self.assertNotIn("abstract", candidate)
        self.assertNotIn("year", candidate)

    def test_empty_results_are_saved_as_successful_search(self):
        report = self.discover([])
        self.assertEqual(report["added"], 0)
        self.assertEqual(len(wb.load(self.root)[1]), 1)

    def test_network_failure_writes_nothing(self):
        with patch.object(literature, "fetch_json", side_effect=ValueError("429")), self.assertRaises(ValueError):
            wb.discover(self.root, "example")
        self.assertEqual(wb.load(self.root)[1], [])

    def test_invalid_parameters_do_not_request(self):
        for kwargs in ({"query": ""}, {"limit": 0}, {"limit": 51}, {"year_start": 2025, "year_end": 2020}, {"timeout": 0}):
            args = dict(query="example")
            args.update(kwargs)
            with self.subTest(kwargs=kwargs), patch.object(literature, "fetch_json") as fetch, self.assertRaises(ValueError):
                literature.search_crossref(**args)
            fetch.assert_not_called()

    def test_malformed_response_rejected(self):
        for payload in ({}, {"message": {"items": []}}, {"message": {"items": {}, "total-results": 1}}):
            with patch.object(literature, "fetch_json", return_value=payload), self.assertRaises(ValueError):
                wb.discover(self.root, "example")
        self.assertEqual(wb.load(self.root)[1], [])

    def test_review_and_note_handoff(self):
        self.discover()
        review = {"kind": "candidate_review", "status": "待确认", "title": "筛选", "body": "人工筛选测试",
                  "candidate": {"doi": "10.1234/test", "decision": "kept", "reason": "与课题范围相关"}}
        wb.record(self.root, review)
        self.assertEqual(len(wb.candidates(wb.load(self.root)[1], "kept")), 1)
        paper = dict(source="虚构", reading_basis="abstract", summary="阅读摘要后生成的测试笔记", limitations="没有全文", doi="10.1234/test")
        identifier = wb.record(self.root, dict(self.data, kind="paper", paper=paper))
        candidate = wb.candidates(wb.load(self.root)[1], "noted")[0]
        self.assertEqual(candidate["note_id"], identifier)
        self.assertEqual(candidate["decision"], "kept")
        self.assertNotIn("human_read", candidate)

    def test_reopen_excluded_candidate_keeps_history(self):
        self.discover()
        for decision in ("excluded", "pending"):
            wb.record(self.root, {"kind": "candidate_review", "status": "待确认", "title": "筛选", "body": "理由",
                                 "candidate": {"doi": "10.1234/test", "decision": decision, "reason": "更改筛选"}})
        self.assertEqual(len(wb.candidates(wb.load(self.root)[1])), 1)
        self.assertEqual(len(wb.load(self.root)[1]), 3)

    def test_review_unknown_candidate_rejected(self):
        with self.assertRaises(ValueError):
            wb.record(self.root, {"kind": "candidate_review", "status": "待确认", "title": "筛选", "body": "理由",
                                 "candidate": {"doi": "10.1234/missing", "decision": "kept", "reason": "理由"}})

    def test_search_batch_atomic_write_failure(self):
        with patch.object(wb.os, "replace", side_effect=OSError("disk full")), self.assertRaises(OSError):
            self.discover()
        self.assertEqual(wb.load(self.root)[1], [])

    def test_backup_roundtrip_queue(self):
        self.discover()
        archive = self.base / "backup.json"
        wb.backup(self.root, archive)
        restored = self.base / "restored"
        wb.restore(archive, restored)
        self.assertEqual(wb.candidates(wb.load(self.root)[1]), wb.candidates(wb.load(restored)[1]))

    def test_cli_review_and_queue(self):
        self.discover()
        base = [sys.executable, "-X", "utf8", str(test_workbench.SCRIPT)]
        result = subprocess.run(base + ["candidate-review", "--root", str(self.root), "--doi", "10.1234/test",
                                "--decision", "excluded", "--reason", "不符范围"], capture_output=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        result = subprocess.run(base + ["candidates", "--root", str(self.root), "--state", "excluded"], capture_output=True, encoding="utf-8")
        self.assertEqual(len(json.loads(result.stdout)), 1)

    def test_http_limits_errors_and_no_redirect(self):
        errors = [HTTPError("https://api.crossref.org/works", 429, "limit", {"Retry-After": "60"}, None),
                  HTTPError("https://api.crossref.org/works", 503, "down", {}, None), URLError("offline")]
        for error in errors:
            with patch.object(literature, "build_opener") as opener, self.assertRaises(ValueError):
                opener.return_value.open.side_effect = error
                literature.fetch_json(literature.ENDPOINT, 10)
            self.assertEqual(opener.return_value.open.call_count, 1)
        with patch.object(literature, "build_opener") as opener, patch.object(literature, "MAX_RESPONSE", 1), self.assertRaises(ValueError):
            opener.return_value.open.return_value = io.BytesIO(b"{}")
            literature.fetch_json(literature.ENDPOINT, 10)
        self.assertIsNone(literature.NoRedirect().redirect_request(None, None, 302, "redirect", {}, "http://localhost"))
