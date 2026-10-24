"""图库的来源和写入边界检查；不要求安装 PDF 可选依赖。"""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("figure_gallery", REPO / "skills/research-workbench/scripts/figure_gallery.py")
gallery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gallery)


class GalleryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(self.temporary.name) / "虚构 项目 & # %"
        self.root = self.project / "图片库"
        self.paper_dir = self.root / "papers" / "DEMO-001"
        self.paper_dir.mkdir(parents=True)
        source = self.project / "原文 & # %.pdf"
        source.write_bytes(b"synthetic source for metadata checks, not a real paper")
        note = self.project / "文字 笔记.md"
        note.write_text("仅用于测试。", encoding="utf-8")
        self.row = {"ledger_id": "DEMO-001", "title": "虚构的测试文献", "authors": ["示例作者"],
                    "year": 2025, "section": "虚构板块", "tags": ["合成"],
                    "pdf_path": "../原文 & # %.pdf", "note_path": "../文字 笔记.md"}
        self.scope = {"schema_version": 1, "papers": [self.row]}
        self.figure = {"figure_id": "DEMO-001-F1", "figure_number": "1", "caption": "Fig. 1. Synthetic example",
                       "category": "workflow", "review_status": "needs_review", "review_method": None,
                       "annotations": {"summary_zh": "虚构流程", "reference_use_zh": "测试说明", "limitation_zh": "无研究结论"},
                       "assets": {"png": "figure.png", "thumbnail": "thumb.png", "pdf": "crop.pdf"},
                       "source": {"pages": [1], "segments": [{"page": 1, "bbox": [10, 20, 190, 160]}]},
                       "segments": [{"page": 1, "bbox": [10, 20, 190, 160],
                                     "assets": {"png": "segment.png", "pdf": "segment.pdf"}}]}
        for name in ("figure.png", "thumb.png", "crop.pdf", "segment.png", "segment.pdf", "proof.png"):
            (self.paper_dir / name).write_bytes(("synthetic asset " + name).encode())
        self.figure["asset_sha256"] = {kind: gallery.digest(self.paper_dir / name)
                                        for kind, name in self.figure["assets"].items()}
        self.manifest = {"schema_version": 1, "paper": self.row, "source_sha256": gallery.digest(source),
                         "extraction": {"status": "extracted_needs_review", "figure_count": 1, "verified_count": 0},
                         "coverage": {"page_review_complete": False}, "figures": [self.figure],
                         "pages": [{"page": 1, "width": 200, "height": 300, "assets": {"proof": "proof.png"}}]}
        self.save()

    def save(self):
        (self.root / "scope.json").write_text(json.dumps(self.scope, ensure_ascii=False), encoding="utf-8")
        (self.paper_dir / "figures.json").write_text(json.dumps(self.manifest, ensure_ascii=False), encoding="utf-8")

    def snapshot(self):
        return {str(path.relative_to(self.project)): (path.read_bytes(), path.stat().st_mtime_ns)
                for path in self.project.rglob("*") if path.is_file()}

    def codes(self):
        return {item["code"] for item in gallery.verify(self.root)["errors"]}

    def test_verify_is_read_only_and_pending_review_is_not_failure(self):
        before = self.snapshot()
        report = gallery.verify(self.root)
        self.assertTrue(report["ok"], report)
        self.assertEqual((report["papers"], report["figures"], report["needs_review"]), (1, 1, 1))
        self.assertEqual(before, self.snapshot())

    def test_build_uses_same_data_and_encodes_special_character_links(self):
        report = gallery.build(self.root)
        data = gallery.read_json(self.root / "gallery_manifest.json")
        self.assertTrue(report["ok"])
        self.assertEqual(data["counts"]["figures"], 1)
        paper = data["papers"][0]
        self.assertIn("%23", paper["source_url"])
        self.assertIn("%25", paper["source_url"])
        self.assertIn("%26", paper["source_url"])
        self.assertEqual(paper["figures"][0]["category"], "方法流程")
        self.assertIn("DEMO-001-F1", (self.root / "快速导航.md").read_text(encoding="utf-8"))
        self.assertNotIn(str(self.project), (self.root / "index.html").read_text(encoding="utf-8"))
        self.assertTrue(gallery.build(self.root)["ok"])

    def test_source_change_or_missing_source_stops_build(self):
        source = self.project / "原文 & # %.pdf"
        source.write_bytes(b"source changed")
        self.assertIn("source_hash_changed", self.codes())
        with self.assertRaisesRegex(ValueError, "检查未通过"):
            gallery.build(self.root)
        source.unlink()
        self.assertIn("source_missing", self.codes())

    def test_scope_and_paper_metadata_cannot_silently_diverge(self):
        self.manifest["paper"] = dict(self.row, title="旧的逐篇题名")
        self.save()
        self.assertIn("paper_scope_metadata_mismatch", self.codes())
        with self.assertRaisesRegex(ValueError, "检查未通过"):
            gallery.build(self.root)

    def test_zero_figure_papers_keep_review_sources_and_proofs(self):
        self.manifest["figures"] = []
        self.manifest["extraction"].update(status="no_caption_detected_needs_review", figure_count=0)
        self.save()
        gallery.build(self.root)
        paper = gallery.read_json(self.root / "gallery_manifest.json")["papers"][0]
        self.assertEqual(paper["figures"], [])
        self.assertEqual(paper["status"], "no_caption_detected_needs_review")
        self.assertEqual(paper["proofs"][0]["page"], 1)
        self.assertTrue(paper["source_url"])
        self.assertTrue(paper["proofs"][0]["url"].endswith("proof.png"))

    def test_asset_change_missing_and_escape_are_detected(self):
        (self.paper_dir / "figure.png").write_bytes(b"changed")
        self.assertIn("asset_hash_mismatch:png", self.codes())
        (self.paper_dir / "figure.png").unlink()
        self.assertIn("asset_missing:png", self.codes())
        self.figure["assets"]["png"] = "../other.png"
        self.save()
        self.assertIn("invalid_asset_path:png", self.codes())

    def test_ids_must_be_unique_and_cannot_escape(self):
        for bad in ("../escape", "C:/escape", "DEMO.001", "CON"):
            with self.subTest(bad=bad):
                self.scope["papers"] = [dict(self.row, ledger_id=bad)]
                self.save()
                self.assertIn("invalid_scope_or_root", self.codes())
        self.scope["papers"] = [self.row, dict(self.row, ledger_id="demo-001")]
        self.save()
        self.assertIn("invalid_scope_or_root", self.codes())

    def test_verified_requires_declared_human_or_ai_method(self):
        self.figure["review_status"] = "verified"
        self.manifest["extraction"]["verified_count"] = 1
        self.save()
        self.assertIn("verified_without_review_method", self.codes())
        self.figure["review_method"] = "ai"
        self.save()
        self.assertTrue(gallery.verify(self.root)["ok"])
        gallery.build(self.root)
        self.assertEqual(gallery.read_json(self.root / "gallery_manifest.json")["papers"][0]["figures"][0]["review_method"], "ai")

    def test_geometry_and_full_coverage_are_checked(self):
        self.figure["segments"][0]["bbox"] = [0, 0, 1000, 200]
        self.manifest["extraction"]["status"] = "complete_verified"
        self.save()
        self.assertIn("segment_outside_page", self.codes())
        self.assertIn("coverage_not_verified", self.codes())
        self.figure["segments"][0]["bbox"] = [0, 0, float("nan"), 200]
        self.save()
        self.assertIn("invalid_segment_geometry", self.codes())

    def test_manual_output_is_not_overwritten_or_partly_generated(self):
        manual = self.root / "快速导航.md"
        manual.write_text("用户手写导航", encoding="utf-8")
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "人工文件"):
            gallery.build(self.root)
        self.assertEqual(before, self.snapshot())
        self.assertFalse((self.root / ".figures.lock").exists())

    def test_existing_manifest_and_page_survive_publish_failure(self):
        gallery.build(self.root)
        before = self.snapshot()
        real_replace = gallery.os.replace
        calls = []

        def interrupted(src, dst):
            calls.append(str(dst))
            if len(calls) == 2:
                raise OSError("synthetic interruption")
            return real_replace(src, dst)

        with patch.object(gallery.os, "replace", side_effect=interrupted):
            with self.assertRaises(OSError):
                gallery.build(self.root)
        after = self.snapshot()
        self.assertEqual({k: v[0] for k, v in before.items()}, {k: v[0] for k, v in after.items()})

    def test_template_does_not_load_network_and_escapes_untrusted_caption(self):
        self.figure["caption"] = '</script><script>alert("x")</script>& <b>测试</b>'
        self.save()
        gallery.build(self.root)
        content = (self.root / "index.html").read_text(encoding="utf-8")
        self.assertNotIn(self.figure["caption"], content)
        self.assertIn("\\u003c/script\\u003e", content)
        self.assertNotIn("fetch(", content)
        self.assertNotIn("innerHTML", content)
        self.assertIn('connect-src \'none\'', content)
        self.assertIn('aria-pressed="true">按图浏览', content)
        for identifier in ("section", "category", "year", "review", "search", "viewer"):
            self.assertIn('id="' + identifier + '"', content)

    def test_project_move_keeps_relative_source_and_asset_links(self):
        gallery.build(self.root)
        first = gallery.read_json(self.root / "gallery_manifest.json")["papers"]
        relocated = Path(self.temporary.name) / "移到这里"
        shutil.move(str(self.project), relocated)
        root = relocated / "图片库"
        self.assertTrue(gallery.verify(root)["ok"])
        gallery.build(root)
        self.assertEqual(first, gallery.read_json(root / "gallery_manifest.json")["papers"])

    def test_sources_must_be_local_files_of_expected_types(self):
        for value in ("https://example.test/paper.pdf", "javascript:alert(1)", "../page.html", "//server/paper.pdf"):
            with self.subTest(value=value):
                self.row["pdf_path"] = value
                self.save()
                self.assertIn("invalid_source_path", self.codes())

    def test_no_figures_is_valid_but_does_not_mean_full_coverage(self):
        self.manifest["figures"] = []
        self.manifest["extraction"].update(status="no_caption_detected_needs_review", figure_count=0)
        self.save()
        self.assertTrue(gallery.build(self.root)["ok"])
        self.assertEqual(gallery.verify(self.root)["figures"], 0)

    def test_bad_nested_data_is_reported_without_crashing(self):
        self.figure["source"] = []
        self.figure["segments"][0]["assets"] = []
        self.save()
        self.assertIn("invalid_segment_assets", self.codes())
        self.assertIn("source_pages_mismatch", self.codes())

    def test_text_metadata_must_have_safe_shapes(self):
        self.scope["papers"][0]["authors"] = "单个字符串不能当作者数组"
        self.save()
        self.assertIn("invalid_scope_or_root", self.codes())
        self.scope["papers"][0]["authors"] = ["示例作者"]
        self.figure["annotations"] = []
        self.save()
        self.assertIn("invalid_figure_text", self.codes())

    def test_generated_output_cannot_be_a_symlink(self):
        target = self.project / "用户内容.html"
        target.write_text("不能修改", encoding="utf-8")
        try:
            (self.root / "index.html").symlink_to(target)
        except OSError:
            self.skipTest("系统未授予创建符号链接权限")
        with self.assertRaises(ValueError):
            gallery.build(self.root)
        self.assertEqual(target.read_text(encoding="utf-8"), "不能修改")

    def test_concurrent_extract_or_build_lock_is_respected(self):
        (self.root / ".figures.lock").write_text("synthetic owner", encoding="utf-8")
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "正在处理"):
            gallery.build(self.root)
        self.assertEqual(before, self.snapshot())

    def test_windows_reparse_point_guard_does_not_need_new_path_api(self):
        # Python 3.10 尚无 Path.is_junction；文件属性必须也能拦截目录联接。
        with patch.object(Path, "lstat", return_value=SimpleNamespace(st_file_attributes=0x400, st_mode=0)):
            with self.assertRaisesRegex(ValueError, "目录联接"):
                gallery.no_links(self.root)


if __name__ == "__main__":
    unittest.main()
