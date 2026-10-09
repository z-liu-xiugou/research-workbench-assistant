"""离线总览使用实际事件语义；资料中的 HTML 和危险地址不能变成可执行内容。"""
import base64
import copy
from datetime import datetime
import hashlib
from html.parser import HTMLParser
import re
import unittest
from unittest.mock import patch

import test_workbench
import overview


wb = test_workbench.wb
STAMP = "2026-10-09T08:00:00+00:00"


class Page(HTMLParser):
    """按浏览器的 HTML 标签结构检查链接、卡片和实际脚本，而不是只查转义字符串。"""
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.cards = []
        self.links = []
        self.scripts = []
        self.styles = []
        self.csp = ""
        self.words = []
        self.active = None
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append((tag, attrs))
        if tag == "article" and "data-card" in attrs:
            self.cards.append(attrs)
        if tag == "a":
            self.links.append(attrs)
        if tag == "meta" and attrs.get("http-equiv") == "Content-Security-Policy":
            self.csp = attrs["content"]
        if tag in ("script", "style"):
            self.active = tag
            (self.scripts if tag == "script" else self.styles).append("")

    def handle_endtag(self, tag):
        if tag == self.active:
            self.active = None

    def handle_data(self, data):
        if self.active:
            (self.scripts if self.active == "script" else self.styles)[-1] += data
        else:
            self.words.append(data)


class OverviewTests(unittest.TestCase):
    setUp = test_workbench.WorkbenchTests.setUp

    def record(self, **fields):
        return wb.record(self.root, dict(self.data, **fields))

    def render(self, **fields):
        config, rows = wb.load(self.root)
        inputs = dict(current_rows=wb.current(rows), candidate_state=wb.candidates(rows, "all"),
                      relations=wb.relationship_graph(rows), generated_at=STAMP)
        inputs.update(fields)
        return overview.render_overview(config, rows, **inputs)

    def seed_candidates(self):
        raw = [{"DOI": "10.1234/" + state, "title": ["虚构候选 " + state]}
               for state in ("pending", "kept", "excluded", "noted")]
        payload = {"message": {"items": raw, "total-results": 4}}
        with patch("literature.fetch_json", return_value=payload):
            discovery = wb.discover(self.root, "公开的虚构中文检索词")
        for decision in ("kept", "excluded"):
            self.record(kind="candidate_review", candidate={"doi": "10.1234/" + decision,
                        "decision": decision, "reason": "虚构筛选理由 " + decision})
        self.record(kind="candidate_review", candidate={"doi": "10.1234/noted", "decision": "excluded",
                                                       "reason": "保留原筛选决定的虚构测试"})
        note = self.record(kind="paper", title="已有全文依据笔记", paper={"source": "虚构来源",
                           "reading_basis": "full_text", "summary": "虚构笔记摘要", "limitations": "没有人工确认",
                           "doi": "10.1234/noted"})
        return discovery["discovery_id"], note

    def test_empty_project_has_accurate_empty_states_and_no_invented_progress(self):
        source = self.render()
        page = Page(source)
        self.assertTrue(source.startswith(overview.OWNER_MARKER + "\n"))
        self.assertEqual(page.cards, [])
        self.assertEqual(source.count("暂无符合条件的条目。"), 9)
        self.assertIn(STAMP, source)
        self.assertIn("当前任务记录", source)
        self.assertIn("当前笔记事件", source)
        self.assertNotIn("论文完成：", source)
        self.assertNotIn("人工已读：", source)

    def test_latest_current_checkpoint_and_only_five_recent_progress_records(self):
        old = self.record(kind="checkpoint", title="旧断点", next_step="旧下一步")
        latest = self.record(kind="checkpoint", title="中文最新目标", supersedes=old, next_step="下一步检查虚构材料")
        progress = [self.record(title="中文进展 " + str(index)) for index in range(6)]
        source = self.render()
        cards = Page(source).cards
        checkpoints = [card for card in cards if card["data-card"] == "checkpoint"]
        recent = [card["data-record-id"] for card in cards if card["data-card"] == "progress"]
        self.assertEqual([card["data-record-id"] for card in checkpoints], [latest])
        self.assertEqual(recent, progress[-1:0:-1])
        self.assertNotIn("旧断点</h3>", source)
        self.assertIn("events/" + old + ".json", source)  # 修订来源保留。
        self.assertIn("下一步检查虚构材料", source)

    def test_task_execution_states_remain_separate_from_research_status(self):
        identifiers = {}
        for state in ("todo", "in_progress", "done", "cancelled", "unspecified"):
            fields = {} if state == "unspecified" else {"task_state": state}
            if state == "done":
                fields["evidence"] = ["虚构产物"]
            identifiers[state] = self.record(kind="task", title="虚构任务 " + state, **fields)
        source = self.render()
        cards = [card for card in Page(source).cards if card["data-card"] == "tasks"]
        self.assertEqual({card["data-state"]: card["data-record-id"] for card in cards}, identifiers)
        self.assertEqual({card["data-status"] for card in cards}, {"计划中"})
        self.assertIn("执行情况：完成", source)
        self.assertIn("研究状态：计划中", source)
        self.assertIn('<strong>3</strong><span>未关闭任务记录', source)

    def test_candidates_keep_decision_provenance_and_noted_is_not_human_read(self):
        discovery, note = self.seed_candidates()
        source = self.render()
        cards = Page(source).cards
        candidates = [card for card in cards if card["data-card"] == "candidates"]
        self.assertEqual({card["data-state"] for card in candidates}, {"pending", "kept", "excluded", "noted"})
        self.assertEqual(len(candidates), 4)
        self.assertIn("已有同 DOI 的当前笔记，不代表人工已读。", source)
        self.assertIn("筛选决定：排除", source)  # noted 不把之前 excluded 决定抹掉。
        self.assertIn("读取依据：全文", source)
        self.assertIn("字段 reading_basis，不是人工阅读确认", source)
        self.assertIn("events/" + discovery + ".json", source)
        self.assertIn("notes/" + note + ".md", source)
        self.assertIn("最近筛选事件（JSON）", source)
        self.assertIn("作者：未知 · 年份：未知", source)
        self.assertIn('<strong>4</strong><span>候选 DOI 条目', source)
        self.assertIn('<strong>1</strong><span>当前笔记事件', source)

    def test_historical_relation_target_stays_exact_and_new_version_is_separate(self):
        first = self.record(title="原版本虚构依据")
        task = self.record(kind="task", title="依赖旧版本的虚构任务", task_state="todo",
                           links=[{"target": first, "relation": "references", "reason": "保留原依据"}])
        latest = self.record(title="新版虚构依据", supersedes=first)
        source = self.render()
        cards = Page(source).cards
        self.assertNotIn(first, [card.get("data-record-id") for card in cards])
        self.assertIn(task, [card.get("data-record-id") for card in cards])
        self.assertIn("历史目标", source)
        self.assertIn("原引用仍指向历史记录", source)
        self.assertIn('href="events/' + first + '.json"', source)
        self.assertIn('href="events/' + latest + '.json"', source)

    def test_project_and_all_record_fields_render_as_text_not_html_or_handlers(self):
        payload = '</script><img src=x onerror="alert(1)"><svg onload="alert(2)">'
        identifier = self.record(kind="paper", title=payload, body=payload, evidence=[payload],
                                 paper={"source": payload, "reading_basis": "abstract", "summary": payload,
                                        "limitations": payload, "authors": [payload], "tags": [payload]})
        config, rows = wb.load(self.root)
        source = overview.render_overview(dict(config, name=payload + "@@CSP@@"), rows,
                   current_rows=wb.current(rows), candidate_state=[], relations=wb.relationship_graph(rows), generated_at=STAMP)
        page = Page(source)
        self.assertEqual(len(page.scripts), 1)
        self.assertFalse(any(tag in ("img", "svg", "iframe") for tag, _ in page.tags))
        self.assertFalse(any(name.startswith("on") for _, attrs in page.tags for name in attrs))
        self.assertIn(payload, "".join(page.words))
        self.assertNotIn(payload, page.scripts[0])
        self.assertIn("@@CSP@@", "".join(page.words))  # 替换槽位不递归处理用户文字。
        self.assertIn('href="notes/' + identifier + '.md"', source)

    def test_candidate_metadata_and_filter_attributes_are_escaped(self):
        attack = '\" onclick=\"alert(1)\"><script>alert(2)</script>'
        source = self.render(candidate_state=[{"title": attack, "doi": "10.1234/test", "state": attack,
                              "decision": attack, "authors": [attack], "abstract": attack, "query": attack}])
        page = Page(source)
        self.assertEqual(len(page.scripts), 1)
        self.assertEqual(len(page.cards), 1)
        self.assertEqual(page.cards[0]["data-state"], attack)
        self.assertFalse(any(name.startswith("on") for _, attrs in page.tags for name in attrs))
        self.assertIn(attack, "".join(page.words))

    def test_evidence_urls_have_explicit_safe_schemes_and_bounded_local_names(self):
        known = self.record(title="虚构引用对象")
        unsafe = ["javascript:alert(1)", "data:text/html,<script>alert(1)</script>",
                  "file:///private/secret", "file:../outside.txt", "file:events/../../outside.txt",
                  "https://user:password@example.invalid/path", "//example.invalid/path",
                  "https://example.invalid/\nattack", "https:\\example.invalid\\path"]
        safe = ["https://example.invalid/proof?a=1&b=2", "http://example.invalid/source", "doi:10.1234/safe",
                "event:" + known, "file:PROJECT_MANUAL.md"]
        self.record(evidence=unsafe + safe)
        source = self.render()
        hrefs = {item["href"] for item in Page(source).links}
        self.assertFalse(set(unsafe) & hrefs)
        self.assertIn("https://example.invalid/proof?a=1&b=2", hrefs)
        self.assertIn("https://doi.org/10.1234/safe", hrefs)
        self.assertIn("events/" + known + ".json", hrefs)
        self.assertIn("PROJECT_MANUAL.md", hrefs)
        self.assertTrue(all(not value.startswith(("javascript:", "data:", "file:", "../", "//")) for value in hrefs))

    def test_csp_matches_only_inline_resources_and_page_has_no_external_loading(self):
        page = Page(self.render())
        for contents in (page.scripts[0], page.styles[0]):
            digest = base64.b64encode(hashlib.sha256(contents.encode("utf-8")).digest()).decode("ascii")
            self.assertIn("'sha256-" + digest + "'", page.csp)
        self.assertIn("default-src 'none'", page.csp)
        self.assertIn("connect-src 'none'", page.csp)
        self.assertNotIn("unsafe-inline", page.csp)
        self.assertFalse(any("src" in attrs for _, attrs in page.tags))
        self.assertFalse(any(tag == "link" for tag, _ in page.tags))
        self.assertNotRegex(page.scripts[0], r"\b(?:fetch|XMLHttpRequest|WebSocket|innerHTML|eval)\b")
        self.assertIn("textContent", page.scripts[0])
        for selector in ("query", "scope", "task-state", "candidate-state", "research-status", "reset"):
            self.assertTrue(any(attrs.get("id") == selector for _, attrs in page.tags), selector)

    def test_render_does_not_mutate_input_or_existing_history_and_manual_files(self):
        self.record(kind="paper", paper={"source": "虚构", "reading_basis": "metadata", "summary": "元数据笔记",
                                         "limitations": "没有摘要或全文"})
        (self.root / "PERSONAL_NOTES.md").write_bytes("人工笔记\r\n".encode("utf-8"))
        before = {path.relative_to(self.root): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        config, rows = wb.load(self.root)
        inputs = dict(current_rows=wb.current(rows), candidate_state=wb.candidates(rows, "all"),
                      relations=wb.relationship_graph(rows), generated_at=STAMP)
        copied = copy.deepcopy((config, rows, inputs))
        overview.render_overview(config, rows, **inputs)
        self.assertEqual((config, rows, inputs), copied)
        self.assertEqual(before, {path.relative_to(self.root): path.read_bytes() for path in self.root.rglob("*") if path.is_file()})
        self.assertFalse((self.root / "OVERVIEW.html").exists())  # 写入由 CLI 统一负责。

    def test_legacy_optional_fields_display_unknown_and_do_not_invent_task_state(self):
        identifier = self.record(kind="task")
        source = self.render()
        card = next(card for card in Page(source).cards if card["data-record-id"] == identifier)
        self.assertEqual(card["data-state"], "unspecified")
        self.assertIn("未记录证据入口", source)
        self.assertIn("执行情况：状态未指定", source)

    def test_generated_at_requires_timezone_and_normalizes_to_utc(self):
        self.assertIn(STAMP, self.render(generated_at="2026-10-09T16:00:00+08:00"))
        for bad in ("2026-10-09T08:00:00", datetime(2026, 10, 9), "</script>"):
            with self.subTest(value=bad), self.assertRaises(ValueError):
                self.render(generated_at=bad)


if __name__ == "__main__":
    unittest.main()
