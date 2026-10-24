"""用实际 CLI 验证没有 PDF 组件时的基础命令和错误边界。"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


CLI = Path(__file__).resolve().parents[1] / "skills/research-workbench/scripts/workbench.py"


class FigureCommandTests(unittest.TestCase):
    def command(self, *arguments):
        # -S 不加载 site-packages，证明基础入口不依赖已安装的 PDF 包。
        return subprocess.run([sys.executable, "-S", "-B", "-X", "utf8", str(CLI), *arguments],
                              capture_output=True, encoding="utf-8", check=False)

    def test_core_and_figure_help_work_without_optional_packages(self):
        self.assertEqual(self.command("--version").returncode, 0)
        help_result = self.command("figures", "extract", "--help")
        self.assertEqual(help_result.returncode, 0)
        self.assertIn("--overrides", help_result.stdout)
        self.assertIn("--skip-existing", help_result.stdout)

    def test_missing_optional_packages_do_not_create_gallery(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            scope = base / "scope.json"
            scope.write_text(json.dumps({"schema_version": 1, "papers": []}), encoding="utf-8")
            gallery = base / "gallery"
            result = self.command("figures", "extract", "--scope", str(scope), "--output", str(gallery))
            self.assertEqual(result.returncode, 2)
            self.assertIn("requirements-figures", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertFalse(gallery.exists())

    def test_read_only_verify_returns_json_and_nonzero_for_invalid_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            missing = Path(temporary) / "missing"
            result = self.command("figures", "verify", "--root", str(missing))
            self.assertEqual(result.returncode, 1)
            report = json.loads(result.stdout)
            self.assertFalse(report["ok"])
            self.assertTrue(report["read_only"])
            self.assertFalse(missing.exists())
