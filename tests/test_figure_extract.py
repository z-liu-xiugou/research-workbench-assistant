"""虚构 PDF 上验证可观察的提取内容、坐标、复核失效及失败完整性。"""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from figure_fixture import make_demo, write_pdf

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/research-workbench/scripts"
sys.path.insert(0, str(SCRIPTS))
import figure_extract as extractor

HAS_DEPS = all(importlib.util.find_spec(name) for name in ("pdfplumber", "pypdf", "PIL"))


def snapshot(root):
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}


class ScopeValidationTests(unittest.TestCase):
    def test_duplicate_and_path_like_ids_fail_before_writing(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            scope = make_demo(base)
            original = json.loads(scope.read_text(encoding="utf-8"))
            for bad in ("../escape", "/absolute", "A/B", "A\\B", "A:B", "", "x" * 81, "CON", "com1", "LPT9"):
                with self.subTest(bad=bad):
                    value = json.loads(json.dumps(original))
                    value["papers"][0]["ledger_id"] = bad
                    scope.write_text(json.dumps(value), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        extractor.extract(scope, base / "gallery")
                    self.assertFalse((base / "gallery").exists())
            original["papers"].append(dict(original["papers"][0], ledger_id="demo-001"))
            scope.write_text(json.dumps(original), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "重复"):
                extractor.scope_rows(scope)

    def test_missing_optional_dependencies_explains_installation(self):
        original = __import__("builtins").__import__

        def without_pdf(name, *args, **kwargs):
            if name == "pdfplumber":
                raise ImportError("not installed")
            return original(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=without_pdf):
            with self.assertRaisesRegex(ValueError, "requirements-figures"):
                extractor.dependencies()

    def test_directory_publish_rolls_back_old_result(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            target, stage = base / "old", base / "stage"
            target.mkdir()
            stage.mkdir()
            (target / "old.txt").write_text("keep", encoding="utf-8")
            (stage / "new.txt").write_text("new", encoding="utf-8")
            original = extractor.os.replace

            def fail_publication(source, destination):
                if Path(source) == stage:
                    raise OSError("injected publish failure")
                return original(source, destination)

            with patch.object(extractor.os, "replace", side_effect=fail_publication):
                with self.assertRaises(OSError):
                    extractor.publish(stage, target)
            self.assertEqual((target / "old.txt").read_text(encoding="utf-8"), "keep")
            self.assertTrue((stage / "new.txt").is_file())
            self.assertFalse(any(base.glob(".previous-*")))


@unittest.skipUnless(HAS_DEPS, "图库可选依赖未安装；基础功能无需这些依赖")
class FigureExtractionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.scope = make_demo(self.base)
        self.output = self.base / "图库 output & # %"
        self.paper_dir = self.output / "papers/DEMO-001"

    def extract(self, **kwargs):
        report = extractor.extract(self.scope, self.output, **kwargs)
        self.assertTrue(report["ok"], report)
        return report

    def record(self):
        return json.loads((self.paper_dir / "figures.json").read_text(encoding="utf-8"))

    def changes(self, figures):
        path = self.base / "overrides.json"
        path.write_text(json.dumps({"papers": {"DEMO-001": {"figures": figures}}}), encoding="utf-8")
        return path

    def test_english_chinese_candidates_assets_and_original_unchanged(self):
        from PIL import Image
        from pypdf import PdfReader
        source = self.base / "虚构 source & # %.pdf"
        before = source.read_bytes()
        self.assertEqual(self.extract()["figure_count"], 2)
        record = self.record()
        self.assertEqual(source.read_bytes(), before)
        self.assertEqual(record["figures"][1]["caption"], "图 2 虚构结果")
        self.assertFalse(record["coverage"]["page_review_complete"])
        for figure in record["figures"]:
            self.assertEqual(figure["review_status"], "needs_review")
            self.assertIsNone(figure["review_method"])
            with Image.open(self.paper_dir / figure["assets"]["png"]) as image:
                self.assertEqual(image.mode, "RGB")
                self.assertAlmostEqual(image.info["dpi"][0], 300, places=1)
                self.assertGreater(image.width, 1000)
                self.assertGreater(len(image.getcolors(maxcolors=1000000)), 2)
            cropped = PdfReader(self.paper_dir / figure["assets"]["pdf"])
            self.assertEqual(len(cropped.pages), 1)
            self.assertIn(b" re", cropped.pages[0].get_contents().get_data())
            with Image.open(self.paper_dir / figure["assets"]["thumbnail"]) as image:
                self.assertLessEqual(image.width, 480)
                self.assertLessEqual(image.height, 360)
            bbox = figure["source"]["segments"][0]["bbox"]
            self.assertLessEqual(bbox[0], 24, "左侧轴标签必须保留")
            self.assertGreaterEqual(bbox[3], 215, "底部横轴文字必须保留")
            self.assertLessEqual(bbox[1], 48, "图上方图例文字必须保留")
        archived_scope = json.loads((self.output / "scope.json").read_text(encoding="utf-8"))
        self.assertFalse(Path(archived_scope["papers"][0]["pdf_path"]).is_absolute())
        self.assertEqual((self.output / archived_scope["papers"][0]["pdf_path"]).resolve(), source.resolve())

    def test_manual_cross_page_complete_png_and_multi_page_vector_pdf(self):
        from PIL import Image
        from pypdf import PdfReader
        override = self.changes([{"figure_number": "1", "caption": "Manual complete figure",
                                 "segments": [{"page": 1, "bbox": [40, 60, 350, 205]},
                                              {"page": 2, "bbox": [40, 60, 350, 205]}]},
                                {"figure_number": "2", "exclude": True}])
        self.assertEqual(self.extract(overrides_path=override)["figure_count"], 1)
        figure = self.record()["figures"][0]
        self.assertEqual(figure["source"]["pages"], [1, 2])
        self.assertEqual(len(figure["segments"]), 2)
        self.assertEqual(len(PdfReader(self.paper_dir / figure["assets"]["pdf"]).pages), 2)
        with Image.open(self.paper_dir / figure["assets"]["png"]) as image:
            dimensions = image.size
        with Image.open(self.paper_dir / figure["segments"][0]["assets"]["png"]) as first:
            self.assertEqual(dimensions[0], first.width)
            self.assertGreater(dimensions[1], first.height * 2)

    def test_two_column_captions_at_same_height_stay_separate(self):
        write_pdf(self.base / "虚构 source & # %.pdf", pages=1, dual_column=True)
        self.assertEqual(self.extract()["figure_count"], 2)
        left, right = self.record()["figures"]
        self.assertEqual(left["caption"], "Fig. 1 Left panel")
        self.assertEqual(right["caption"], "Fig. 2 Right panel")
        self.assertLessEqual(left["source"]["segments"][0]["bbox"][2], 200)
        self.assertGreaterEqual(right["source"]["segments"][0]["bbox"][0], 200)

    def test_rotation_and_nonzero_cropbox_match_png_and_vector_pdf(self):
        import pdfplumber
        from PIL import Image, ImageChops, ImageStat
        source = self.base / "虚构 source & # %.pdf"
        for rotation in (0, 90, 180, 270):
            for crop in (False, True):
                with self.subTest(rotation=rotation, crop=crop):
                    write_pdf(source, rotate=rotation, crop=crop, pages=1)
                    width, height = ((360, 450) if crop else (400, 500))
                    if rotation in (90, 270):
                        width, height = height, width
                    override = self.changes([{"figure_number": "7", "caption": "Rotation fixture",
                        "segments": [{"page": 1, "bbox": [20, 30, width - 20, height - 30]}]},
                        {"figure_number": "1", "exclude": True}])
                    self.extract(overrides_path=override, dpi=72)
                    figure = self.record()["figures"][0]
                    with Image.open(self.paper_dir / figure["assets"]["png"]) as png:
                        actual = png.convert("RGB")
                    with pdfplumber.open(self.paper_dir / figure["assets"]["pdf"]) as pdf:
                        expected = pdf.pages[0].to_image(resolution=72, antialias=True).original.convert("RGB")
                    self.assertEqual(actual.size, (width - 40, height - 60))
                    self.assertEqual(expected.size, actual.size)
                    self.assertLess(max(ImageStat.Stat(ImageChops.difference(actual, expected)).mean), 2)

    def test_same_source_preserves_review_but_geometry_and_source_changes_revoke_it(self):
        self.extract()
        record = self.record()
        record["figures"][0]["review_status"] = "verified"
        record["figures"][0]["review_method"] = "human"
        record["figures"][0]["annotations"]["summary_zh"] = "人工填写，重提取保留"
        (self.paper_dir / "figures.json").write_text(json.dumps(record), encoding="utf-8")
        self.extract()
        self.assertEqual(self.record()["figures"][0]["review_status"], "verified")
        override = self.changes([{"figure_number": "1", "segments": [{"page": 1, "bbox": [41, 60, 350, 205]}]}])
        self.extract(overrides_path=override)
        changed = self.record()["figures"][0]
        self.assertEqual(changed["review_status"], "needs_review")
        self.assertIsNone(changed["review_method"])
        self.assertEqual(changed["annotations"]["summary_zh"], "人工填写，重提取保留")
        record = self.record()
        record["figures"][0].update(review_status="verified", review_method="ai")
        (self.paper_dir / "figures.json").write_text(json.dumps(record), encoding="utf-8")
        source = self.base / "虚构 source & # %.pdf"
        source.write_bytes(source.read_bytes() + b"\n% source revision\n")
        self.extract(overrides_path=override)
        self.assertEqual(self.record()["figures"][0]["review_status"], "needs_review")

    def test_skip_existing_reuses_assets_but_changed_source_does_not(self):
        self.extract()
        path = self.paper_dir / self.record()["figures"][0]["assets"]["png"]
        previous_mtime = path.stat().st_mtime_ns
        result = self.extract(skip_existing=True)
        self.assertEqual(result["skipped"], ["DEMO-001"])
        self.assertEqual(path.stat().st_mtime_ns, previous_mtime)
        path.unlink()
        self.assertEqual(self.extract(skip_existing=True)["papers"], 1)

    def test_skip_existing_checks_corruption_segments_and_page_proofs(self):
        self.extract()
        for relative in (self.record()["figures"][0]["assets"]["png"],
                         self.record()["figures"][0]["segments"][0]["assets"]["png"],
                         self.record()["pages"][0]["assets"]["proof"]):
            with self.subTest(asset=relative):
                target = self.paper_dir / relative
                before = target.read_bytes()
                target.write_bytes(b"corrupted")
                self.assertEqual(self.extract(skip_existing=True)["papers"], 1)
                self.assertEqual(target.read_bytes(), before)
                target.unlink()
                self.assertEqual(self.extract(skip_existing=True)["papers"], 1)
                self.assertEqual(target.read_bytes(), before)

    def test_excluding_a_verified_figure_revokes_whole_paper_coverage(self):
        self.extract()
        record = self.record()
        for figure in record["figures"]:
            figure.update(review_status="verified", review_method="human")
        record["coverage"]["page_review_complete"] = True
        record["extraction"].update(status="complete_verified", verified_count=2)
        (self.paper_dir / "figures.json").write_text(json.dumps(record), encoding="utf-8")
        override = self.changes([{"figure_number": "2", "exclude": True}])
        self.extract(overrides_path=override)
        changed = self.record()
        self.assertEqual(changed["figures"][0]["review_status"], "verified")
        self.assertFalse(changed["coverage"]["page_review_complete"])
        self.assertEqual(changed["extraction"]["status"], "extracted_needs_review")

    def test_unregistered_manual_file_is_preserved(self):
        self.extract()
        manual = self.paper_dir / "user-notes.md"
        manual.write_text("keep this file", encoding="utf-8")
        before = snapshot(self.paper_dir)
        with self.assertRaisesRegex(ValueError, "人工文件"):
            extractor.extract(self.scope, self.output)
        self.assertEqual(snapshot(self.paper_dir), before)

    def test_scope_publication_failure_rolls_back_paper_and_index(self):
        self.extract()
        before = snapshot(self.output)
        changed = json.loads(self.scope.read_text(encoding="utf-8"))
        changed["papers"][0]["title"] = "新题名只能与归档一起发布"
        self.scope.write_text(json.dumps(changed), encoding="utf-8")
        original = extractor.os.replace

        def fail_scope(source, target):
            if Path(target) == self.output / "scope.json":
                raise OSError("injected scope publication failure")
            return original(source, target)

        with patch.object(extractor.os, "replace", side_effect=fail_scope):
            result = extractor.extract(self.scope, self.output)
        self.assertFalse(result["ok"])
        self.assertEqual(snapshot(self.output), before)

    def test_new_paper_scope_failure_removes_unindexed_new_assets(self):
        self.output.mkdir()
        extractor.publish_scope(self.output, {})
        before = snapshot(self.output)
        original = extractor.os.replace

        def fail_scope(source, target):
            if Path(target) == self.output / "scope.json":
                raise OSError("injected scope publication failure")
            return original(source, target)

        with patch.object(extractor.os, "replace", side_effect=fail_scope):
            self.assertFalse(extractor.extract(self.scope, self.output)["ok"])
        self.assertEqual(snapshot(self.output), before)

    def test_source_or_note_in_generated_papers_rejected_before_any_write(self):
        original = json.loads(self.scope.read_text(encoding="utf-8"))
        for field in ("pdf_path", "note_path"):
            with self.subTest(field=field):
                value = json.loads(json.dumps(original))
                value["papers"][0][field] = str(self.output / "papers/OTHER-ID/source.pdf")
                self.scope.write_text(json.dumps(value), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "papers"):
                    extractor.extract(self.scope, self.output)
                self.assertFalse(self.output.exists())

    def test_invalid_crop_missing_pdf_corruption_and_failure_preserve_old_archive(self):
        self.extract()
        before = snapshot(self.paper_dir)
        for figures in ([{"figure_number": "1", "segments": [{"page": 1, "bbox": [-1, 0, 20, 20]}]}],
                        [{"figure_number": "1", "segments": [{"page": 99, "bbox": [0, 0, 20, 20]}]}]):
            with self.subTest(figures=figures):
                report = extractor.extract(self.scope, self.output, overrides_path=self.changes(figures))
                self.assertFalse(report["ok"])
                self.assertEqual(snapshot(self.paper_dir), before)
        source = self.base / "虚构 source & # %.pdf"
        content = source.read_bytes()
        source.unlink()
        self.assertFalse(extractor.extract(self.scope, self.output)["ok"])
        self.assertEqual(snapshot(self.paper_dir), before)
        source.write_bytes(b"not a pdf")
        self.assertFalse(extractor.extract(self.scope, self.output)["ok"])
        self.assertEqual(snapshot(self.paper_dir), before)
        source.write_bytes(content)
        with patch.object(extractor, "build_paper", side_effect=OSError("injected render failure")):
            self.assertFalse(extractor.extract(self.scope, self.output)["ok"])
        self.assertEqual(snapshot(self.paper_dir), before)
        self.assertFalse(any(self.output.rglob(".figures-stage-*")))
        self.assertFalse((self.output / ".figures.lock").exists())

    def test_no_caption_keeps_proofs_and_never_claims_no_figures_confirmed(self):
        write_pdf(self.base / "虚构 source & # %.pdf", caption=False)
        self.assertEqual(self.extract()["figure_count"], 0)
        record = self.record()
        self.assertEqual(record["extraction"]["status"], "no_caption_detected_needs_review")
        self.assertFalse(record["coverage"]["page_review_complete"])
        self.assertEqual(len(record["pages"]), 2)

    def test_non_owned_directories_and_output_symlink_rejected(self):
        self.output.mkdir()
        (self.output / "manual.txt").write_text("keep", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "人工目录"):
            extractor.extract(self.scope, self.output)
        self.assertEqual((self.output / "manual.txt").read_text(encoding="utf-8"), "keep")


if __name__ == "__main__":
    unittest.main()
