"""破包必须在解包前被拒绝；基本流程必须运行选定提交的安装副本。"""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
import warnings
import zipfile


REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("verify_distribution", REPO / "scripts/verify_distribution.py")
distribution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(distribution)


def git(root, *arguments):
    return subprocess.run(["git", *arguments], cwd=root, capture_output=True,
                          encoding="utf-8", errors="replace", check=True).stdout.strip()


class ArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.fixture.cleanup)
        cls.original = Path(cls.fixture.name) / "committed.zip"
        git(REPO, "archive", "--format=zip", "--output", str(cls.original), "HEAD")

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)

    def mutate(self, remove=(), additions=()):
        """直接改变真实 git archive 的成员，不依靠 checker 的文件清单造正确包。"""
        output = self.base / "changed.zip"
        with zipfile.ZipFile(self.original) as source, zipfile.ZipFile(output, "w") as target:
            for item in source.infolist():
                if item.filename not in remove:
                    target.writestr(item, source.read(item))
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                for name, content in additions:
                    if isinstance(name, str):
                        # ZipInfo 在 Windows 会把反斜杠转成正斜杠；直接改成员名才保留坏包原样。
                        member = zipfile.ZipInfo("placeholder")
                        member.filename = name
                    else:
                        member = name
                    target.writestr(member, content)
        return output

    def assert_refused_before_extract(self, archive, reason):
        target = self.base / "未创建 解包目录"
        with self.assertRaisesRegex(distribution.DistributionError, reason):
            distribution.extract_archive(archive, target)
        self.assertFalse(target.exists())

    def test_real_archive_extracts_with_chinese_and_spaces(self):
        target = self.base / "中文 解包目录"
        result = distribution.extract_archive(self.original, target)
        self.assertGreater(result["files"], 0)
        with zipfile.ZipFile(self.original) as source:
            self.assertEqual((target / "scripts/install.py").read_bytes(), source.read("scripts/install.py"))
            self.assertEqual((target / "skills/research-workbench/scripts/workbench.py").read_bytes(),
                             source.read("skills/research-workbench/scripts/workbench.py"))

    def test_missing_cli_sibling_and_schema_each_rejected(self):
        for name in ("scripts/install.py", "skills/research-workbench/scripts/workbench.py",
                     "skills/research-workbench/scripts/literature.py",
                     "skills/research-workbench/scripts/overview.py",
                     "skills/research-workbench/assets/overview.html",
                     "skills/research-workbench/references/project-manual-template.md",
                     "skills/research-workbench/references/schemas/record-v2.schema.json"):
            with self.subTest(omitted=name):
                self.assert_refused_before_extract(self.mutate(remove=(name,)), "missing-required-files")

    def test_empty_cli_rejected_even_when_filename_is_present(self):
        name = "skills/research-workbench/scripts/workbench.py"
        self.assert_refused_before_extract(self.mutate(remove=(name,), additions=((name, b""),)),
                                           "empty-required-file")

    def test_private_material_and_actual_record_locations_rejected(self):
        for name in ("_private_reference/source.json", "papers/unused.txt", ".env", "local/.env.secret",
                     "skills/research-workbench/scripts/__pycache__/workbench.pyc",
                     "project-workbench/events/" + "a" * 32 + ".json",
                     "research-workbench/notes/private.md", "data/measurements.json",
                     "secrets/config.json", "paper.pdf", "ledger.xlsx"):
            with self.subTest(member=name):
                self.assert_refused_before_extract(self.mutate(additions=((name, "synthetic"),)),
                                                   "private-or-generated-member")

    def test_path_traversal_absolute_and_windows_names_rejected(self):
        for name in ("../escaped.txt", "/absolute.txt", "C:/escape.txt", "a/../escape.txt",
                     "a\\escape.txt", "a//escape.txt", "a/./escape.txt", "CON", "NUL.txt", "tail. ",
                     "a?b", "a*b", 'a"b', "a<b", "a>b", "a|b", "a\x01b"):
            with self.subTest(member=name):
                self.assert_refused_before_extract(self.mutate(additions=((name, "synthetic"),)),
                                                   "unsafe-member-path")
        self.assertFalse((self.base.parent / "escaped.txt").exists())

    def test_symlink_member_rejected(self):
        member = zipfile.ZipInfo("shortcut")
        member.create_system = 3
        member.external_attr = (stat.S_IFLNK | 0o777) << 16
        self.assert_refused_before_extract(self.mutate(additions=((member, "../elsewhere"),)), "special-member")

    def test_duplicate_and_case_collisions_rejected(self):
        for name in ("README.md", "readme.md"):
            with self.subTest(member=name):
                self.assert_refused_before_extract(self.mutate(additions=((name, "synthetic"),)),
                                                   "duplicate-or-case-collision")

    def test_file_cannot_be_parent_of_another_member(self):
        for parent, child in (("extra", "extra/child"), ("ExTrA", "EXTRA/child")):
            with self.subTest(parent=parent, child=child):
                self.assert_refused_before_extract(self.mutate(additions=((parent, "file"), (child, "file"))),
                                                   "file-directory-collision")

    def test_invalid_zip_rejected_without_partial_extraction(self):
        broken = self.base / "broken.zip"
        broken.write_bytes(b"not a zip file")
        self.assert_refused_before_extract(broken, "unreadable-zip")


class CommitDistributionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.base = Path(cls.temporary.name)
        archive = cls.base / "base.zip"
        git(REPO, "archive", "--format=zip", "--output", str(archive), "HEAD")
        cls.repo = cls.base / "虚构 Git 仓库"
        distribution.extract_archive(archive, cls.repo)
        # 配置仅用于这个新建的虚构仓库，不读写维护者的全局 Git 配置。
        git(cls.repo, "-c", "init.templateDir=", "init", "-q")
        git(cls.repo, "config", "user.name", "Distribution Test")
        git(cls.repo, "config", "user.email", "distribution@example.invalid")
        git(cls.repo, "config", "commit.gpgsign", "false")
        git(cls.repo, "config", "core.hooksPath", str(cls.base / "no-hooks"))
        git(cls.repo, "add", ".")
        git(cls.repo, "commit", "-qm", "Synthetic distribution fixture")
        cls.good_commit = git(cls.repo, "rev-parse", "HEAD")
        git(cls.repo, "rm", "-q", "skills/research-workbench/scripts/literature.py")
        git(cls.repo, "commit", "-qm", "Intentionally remove required installed dependency")
        cls.bad_commit = git(cls.repo, "rev-parse", "HEAD")
        git(cls.repo, "checkout", cls.good_commit, "--", "skills/research-workbench/scripts/literature.py")
        script = cls.repo / "skills/research-workbench/scripts/workbench.py"
        # CLI 返回码仍为 0，但把 search 应返回的对象替换为数组。
        script.write_text('import sys\nif sys.argv[1:2] == ["search"]:\n'
                          '    print("[]")\n    sys.exit(0)\n' + script.read_text(encoding="utf-8"),
                          encoding="utf-8")
        git(cls.repo, "add", "skills/research-workbench/scripts/workbench.py")
        git(cls.repo, "commit", "-qm", "Intentionally return wrong JSON shape from search")
        cls.malformed_commit = git(cls.repo, "rev-parse", "HEAD")
        (cls.repo / "skills/research-workbench/scripts/workbench.py").write_text(
            "raise SystemExit(99)\n", encoding="utf-8")
        (cls.repo / "_private_reference").mkdir()
        (cls.repo / "_private_reference/untracked.txt").write_text("synthetic", encoding="utf-8")

    def test_selected_commit_runs_even_when_head_and_working_tree_are_broken(self):
        report = distribution.verify_distribution(self.repo, self.good_commit)
        self.assertTrue(report["ok"])
        self.assertEqual(report["commit"], self.good_commit)
        steps = {row["name"]: row for row in report["steps"]}
        for name in ("extracted_source_removed", "refuse_existing_install", "search", "show_history",
                     "restored_audit", "restored_show", "restored_history", "restored_resume"):
            self.assertTrue(steps[name]["ok"], name)
        self.assertEqual(steps["refuse_existing_install"]["returncode"], 1)
        self.assertEqual(steps["restored_bytes_and_event_history_match"]["events"], 2)
        self.assertNotIn(str(self.base), json.dumps(report))

    def test_selected_broken_commit_refused_before_install(self):
        report = {}
        with self.assertRaisesRegex(distribution.DistributionError, "missing-required-files"):
            distribution.verify_distribution(self.repo, self.bad_commit, report)
        self.assertFalse(report["ok"])
        self.assertEqual(report["commit"], self.bad_commit)
        self.assertNotIn("install", [row["name"] for row in report["steps"]])

    def test_dash_prefixed_ref_is_not_interpreted_as_git_option(self):
        report = {}
        with self.assertRaisesRegex(distribution.DistributionError, "resolve_commit: unexpected-exit-code"):
            distribution.verify_distribution(self.repo, "--help", report)
        self.assertFalse(report["ok"])
        self.assertEqual(len(report["steps"]), 1)

    def test_success_exit_with_wrong_cli_json_shape_still_fails_cleanly(self):
        report = {}
        with self.assertRaisesRegex(distribution.DistributionError, "search: invalid-json-output-shape"):
            distribution.verify_distribution(self.repo, self.malformed_commit, report)
        self.assertFalse(report["ok"])
        self.assertEqual(report["commit"], self.malformed_commit)
        self.assertNotIn("backup", [row["name"] for row in report["steps"]])

    def test_main_invalid_ref_returns_json_without_private_absolute_paths(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = distribution.main(["--ref=" + str(self.base / "not-a-git-ref")])
        report = json.loads(output.getvalue())
        self.assertEqual(code, 1)
        self.assertFalse(report["ok"])
        self.assertIn("resolve_commit", report["error"])
        self.assertNotIn(str(self.base), output.getvalue())
        self.assertNotIn(str(REPO), output.getvalue())


if __name__ == "__main__":
    unittest.main()
