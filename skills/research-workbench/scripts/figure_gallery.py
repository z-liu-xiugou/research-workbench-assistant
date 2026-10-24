"""把逐篇图目生成离线图库，或只读检查来源、资产和核验记录。"""
import hashlib
from contextlib import contextmanager
import json
import math
import os
from pathlib import Path
import re
import stat
import tempfile
from datetime import datetime, timezone
from urllib.parse import quote


OWNER = "research-workbench-figures:v1"
MARKER = "<!-- " + OWNER + " -->"
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}\Z")
FIGURE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,159}\Z")
RESERVED = {"con", "prn", "aux", "nul"} | {
    prefix + str(number) for prefix in ("com", "lpt") for number in range(1, 10)}
CATEGORY_LABELS = {"other": "其他正式图", "structure": "模型结构", "workflow": "方法流程",
                   "results": "实验结果", "system": "系统示意"}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(part)
    return value.hexdigest()


def identifier(value):
    if not isinstance(value, str) or not ID.fullmatch(value) or value.lower() in RESERVED:
        raise ValueError("文献 ID 只能使用字母、数字、下划线和连字符，且不能是系统保留名")
    return value


def no_links(path):
    """生成目录的任何现存父级都不能是链接，避免把输出写到别处。"""
    path = Path(path).absolute()
    for part in (path, *path.parents):
        try:
            attributes = getattr(part.lstat(), "st_file_attributes", 0)
        except FileNotFoundError:
            attributes = 0
        if (part.is_symlink() or getattr(part, "is_junction", lambda: False)()
                or attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)):
            raise ValueError("图库目录及父目录不能是符号链接或目录联接")
    return path.resolve()


def source_path(value, base, suffixes=None):
    if not isinstance(value, str) or not value or any(ord(c) < 32 for c in value):
        raise ValueError("来源路径必须是非空本地文件路径")
    # Windows 盘符是本地路径；其余冒号会把 URL、ADS 等误当作文件。
    if re.match(r"^[A-Za-z]:[\\/]", value):
        local = Path(value)
    else:
        if ":" in value or value.startswith(("//", "\\\\")):
            raise ValueError("来源只接受本地文件，不接受网址或网络共享路径")
        local = Path(value)
    path = local if local.is_absolute() else Path(base) / local
    path = path.resolve()
    if suffixes and path.suffix.lower() not in suffixes:
        raise ValueError("来源文件类型不受支持")
    return path


def asset_path(directory, value):
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ValueError("资产路径必须是图库内的相对路径")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("资产路径越出逐篇目录")
    path = no_links(Path(directory) / relative)
    if not path.resolve().is_relative_to(Path(directory).resolve()):
        raise ValueError("资产路径越出逐篇目录")
    return path


def local_url(path, root, page=None):
    """只从已解析的本地文件生成链接；空格、#、% 等按 URL 编码。"""
    try:
        relative = os.path.relpath(path, root).replace(os.sep, "/")
    except ValueError:
        return None  # Windows 不同盘符没有可随项目移动的相对链接。
    url = quote(relative, safe="/")
    return url + ("#page=" + str(page) if page else "")


def load_scope(root, scope_path=None):
    root = no_links(root)
    if not root.is_dir():
        raise ValueError("图库目录不存在，请先提取图像")
    scope = Path(scope_path).resolve() if scope_path else root / "scope.json"
    data = read_json(scope)
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("papers"), list):
        raise ValueError("scope.json 必须包含 schema_version=1 和 papers 数组")
    seen = set()
    for row in data["papers"]:
        if not isinstance(row, dict):
            raise ValueError("papers 中每项必须是对象")
        key = identifier(row.get("ledger_id"))
        if key.casefold() in seen:
            raise ValueError("文献 ID 重复（不区分大小写）：" + key)
        seen.add(key.casefold())
        if not isinstance(row.get("title"), str) or not row["title"].strip():
            raise ValueError("每篇文献需要非空题名")
        for field in ("authors", "tags"):
            if not isinstance(row.get(field, []), list) or not all(isinstance(value, str) for value in row.get(field, [])):
                raise ValueError(field + " 必须是文字数组")
    return root, scope, data["papers"]


def valid_bbox(value):
    return (isinstance(value, list) and len(value) == 4
            and all(type(number) in (int, float) and math.isfinite(number) for number in value)
            and 0 <= value[0] < value[2] and 0 <= value[1] < value[3])


def verify(root, scope_path=None):
    """检查结构与文件，不写入、不改变核验状态，也不证明图已提取齐全。"""
    report = {"ok": False, "read_only": True, "papers": 0, "figures": 0,
              "needs_review": 0, "errors": [], "warnings": []}

    def error(code, paper=None, figure=None):
        item = {"code": code}
        if paper:
            item["paper"] = paper
        if figure:
            item["figure"] = figure
        report["errors"].append(item)

    try:
        root, scope, rows = load_scope(root, scope_path)
    except (OSError, ValueError, TypeError, KeyError):
        error("invalid_scope_or_root")
        return report
    report["papers"] = len(rows)
    figure_ids = set()
    for row in rows:
        key = row["ledger_id"]
        directory = root / "papers" / key
        try:
            no_links(directory)
            item = read_json(directory / "figures.json")
            if not isinstance(item, dict) or item.get("schema_version") != 1 or not isinstance(item.get("figures"), list):
                raise ValueError("invalid figures.json")
            if not isinstance(item.get("paper"), dict) or item["paper"].get("ledger_id") != key:
                raise ValueError("paper mismatch")
            if item["paper"] != row:
                # 外部范围清单的来源路径可使用另一相对基准，其余元数据必须一致。
                left, right = dict(item["paper"]), dict(row)
                for field in ("pdf_path", "note_path"):
                    if left.get(field):
                        left[field] = str(source_path(left[field], root))
                    if right.get(field):
                        right[field] = str(source_path(right[field], scope.parent))
                if left != right:
                    error("paper_scope_metadata_mismatch", key)
        except (OSError, ValueError, TypeError):
            error("missing_or_invalid_paper_manifest", key)
            continue
        try:
            pdf = source_path(row.get("pdf_path"), scope.parent, {".pdf"})
            if not pdf.is_file():
                error("source_missing", key)
            elif digest(pdf) != item.get("source_sha256"):
                error("source_hash_changed", key)
        except (OSError, ValueError):
            error("invalid_source_path", key)
        if row.get("note_path"):
            try:
                if not source_path(row["note_path"], scope.parent, {".md", ".txt"}).is_file():
                    report["warnings"].append({"code": "note_missing", "paper": key})
            except ValueError:
                error("invalid_note_path", key)
        figures = item["figures"]
        pages = item.get("pages", [])
        if not isinstance(pages, list):
            error("invalid_pages", key)
            pages = []
        geometry = {page["page"]: (page.get("width"), page.get("height"))
                    for page in pages if isinstance(page, dict) and type(page.get("page")) is int}
        if not pages or len(geometry) != len(pages):
            error("missing_or_duplicate_pages", key)
        report["figures"] += len(figures)
        verified = 0
        for figure in figures:
            if not isinstance(figure, dict):
                error("invalid_figure", key)
                continue
            fid = figure.get("figure_id")
            if not isinstance(fid, str) or not FIGURE_ID.fullmatch(fid) or not fid.startswith(key + "-F") or fid.casefold() in figure_ids:
                error("invalid_or_duplicate_figure_id", key)
            else:
                figure_ids.add(fid.casefold())
            annotations = figure.get("annotations", {})
            if (not isinstance(figure.get("caption"), str) or not isinstance(figure.get("category"), str)
                    or not isinstance(annotations, dict)
                    or not all(isinstance(value, str) for value in annotations.values())):
                error("invalid_figure_text", key, fid)
            if figure.get("review_status") == "verified":
                verified += 1
                if figure.get("review_method") not in ("human", "ai"):
                    error("verified_without_review_method", key, fid)
            elif figure.get("review_status") == "needs_review":
                report["needs_review"] += 1
            else:
                error("invalid_review_status", key, fid)
            assets = figure.get("assets", {})
            hashes = figure.get("asset_sha256", {})
            if not isinstance(assets, dict) or not isinstance(hashes, dict):
                error("invalid_assets", key, fid)
                continue
            for kind in ("png", "thumbnail", "pdf"):
                try:
                    target = asset_path(directory, assets.get(kind))
                    expected_suffix = ".pdf" if kind == "pdf" else ".png"
                    if target.suffix.lower() != expected_suffix:
                        error("invalid_asset_type:" + kind, key, fid)
                    elif not target.is_file():
                        error("asset_missing:" + kind, key, fid)
                    elif digest(target) != hashes.get(kind):
                        error("asset_hash_mismatch:" + kind, key, fid)
                except (OSError, ValueError):
                    error("invalid_asset_path:" + kind, key, fid)
            segments = figure.get("segments", [])
            if not isinstance(segments, list) or not segments:
                error("missing_segments", key, fid)
                continue
            for segment in segments:
                if (not isinstance(segment, dict) or type(segment.get("page")) is not int
                        or segment["page"] < 1 or not valid_bbox(segment.get("bbox"))):
                    error("invalid_segment_geometry", key, fid)
                    continue
                size = geometry.get(segment["page"])
                if size is None:
                    error("segment_page_missing", key, fid)
                if size and all(type(v) in (int, float) and math.isfinite(v) for v in size):
                    if segment["bbox"][2] > size[0] + .01 or segment["bbox"][3] > size[1] + .01:
                        error("segment_outside_page", key, fid)
                segment_assets = segment.get("assets", {})
                if not isinstance(segment_assets, dict) or set(segment_assets) != {"png", "pdf"}:
                    error("invalid_segment_assets", key, fid)
                    continue
                for kind, name in segment_assets.items():
                    try:
                        if kind not in ("png", "pdf") or not asset_path(directory, name).is_file():
                            error("segment_asset_missing", key, fid)
                    except (OSError, ValueError):
                        error("invalid_segment_asset_path", key, fid)
            source = figure.get("source", {})
            source_pages = source.get("pages") if isinstance(source, dict) else None
            if source_pages != list(dict.fromkeys(segment.get("page") for segment in segments if isinstance(segment, dict))):
                error("source_pages_mismatch", key, fid)
            if isinstance(source, dict) and source.get("segments") != [{"page": segment.get("page"), "bbox": segment.get("bbox")}
                    for segment in segments if isinstance(segment, dict)]:
                error("source_segments_mismatch", key, fid)
        extraction = item.get("extraction", {})
        if not isinstance(extraction, dict):
            error("invalid_extraction", key)
            extraction = {}
        if extraction.get("figure_count") != len(figures) or extraction.get("verified_count") != verified:
            error("count_mismatch", key)
        coverage = item.get("coverage", {})
        if not isinstance(coverage, dict):
            error("invalid_coverage", key)
            coverage = {}
        if extraction.get("status") == "complete_verified" and (not figures or verified != len(figures) or not coverage.get("page_review_complete")):
            error("coverage_not_verified", key)
        for page in pages:
            try:
                if not asset_path(directory, page["assets"]["proof"]).is_file():
                    error("page_proof_missing", key)
            except (OSError, ValueError, TypeError, KeyError):
                error("invalid_page_proof", key)
    report["ok"] = not report["errors"]
    report["note"] = "结构检查不等于原文图像完整覆盖；人工与 AI 复核不代表文献已人工阅读。"
    return report


def normalized(root, scope_path=None):
    root, scope, rows = load_scope(root, scope_path)
    papers = []
    for row in rows:
        key = row["ledger_id"]
        directory = no_links(root / "papers" / key)
        item = read_json(directory / "figures.json")
        pdf = source_path(row.get("pdf_path"), scope.parent, {".pdf"})
        note = source_path(row["note_path"], scope.parent, {".md", ".txt"}) if row.get("note_path") else None
        paper = {"id": key, "title": str(row.get("title", key)),
                 "authors": "、".join(map(str, row.get("authors", []))), "year": str(row.get("year", "未知")),
                 "section": str(row.get("section") or "未分类"), "tags": list(map(str, row.get("tags", []))),
                 "source_url": local_url(pdf, root), "note_url": local_url(note, root) if note else None,
                 "manifest_url": local_url(directory / "figures.json", root), "figures": [],
                 "status": item.get("extraction", {}).get("status", "needs_review"),
                 "proofs": [{"page": page["page"], "url": local_url(asset_path(directory, page["assets"]["proof"]), root)}
                            for page in item.get("pages", [])]}
        for figure in item.get("figures", []):
            annotation = figure.get("annotations", {})
            shown = {"id": str(figure.get("figure_id", "")), "number": str(figure.get("figure_number", "")),
                     "caption": str(figure.get("caption") or "原图注待补充"),
                     "category": CATEGORY_LABELS.get(figure.get("category"), str(figure.get("category") or "未分类")),
                     "review": figure.get("review_status", "needs_review"),
                     "review_method": figure.get("review_method"),
                     "summary": str(annotation.get("summary_zh") or ""),
                     "use": str(annotation.get("reference_use_zh") or ""),
                     "limitation": str(annotation.get("limitation_zh") or ""),
                     "assets": {}, "segments": [], "pages": figure.get("source", {}).get("pages", [])}
            for kind, name in figure.get("assets", {}).items():
                if kind in ("png", "thumbnail", "pdf"):
                    shown["assets"][kind] = local_url(asset_path(directory, name), root)
            for segment in figure.get("segments", []):
                shown["segments"].append({"page": segment["page"],
                    "source_url": local_url(pdf, root, segment["page"]),
                    "assets": {kind: local_url(asset_path(directory, name), root)
                               for kind, name in segment.get("assets", {}).items() if kind in ("png", "pdf")}})
            paper["figures"].append(shown)
        papers.append(paper)
    return papers


def publish(root, contents):
    """先检查全部旧入口，再暂存全部内容；发布异常时恢复已替换的入口。"""
    old = {}
    temporary = {}
    replaced = []
    try:
        for name in contents:
            path = no_links(root / name)
            previous = path.read_bytes() if path.exists() else None
            if previous is not None:
                if name.endswith(".json"):
                    try:
                        owned = json.loads(previous).get("generator") == OWNER
                    except (ValueError, AttributeError):
                        owned = False
                else:
                    owned = previous.decode("utf-8-sig").startswith(MARKER)
                if not owned:
                    raise ValueError("拒绝覆盖没有工具标记的人工文件：" + name)
            old[name] = previous
        for name, content in contents.items():
            fd, location = tempfile.mkstemp(prefix=".figures-", dir=root)
            temporary[name] = Path(location)
            with os.fdopen(fd, "wb") as stream:
                stream.write(content.encode("utf-8"))
        try:
            for name, location in temporary.items():
                os.replace(location, root / name)
                replaced.append(name)
        except OSError:
            for name in reversed(replaced):
                if old[name] is None:
                    (root / name).unlink(missing_ok=True)
                else:
                    (root / name).write_bytes(old[name])
            raise
    finally:
        for location in temporary.values():
            location.unlink(missing_ok=True)


@contextmanager
def locked(root):
    """与提取器共用图库锁，避免一边替换图像一边生成网页。"""
    lock = root / ".figures.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise ValueError("图库正在处理；确认没有写入进程后再处理遗留 .figures.lock") from None
    os.close(fd)
    try:
        yield
    finally:
        lock.unlink(missing_ok=True)


def build(root, scope_path=None):
    root = no_links(root)
    if not root.is_dir():
        raise ValueError("图库目录不存在，请先提取图像")
    with locked(root):
        return _build(root, scope_path)


def _build(root, scope_path=None):
    report = verify(root, scope_path)
    if not report["ok"]:
        raise ValueError("图库检查未通过，请先执行 figures verify：" + ", ".join(item["code"] for item in report["errors"][:5]))
    papers = normalized(root, scope_path)
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    data = {"generator": OWNER, "schema_version": 1, "generated": stamp, "papers": papers,
            "counts": {"papers": len(papers), "figures": report["figures"], "needs_review": report["needs_review"]}}
    embedded = json.dumps(data, ensure_ascii=False).replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    template = (Path(__file__).resolve().parents[1] / "assets/figures.html").read_text(encoding="utf-8")
    if template.count("__FIGURE_DATA__") != 1 or not template.startswith(MARKER):
        raise ValueError("图库页面模板缺失或格式不正确")
    navigation = [MARKER, "# 文献图片快速导航", "", "生成时间（UTC）：" + stamp,
                  "", "图像核验不代表文献已人工阅读。裁切 PDF 不是脱敏文件。", ""]
    for paper in papers:
        title = re.sub(r"[\r\n\[\]<>]", " ", paper["title"])
        navigation.extend(["## " + paper["id"] + " · " + title, "", "[逐篇图目](" + paper["manifest_url"] + ")", ""])
        for figure in paper["figures"]:
            caption = re.sub(r"[\r\n\[\]<>]", " ", figure["caption"])
            navigation.append("- " + figure["id"] + "：" + caption + " [PNG](" + figure["assets"]["png"] + ")")
        navigation.append("")
    publish(root, {"index.html": template.replace("__FIGURE_DATA__", embedded),
                   "gallery_manifest.json": json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                   "快速导航.md": "\n".join(navigation) + "\n"})
    return {"ok": True, "output": "index.html", "manifest": "gallery_manifest.json",
            "papers": len(papers), "figures": report["figures"], "needs_review": report["needs_review"],
            "note": "离线快照已生成；修改清单后需重新生成，来源链接随项目相对目录移动。"}
