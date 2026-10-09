"""从指定 Git 提交打包，在临时目录验证分发包和安装后的基本流程。"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile


REPO = Path(__file__).resolve().parents[1]
SKILL = "skills/research-workbench/"
REQUIRED_FILES = {
    "LICENSE", "README.md", "docs/GETTING_STARTED.md", "scripts/install.py",
    SKILL + "SKILL.md", SKILL + "scripts/workbench.py", SKILL + "scripts/literature.py",
    SKILL + "scripts/overview.py", SKILL + "assets/overview.html",
    SKILL + "references/onboarding.md", SKILL + "references/project-manual-template.md",
    SKILL + "references/records.md", SKILL + "references/discovery.md",
    SKILL + "references/schemas/config-v1.schema.json",
    SKILL + "references/schemas/event-v2.schema.json",
    SKILL + "references/schemas/record-v2.schema.json",
}
PRIVATE_PARTS = {
    "_private_reference", "__pycache__", ".git", ".agents", ".codex",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", ".venv", "venv",
    "data", "papers", "library", "outputs", "secrets", "events", "notes",
}
PRIVATE_SUFFIXES = {".pdf", ".caj", ".pem", ".key", ".pyc", ".pyo",
                    ".doc", ".docx", ".xls", ".xlsx", ".sqlite", ".db"}
WINDOWS_RESERVED = {"con", "prn", "aux", "nul"} | {
    prefix + str(number) for prefix in ("com", "lpt") for number in range(1, 10)
}
ARCHIVE_LIMIT = 64 * 1024 * 1024
MEMBER_LIMIT = 10000


class DistributionError(ValueError):
    """只携带检查阶段和规则，不附带个人绝对路径或子进程原始输出。"""


def require(condition, message):
    if not condition:
        raise DistributionError(message)


def validate_archive(archive):
    """先检查整个 ZIP；失败时尚未向磁盘解包任何成员。"""
    require(archive.stat().st_size <= ARCHIVE_LIMIT, "archive: compressed-size-limit")
    try:
        with zipfile.ZipFile(archive) as package:
            members = package.infolist()
            require(len(members) <= MEMBER_LIMIT, "archive: member-count-limit")
            require(sum(item.file_size for item in members) <= ARCHIVE_LIMIT,
                    "archive: expanded-size-limit")
            names = {}
            files = set()
            for item in members:
                # Git archive 使用正斜杠；同时拒绝 Windows 盘符、ADS 和特殊名字。
                require(item.orig_filename == item.filename, "archive: unsafe-member-path")
                name = item.filename[:-1] if item.is_dir() else item.filename
                parts = name.split("/")
                require(not any(character in name for character in '\\:<>"|?*')
                        and not any(ord(character) < 32 for character in name),
                        "archive: unsafe-member-path")
                require(all(part and part not in (".", "..") and part.rstrip(" .") == part
                            and part.split(".", 1)[0].casefold() not in WINDOWS_RESERVED
                            for part in parts), "archive: unsafe-member-path")
                mode = stat.S_IFMT(item.external_attr >> 16)
                require(mode in (0, stat.S_IFDIR, stat.S_IFREG), "archive: special-member")
                require(not item.flag_bits & 1, "archive: encrypted-member")
                key = name.casefold()
                require(key not in names, "archive: duplicate-or-case-collision")
                names[key] = item.is_dir()
                private = (bool(set(part.casefold() for part in parts) & PRIVATE_PARTS)
                           or Path(name).suffix.casefold() in PRIVATE_SUFFIXES
                           or parts[-1].casefold() == ".env"
                           or parts[-1].casefold().startswith(".env."))
                require(not private, "archive: private-or-generated-member")
                if not item.is_dir():
                    files.add(name)
            for name in names:
                parts = name.split("/")
                for length in range(1, len(parts)):
                    require(names.get("/".join(parts[:length]).casefold(), True),
                            "archive: file-directory-collision")
            missing = sorted(REQUIRED_FILES - files)
            require(not missing, "archive: missing-required-files: " + ", ".join(missing))
            # 读取也会校验 ZIP 自身的 CRC，防止破损文件被算作完整成员。
            for item in members:
                if not item.is_dir():
                    require(bool(package.read(item)) or item.filename not in REQUIRED_FILES,
                            "archive: empty-required-file")
            return {"members": len(members), "files": len(files)}
    except (zipfile.BadZipFile, RuntimeError) as error:
        raise DistributionError("archive: unreadable-zip") from error


def extract_archive(archive, destination):
    """仅向新的临时目录安全解包；不使用允许越界路径的 extractall。"""
    report = validate_archive(archive)
    destination.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(archive) as package:
        for item in package.infolist():
            target = destination.joinpath(*item.filename.rstrip("/").split("/"))
            require(target.resolve().is_relative_to(destination.resolve()),
                    "archive: extraction-boundary")
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with package.open(item) as source, target.open("xb") as output:
                    shutil.copyfileobj(source, output)
    return report


def snapshot(root):
    """用相对文件名和原字节比对，不把临时绝对路径写进报告。"""
    return {path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*") if path.is_file()}


def environment():
    return {"python": platform.python_version(), "system": platform.system(),
            "architecture": platform.machine()}


def verify_distribution(repo=REPO, ref="HEAD", report=None):
    """执行真实归档和 CLI；report 可由调用者保留，以查看失败前的步骤。"""
    if report is None:
        report = {}
    report.update({"ok": False, "environment": environment(), "steps": []})

    def mark(name, **details):
        report["steps"].append({"name": name, "ok": True, **details})

    def run(name, arguments, cwd, expected=0):
        # 只使用当前 Python、传参列表和显式 --dest，绝不调用全局安装。
        child_env = dict(os.environ, PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
        child_env.pop("PYTHONPATH", None)
        child_env.pop("PYTHONHOME", None)
        try:
            result = subprocess.run(arguments, cwd=cwd, env=child_env, stdin=subprocess.DEVNULL,
                                    capture_output=True, encoding="utf-8", errors="replace", timeout=60)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise DistributionError(name + ": process-unavailable-or-timeout") from error
        report["steps"].append({"name": name, "ok": result.returncode == expected,
                                "returncode": result.returncode})
        require(result.returncode == expected, name + ": unexpected-exit-code")
        return result.stdout, result.stderr

    def read_json(name, output):
        try:
            value = json.loads(output)
        except (ValueError, TypeError) as error:
            raise DistributionError(name + ": invalid-json-output") from error
        require(isinstance(value, dict), name + ": invalid-json-output-shape")
        return value

    with tempfile.TemporaryDirectory(prefix="workbench-distribution-") as temporary:
        base = Path(temporary) / "中文 分发验证"
        base.mkdir()
        commit, _ = run("resolve_commit", ["git", "rev-parse", "--verify", "--end-of-options",
                                            ref + "^{commit}"], repo)
        commit = commit.strip()
        require(bool(re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit)), "resolve_commit: invalid-sha")
        report["commit"] = commit
        archive = base / "源码 包.zip"
        run("git_archive", ["git", "archive", "--format=zip", "--output", str(archive), commit], repo)
        extracted = base / "解包 源码"
        report["archive"] = {"format": "git archive --format=zip", **extract_archive(archive, extracted),
                             "sha256": hashlib.sha256(archive.read_bytes()).hexdigest()}
        mark("archive_boundary_and_required_files")
        destination = base / "项目 安装" / ".agents" / "skills"
        run("install", [sys.executable, "-X", "utf8", "scripts/install.py", "--dest", str(destination)],
            extracted)
        installed = destination / "research-workbench"
        require(snapshot(installed) == snapshot(extracted / SKILL), "install: installed-files-differ")
        mark("installed_files_match_package")
        before = snapshot(destination)
        _, error = run("refuse_existing_install",
                       [sys.executable, "-X", "utf8", "scripts/install.py", "--dest", str(destination)],
                       extracted, expected=1)
        require("同名" in error, "refuse_existing_install: wrong-rejection")
        require(before == snapshot(destination), "refuse_existing_install: existing-files-changed")
        mark("existing_install_preserved")
        # 移走解包源码再运行，证明没有依赖原 skills 目录或相邻源码文件。
        require(extracted.resolve().is_relative_to(base.resolve()) and extracted.resolve() != base.resolve(),
                "install: source-cleanup-boundary")
        shutil.rmtree(extracted)
        mark("extracted_source_removed")
        cli = [sys.executable, "-X", "utf8", str(installed / "scripts/workbench.py")]
        version, _ = run("installed_version", cli + ["--version"], base)
        version = version.strip()
        require(bool(re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:(?:a|b|rc)[0-9]+)?", version)),
                "installed_version: invalid-version-output")
        report["version"] = version
        installed_doctor, _ = run("installed_doctor", cli + ["doctor"], base)
        diagnosed = read_json("installed_doctor", installed_doctor)
        require(diagnosed.get("status") == "ok" and diagnosed.get("redacted") is True,
                "installed_doctor: incomplete-installation")
        root = base / "虚构 工作台"

        def command(name, operation, selected_root=root, *arguments):
            output, _ = run(name, cli + [operation, "--root", str(selected_root), *arguments], base)
            return output

        command("init", "init", root, "--name", "分发验证用虚构课题")
        record = {"kind": "checkpoint", "status": "计划中", "title": "虚构分发基线",
                  "body": "仅测试安装流程，不是真实科研记录。", "next_step": "核对恢复后的虚构记录"}
        input_file = base / "虚构 记录.json"
        input_file.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8-sig")
        first_id = command("record", "record", root, "--input", str(input_file)).strip()
        require(bool(re.fullmatch(r"[0-9a-f]{32}", first_id)), "record: invalid-event-id")
        first_raw = (root / "events" / (first_id + ".json")).read_bytes()
        revised = dict(record, supersedes=first_id, body="虚构修订：核对记录历史也能完整恢复。")
        input_file.write_text(json.dumps(revised, ensure_ascii=False), encoding="utf-8")
        current_id = command("record_revision", "record", root, "--input", str(input_file)).strip()
        require(bool(re.fullmatch(r"[0-9a-f]{32}", current_id)) and current_id != first_id,
                "record_revision: invalid-event-id")
        require((root / "events" / (first_id + ".json")).read_bytes() == first_raw,
                "record_revision: original-event-changed")
        page = read_json("search", command("search", "search", root, "--query", "虚构分发基线", "--limit", "1"))
        items = page.get("items")
        require(page.get("total") == 1 and isinstance(items, list) and len(items) == 1
                and isinstance(items[0], dict) and items[0].get("id") == current_id
                and page.get("next_offset") is None,
                "search: unexpected-current-record")
        shown = read_json("show", command("show", "show", root, "--id", current_id))
        require(shown.get("is_current") is True and shown.get("latest_id") == current_id
                and isinstance(shown.get("event"), dict)
                and shown["event"].get("record") == revised, "show: unexpected-record")
        history = read_json("show_history", command("show_history", "show", root, "--id", first_id))
        require(history.get("is_current") is False and history.get("latest_id") == current_id
                and isinstance(history.get("event"), dict)
                and history["event"].get("record") == record, "show_history: lost-history")
        resumed = read_json("resume", command("resume", "resume"))
        require(resumed.get("mode") == "lightweight" and resumed.get("reason") is None
                and isinstance(resumed.get("checkpoint"), str)
                and record["next_step"] in resumed["checkpoint"]
                and current_id in resumed["checkpoint"], "resume: missing-checkpoint")
        preferences = resumed.get("project_preferences")
        require(isinstance(preferences, dict) and preferences.get("path") == "PROJECT_MANUAL.md",
                "resume: missing-project-preferences-entry")
        page_report = read_json("overview", command("overview", "overview"))
        require(page_report.get("output") == "OVERVIEW.html" and page_report.get("current_records") == 1,
                "overview: invalid-page-report")
        page_file = root / "OVERVIEW.html"
        require(page_file.is_file() and current_id in page_file.read_text(encoding="utf-8"),
                "overview: missing-current-record")
        (root / "PERSONAL_NOTES.md").write_bytes("虚构手写笔记\r\n中文与空格\r\n".encode("utf-8"))
        (root / "PROJECT_MANUAL.md").write_bytes("# 虚构约定\r\n仅用于分发验证。\r\n".encode("utf-8"))
        original = snapshot(root)
        backup = base / "虚构 备份.json"
        command("backup", "backup", root, "--output", str(backup))
        restored = base / "恢复 后工作台"
        command("restore", "restore", restored, "--input", str(backup))
        require(not (restored / "OVERVIEW.html").exists(), "restore: derived-page-included-in-backup")
        mark("derived_page_excluded_from_backup")
        recovered = snapshot(restored)
        managed = {name for name in original if name == "config.json" or name.startswith("events/")
                   or name in ("PERSONAL_NOTES.md", "PROJECT_MANUAL.md", ".gitignore")}
        require({name: original[name] for name in managed} ==
                {name: recovered.get(name) for name in managed}, "restore: managed-file-bytes-differ")
        require({name for name in recovered if name.startswith("events/")} ==
                {name for name in original if name.startswith("events/")}, "restore: event-set-differs")
        mark("restored_bytes_and_event_history_match", events=2, current=1)
        audit = read_json("restored_audit", command("restored_audit", "audit", restored))
        require(audit.get("events") == 2 and audit.get("current") == 1
                and audit.get("stale_views") == [] and audit.get("evidence_warnings") == [],
                "restored_audit: inconsistent-workbench")
        require(read_json("restored_show", command("restored_show", "show", restored, "--id", current_id)) == shown,
                "restored_show: output-differs")
        require(read_json("restored_history", command("restored_history", "show", restored, "--id", first_id)) == history,
                "restored_history: output-differs")
        require(read_json("restored_resume", command("restored_resume", "resume", restored)) == resumed,
                "restored_resume: output-differs")
        regenerated = read_json("restored_overview", command("restored_overview", "overview", restored))
        restored_page = restored / "OVERVIEW.html"
        require(regenerated.get("output") == "OVERVIEW.html" and regenerated.get("current_records") == 1
                and restored_page.is_file() and current_id in restored_page.read_text(encoding="utf-8"),
                "restored_overview: missing-current-record")
        require(snapshot(root) == original, "restore: source-workbench-changed")
        mark("source_workbench_preserved")
    report["ok"] = True
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default="HEAD", help="要打包的已提交版本；默认 HEAD，不含未提交改动")
    arguments = parser.parse_args(argv)
    report = {}
    try:
        verify_distribution(ref=arguments.ref, report=report)
    except (DistributionError, OSError, ValueError, KeyError, TypeError, AttributeError, IndexError) as error:
        # 原始异常可能含临时路径、用户名或私有 CLI 内容，只输出自己的规则信息。
        report["error"] = str(error) if isinstance(error, DistributionError) else "verification: unexpected-error"
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
