import unittest
import test_workbench

wb = test_workbench.wb


class PaperMetadataTests(unittest.TestCase):
    setUp = test_workbench.WorkbenchTests.setUp
    def paper(self, **metadata):
        return dict(self.data, kind="paper", paper=dict(source="虚构测试", reading_basis="abstract",
                    summary="测试", limitations="不可引用", **metadata))

    def test_doi_normalized_without_mutating_input(self):
        data = self.paper(doi="https://doi.org/10.1234/TEST", authors=["示例作者"], year=2026, tags=["基线"])
        identifier = wb.record(self.root, data)
        self.assertEqual(wb.load(self.root)[1][0]["record"]["paper"]["doi"], "10.1234/test")
        self.assertEqual(data["paper"]["doi"], "https://doi.org/10.1234/TEST")
        self.assertIn(identifier, (self.root / "PAPER_INDEX.md").read_text(encoding="utf-8"))
        self.assertIn("示例作者", (self.root / "notes" / (identifier + ".md")).read_text(encoding="utf-8"))

    def test_duplicate_refused_but_revision_allowed(self):
        first = wb.record(self.root, self.paper(doi="10.1234/test"))
        with self.assertRaisesRegex(ValueError, first):
            wb.record(self.root, self.paper(doi="DOI: 10.1234/TEST"))
        self.assertEqual(len(wb.load(self.root)[1]), 1)
        second = wb.record(self.root, dict(self.paper(doi="10.1234/test"), supersedes=first))
        index = (self.root / "PAPER_INDEX.md").read_text(encoding="utf-8")
        self.assertIn(second, index)
        self.assertNotIn(first, index)

    def test_invalid_metadata_rejected(self):
        for metadata in ({"doi": "bad"}, {"authors": "name"}, {"year": True}, {"year": "2026"}, {"tags": [1]}):
            with self.subTest(metadata=metadata), self.assertRaises(ValueError):
                wb.record(self.root, self.paper(**metadata))
        self.assertEqual(wb.load(self.root)[1], [])
