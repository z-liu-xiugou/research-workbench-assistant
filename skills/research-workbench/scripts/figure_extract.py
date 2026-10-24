"""把用户自己的 PDF 提取为待复核的完整图；不下载论文，也不自动确认人工已读。"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import copy
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile
import uuid


GENERATOR = "research-workbench-figures:v1"
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}\Z")
NUMBER = re.compile(r"[A-Za-z]?\d+(?:[.-]\d+)*\Z")
RESERVED = {"con", "prn", "aux", "nul"} | {prefix + str(number) for prefix in ("com", "lpt") for number in range(1, 10)}
CAPTION = re.compile(r"^\s*(?:Fig(?:ure)?\.?|图)\s*([A-Za-z]?\d+(?:[.-]\d+)*)[.．:：]?\s*(.*)$", re.I)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def no_links(path):
    """生成目录的每层都必须是真实目录，避免通过目录链接写到别处。"""
    path = Path(path).absolute()
    for item in (path, *path.parents):
        reparse = item.exists() and getattr(item.lstat(), "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        if item.is_symlink() or reparse:
            raise ValueError("图库输出路径不能包含符号链接或目录联接")
    return path


def dependencies():
    try:
        import pdfplumber
        from pypdf import PdfReader, PdfWriter, Transformation
        from pypdf.generic import RectangleObject
        from PIL import Image
    except ImportError:
        raise ValueError("图片提取缺少可选依赖；请使用当前 Python 安装本技能 requirements-figures.txt，再重试。") from None
    return pdfplumber, PdfReader, PdfWriter, Transformation, RectangleObject, Image


def scope_rows(path):
    data = read_json(path)
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("papers"), list):
        raise ValueError("scope.json 必须是 schema_version=1 且含 papers 数组的对象")
    found = set()
    for row in data["papers"]:
        if not isinstance(row, dict) or not isinstance(row.get("ledger_id"), str) or not ID.fullmatch(row["ledger_id"]) or row["ledger_id"].casefold() in RESERVED:
            raise ValueError("文献 ID 只能包含字母、数字、下划线和短横线，长度为 1–80")
        key = row["ledger_id"].casefold()
        if key in found:
            raise ValueError("文献 ID 重复（包含仅大小写不同的情况）：" + row["ledger_id"])
        found.add(key)
        if not isinstance(row.get("title"), str) or not row["title"].strip():
            raise ValueError("每篇文献必须填写 title")
        if not isinstance(row.get("pdf_path"), str) or not row["pdf_path"].strip():
            raise ValueError("每篇文献必须填写 pdf_path")
    return data["papers"]


def relative_row(row, source_dir, output):
    result = copy.deepcopy(row)
    for field in ("pdf_path", "note_path"):
        if result.get(field):
            original = Path(result[field]).expanduser()
            original = original if original.is_absolute() else source_dir / original
            try:
                result[field] = Path(os.path.relpath(original.resolve(), output)).as_posix()
            except ValueError:
                # Windows 两个磁盘之间无法形成相对路径；保留明确的本地来源。
                result[field] = original.resolve().as_posix()
    return result


def recorded_assets(previous):
    """只认图目中实际登记的相对生成文件，不允许图目借此访问任意路径。"""
    paths = {}
    for figure in previous.get("figures", []):
        paths.update({value: figure.get("asset_sha256", {}).get(key)
                      for key, value in figure.get("assets", {}).items()})
        for segment in figure.get("segments", []):
            paths.update({value: segment.get("asset_sha256", {}).get(key)
                          for key, value in segment.get("assets", {}).items()})
    for page in previous.get("pages", []):
        paths.update({value: page.get("asset_sha256", {}).get(key)
                      for key, value in page.get("assets", {}).items()})
    for value in paths:
        path = Path(value)
        if not isinstance(value, str) or path.is_absolute() or ".." in path.parts or "\\" in value or ":" in value:
            raise ValueError("已有图目包含不安全的生成资产路径")
    return paths


def check_owned_tree(target, previous):
    allowed = set(recorded_assets(previous)) | {"figures.json"}
    for item in target.rglob("*"):
        no_links(item)
        if item.is_file() and item.relative_to(target).as_posix() not in allowed:
            raise ValueError("文献目录存在未登记的人工文件，拒绝覆盖：" + target.name)


@contextmanager
def locked(output):
    lock = output / ".figures.lock"
    try:
        handle = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise ValueError("图库正在处理，或上次中断留下 .figures.lock；先确认没有运行进程。") from None
    os.close(handle)
    try:
        yield
    finally:
        lock.unlink(missing_ok=True)


def normalized_pdf(source, deps):
    """把旋转和 CropBox 统一成左下角为零的新页，后续坐标都按显示方向计算。"""
    _, PdfReader, PdfWriter, Transformation, RectangleObject, _ = deps
    reader = PdfReader(source)
    if reader.is_encrypted and not reader.decrypt(""):
        raise ValueError("PDF 已加密，当前工具不处理需要口令的文件")
    writer = PdfWriter()
    for original in reader.pages:
        page = writer.add_page(original)
        page.transfer_rotation_to_content()
        left, bottom, right, top = map(float, page.cropbox)
        if right <= left or top <= bottom:
            raise ValueError("PDF 页面尺寸无效")
        page.add_transformation(Transformation().translate(-left, -bottom))
        rectangle = RectangleObject((0, 0, right - left, top - bottom))
        page.mediabox = rectangle
        page.cropbox = RectangleObject(rectangle)
    content = io.BytesIO()
    writer.write(content)
    content.seek(0)
    return content


def lines(page):
    # 不能把同一高度的左右两栏合成一行，否则第二栏的 Fig. 图注会被吞掉。
    rows = []
    words = page.extract_words(x_tolerance=2, y_tolerance=3, extra_attrs=["size"])
    for word in sorted(words, key=lambda item: (round(item["top"] / 3), item["x0"])):
        target = next((row for row in reversed(rows)
                       if abs(row["top"] - word["top"]) < 3
                       and -1 <= word["x0"] - row["x1"] <= max(24, float(word.get("size", 10)) * 2)), None)
        if target:
            target["text"] += " " + word["text"]
            target["x1"] = max(target["x1"], word["x1"])
            target["bottom"] = max(target["bottom"], word["bottom"])
        else:
            rows.append({key: word[key] for key in ("text", "x0", "x1", "top", "bottom")})
    return rows


def primitives(page):
    return [item for group in (page.rects, page.curves, page.images, page.lines) for item in group
            if item.get("x1", 0) > item.get("x0", 0) or item.get("bottom", 0) > item.get("top", 0)]


def candidates(page, page_number):
    text_lines = lines(page)
    captions = []
    for item in text_lines:
        match = CAPTION.match(item["text"])
        if match:
            captions.append({"figure_number": match.group(1).upper(), "caption": item["text"],
                             "page": page_number, "line": item})
    objects = primitives(page)
    for caption in captions:
        line = caption["line"]
        # 短图注可能位于左栏或右栏；宽图注覆盖整页，不裁掉另一半子图。
        if line["x1"] - line["x0"] > page.width * .55:
            left, right = 0, page.width
        elif line["x0"] >= page.width / 2:
            left, right = page.width / 2, page.width
        else:
            left, right = 0, page.width
            if any(other["line"]["x0"] >= page.width / 2 and abs(other["line"]["top"] - line["top"]) < 50
                   for other in captions):
                right = page.width / 2
        previous = [other["line"]["bottom"] for other in captions
                    if other["line"]["top"] < line["top"] - 5
                    and other["line"]["x0"] < right and other["line"]["x1"] > left]
        lower_limit = max(previous, default=0)
        selected = [item for item in objects
                    if item["x0"] >= left - 2 and item["x1"] <= right + 2
                    and item["top"] >= lower_limit and item["bottom"] <= line["top"] + 1
                    and line["top"] - item["bottom"] < page.height * .65]
        if selected:
            # 轴名、刻度、图例常在边框以外；把图形上下邻近的文字一并包入候选区域。
            # 这仍是几何启发式，输出保持待复核，复杂排版可用 overrides 明确边界。
            graphic_top = min(item["top"] for item in selected)
            labels = [item for item in text_lines
                      if item is not line and item["top"] >= graphic_top - 15
                      and item["bottom"] < line["top"] - 1
                      and item["x0"] >= left and item["x1"] <= right]
            selected = selected + labels
            bbox = [max(left, min(item["x0"] for item in selected) - 3),
                    max(0, min(item["top"] for item in selected) - 3),
                    min(right, max(item["x1"] for item in selected) + 3),
                    min(page.height, max(item["bottom"] for item in selected) + 3)]
            caption["segments"] = [{"page": page_number, "bbox": bbox}]
        else:
            caption["segments"] = []
    return captions


def validate_segments(segments, pages):
    if not isinstance(segments, list) or not segments:
        raise ValueError("每幅图必须有至少一个 segments 裁切范围；自动定位失败时请填写 overrides")
    validated = []
    for segment in segments:
        if not isinstance(segment, dict) or type(segment.get("page")) is not int or not 1 <= segment["page"] <= len(pages):
            raise ValueError("裁切 page 必须是从 1 开始的有效 PDF 页序")
        bbox = segment.get("bbox")
        if not isinstance(bbox, (list, tuple)) or len(bbox) != 4 or any(type(value) not in (int, float) or not math.isfinite(value) for value in bbox):
            raise ValueError("bbox 必须包含四个有限数值 [左,上,右,下]")
        left, top, right, bottom = map(float, bbox)
        page = pages[segment["page"] - 1]
        if not (0 <= left < right <= page.width and 0 <= top < bottom <= page.height):
            raise ValueError("裁切 bbox 越界或宽高为零")
        validated.append({"page": segment["page"], "bbox": [left, top, right, bottom]})
    return validated


def category(caption):
    for value, words in (("structure", ("architecture", "structure", "结构")),
                         ("workflow", ("flowchart", "workflow", "framework", "流程", "框架")),
                         ("system", ("system", "network", "系统", "网络")),
                         ("results", ("result", "comparison", "结果", "对比"))):
        if any(word in caption.lower() for word in words):
            return value
    return "other"


def save_crop_pdf(reader, segments, target, deps):
    _, _, PdfWriter, Transformation, RectangleObject, _ = deps
    writer = PdfWriter()
    for segment in segments:
        # 先复制进独立 writer，防止内容流变换意外影响仍需重复裁切的原页。
        page = writer.add_page(reader.pages[segment["page"] - 1])
        left, top, right, bottom = segment["bbox"]
        height = float(page.mediabox.height)
        page.add_transformation(Transformation().translate(-left, -(height - bottom)))
        page.mediabox = RectangleObject((0, 0, right - left, bottom - top))
        page.cropbox = RectangleObject(page.mediabox)
    with target.open("wb") as stream:
        writer.write(stream)


def build_paper(row, source, stage, previous, changes, dpi, deps):
    pdfplumber, PdfReader, _, _, _, Image = deps
    source_hash = digest(source)
    content = normalized_pdf(source, deps)
    reader = PdfReader(content)
    content.seek(0)
    result = {"schema_version": 1, "generator": GENERATOR, "paper": row, "source_sha256": source_hash,
              "extraction": {"status": "extracted_needs_review", "dpi": dpi, "warnings": []},
              "coverage": {"page_review_complete": False}, "figures": [], "pages": []}
    for name in ("figures", "thumbnails", "pages"):
        (stage / name).mkdir()
    with pdfplumber.open(content) as pdf:
        detected = []
        for index, page in enumerate(pdf.pages, 1):
            proof = "pages/page-%03d.png" % index
            page.to_image(resolution=100, antialias=True).original.convert("RGB").save(stage / proof)
            result["pages"].append({"page": index, "width": page.width, "height": page.height,
                                    "assets": {"proof": proof}, "asset_sha256": {"proof": digest(stage / proof)}})
            detected.extend(candidates(page, index))
        by_number = {}
        for item in detected:
            number = item["figure_number"]
            if number in by_number:
                result["extraction"]["warnings"].append("图号重复，需用 overrides 指定完整分段：" + number)
                continue
            by_number[number] = item
        updates = changes.get("figures", [])
        if not isinstance(updates, list):
            raise ValueError("overrides 的 figures 必须为数组")
        seen = set()
        for item in updates:
            if not isinstance(item, dict) or not isinstance(item.get("figure_number"), str) or not NUMBER.fullmatch(item["figure_number"]):
                raise ValueError("修正项必须有合法字符串 figure_number")
            number = item["figure_number"].upper()
            if number in seen:
                raise ValueError("同一文献的修正图号重复：" + number)
            seen.add(number)
            if item.get("exclude") is True:
                by_number.pop(number, None)
            else:
                by_number[number] = dict(by_number.get(number, {}), **item)
        old_by_id = {item["figure_id"]: item for item in previous.get("figures", [])}
        for number, item in by_number.items():
            if not item.get("segments"):
                result["extraction"]["warnings"].append("图 " + number + " 无法定位完整区域，请补充 overrides")
                continue
            segments = validate_segments(item["segments"], pdf.pages)
            token = "F" + number.replace(".", "-")
            figure_id = row["ledger_id"] + "-" + token
            if any(figure["figure_id"] == figure_id for figure in result["figures"]):
                raise ValueError("标准化后的图 ID 重复：" + figure_id)
            assets = {"png": "figures/" + token + ".png", "thumbnail": "thumbnails/" + token + ".png",
                      "pdf": "figures/" + token + ".pdf"}
            images, output_segments = [], []
            for offset, segment in enumerate(segments, 1):
                image = pdf.pages[segment["page"] - 1].crop(tuple(segment["bbox"])).to_image(
                    resolution=dpi, antialias=True).original.convert("RGB")
                png = "figures/%s-segment-%d.png" % (token, offset)
                crop = "figures/%s-segment-%d.pdf" % (token, offset)
                image.save(stage / png, dpi=(dpi, dpi))
                save_crop_pdf(reader, [segment], stage / crop, deps)
                images.append(image)
                output_segments.append(dict(segment, assets={"png": png, "pdf": crop},
                    asset_sha256={"png": digest(stage / png), "pdf": digest(stage / crop)}))
            if len(images) == 1:
                complete = images[0]
            else:
                gap = max(12, round(dpi * .06))
                complete = Image.new("RGB", (max(image.width for image in images), sum(image.height for image in images) + gap * (len(images) - 1)), "white")
                top = 0
                for image in images:
                    complete.paste(image, ((complete.width - image.width) // 2, top))
                    top += image.height + gap
            complete.save(stage / assets["png"], dpi=(dpi, dpi))
            thumbnail = complete.copy()
            thumbnail.thumbnail((480, 360))
            thumbnail.save(stage / assets["thumbnail"])
            save_crop_pdf(reader, segments, stage / assets["pdf"], deps)
            old = old_by_id.get(figure_id, {})
            same = (previous.get("source_sha256") == source_hash and old.get("source", {}).get("segments") == segments
                    and old.get("caption") == item.get("caption", "")
                    and all(old.get("asset_sha256", {}).get(key) == digest(stage / value) for key, value in assets.items()))
            method = old.get("review_method")
            verified = same and old.get("review_status") == "verified" and method in ("human", "ai")
            result["figures"].append({"figure_id": figure_id, "figure_number": number,
                "caption": item.get("caption", ""), "category": item.get("category", old.get("category", category(item.get("caption", "")))),
                "review_status": "verified" if verified else "needs_review", "review_method": method if verified else None,
                "annotations": copy.deepcopy(old.get("annotations", {"summary_zh": "", "reference_use_zh": "", "limitation_zh": ""})),
                "source": {"pages": list(dict.fromkeys(segment["page"] for segment in segments)), "segments": segments, "printed_pages": []},
                "segments": output_segments, "assets": assets,
                "dimensions": {"width": complete.width, "height": complete.height, "dpi": dpi},
                "asset_sha256": {key: digest(stage / value) for key, value in assets.items()}})
        count = len(result["figures"])
        verified_count = sum(figure["review_status"] == "verified" for figure in result["figures"])
        result["extraction"].update(figure_count=count, verified_count=verified_count)
        if not count:
            result["extraction"]["status"] = "no_caption_detected_needs_review"
        elif (verified_count == count and previous.get("coverage", {}).get("page_review_complete")
              and previous.get("source_sha256") == source_hash
              and {figure["figure_id"] for figure in previous.get("figures", [])} == {figure["figure_id"] for figure in result["figures"]}):
            result["coverage"] = copy.deepcopy(previous["coverage"])
            result["extraction"]["status"] = "complete_verified"
    write_json(stage / "figures.json", result)
    return result


def publish(stage, target, commit_scope=None):
    """同一磁盘内发布整篇结果，第二次重命名失败时把旧目录移回原位。"""
    backup = target.with_name(".previous-" + uuid.uuid4().hex)
    if target.exists():
        os.replace(target, backup)
    try:
        os.replace(stage, target)
        if commit_scope is not None:
            commit_scope()
    except BaseException:
        # 清单发布失败时新目录也撤回，不能留下新图片配旧清单。
        if target.exists() and not stage.exists():
            os.replace(target, stage)
        if backup.exists():
            os.replace(backup, target)
        raise
    else:
        if backup.exists():
            shutil.rmtree(backup)


def publish_scope(output, rows):
    temporary = output / (".scope-" + uuid.uuid4().hex + ".json")
    try:
        write_json(temporary, {"schema_version": 1, "generator": GENERATOR, "papers": list(rows.values())})
        os.replace(temporary, output / "scope.json")
    finally:
        temporary.unlink(missing_ok=True)


def extract(scope_path, output, overrides_path=None, ids=None, dpi=300, skip_existing=False):
    """读取范围清单 → 提取并暂存每篇 → 发布资产与图目；失败不覆盖该篇旧归档。"""
    scope_path = Path(scope_path).resolve()
    output = no_links(output)
    if type(dpi) is not int or not 36 <= dpi <= 1200:
        raise ValueError("dpi 必须是 36–1200 的整数，默认 300")
    rows = scope_rows(scope_path)
    generated_papers = output / "papers"
    for row in rows:
        for field in ("pdf_path", "note_path"):
            if row.get(field):
                source = Path(row[field]).expanduser()
                source = source if source.is_absolute() else scope_path.parent / source
                if source.resolve().is_relative_to(generated_papers.resolve()):
                    raise ValueError("原 PDF 和笔记不能位于即将重建的图库 papers 目录内")
    selected = set(ids) if ids else None
    if selected and selected - {row["ledger_id"] for row in rows}:
        raise ValueError("指定了不在 scope.json 中的文献 ID")
    changes = read_json(overrides_path) if overrides_path else {}
    if not isinstance(changes, dict) or not isinstance(changes.get("papers", {}), dict):
        raise ValueError("overrides 必须是含 papers 对象的 JSON")
    deps = dependencies()
    if output.exists() and not output.is_dir():
        raise ValueError("图库输出必须是目录")
    if output.exists() and any(output.iterdir()) and not (output / "scope.json").is_file():
        raise ValueError("拒绝在非空人工目录中创建图库；请指定独立的新目录")
    prior_scope = read_json(output / "scope.json") if (output / "scope.json").exists() else {}
    if prior_scope and prior_scope.get("generator") not in (None, GENERATOR):
        raise ValueError("已有 scope.json 不属于本工具")
    output.mkdir(parents=True, exist_ok=True)
    target_base = no_links(output / "papers")
    target_base.mkdir(exist_ok=True)
    report = {"ok": True, "papers": 0, "figure_count": 0, "skipped": [], "failures": [], "output": str(output)}
    prior_rows = {row["ledger_id"]: row for row in prior_scope.get("papers", [])}
    with locked(output):
        for row in rows:
            if any(key.casefold() == row["ledger_id"].casefold() and key != row["ledger_id"] for key in prior_rows):
                raise ValueError("文献 ID 与已有归档仅大小写不同，请使用已有 ID")
        if not (output / "scope.json").exists():
            publish_scope(output, prior_rows)
        for row in rows:
            if selected and row["ledger_id"] not in selected:
                continue
            ledger_id = row["ledger_id"]
            target = no_links(target_base / ledger_id)
            previous = read_json(target / "figures.json") if (target / "figures.json").is_file() else {}
            if target.exists() and previous.get("generator") != GENERATOR:
                raise ValueError("拒绝覆盖未标记的人工文献目录：" + ledger_id)
            if target.exists():
                check_owned_tree(target, previous)
            source = Path(row["pdf_path"]).expanduser()
            source = source if source.is_absolute() else scope_path.parent / source
            source = source.resolve()
            if source.is_relative_to(target):
                raise ValueError("原 PDF 不能存放在即将重建的生成目录中")
            rebased = relative_row(row, scope_path.parent, output)
            override = changes.get("papers", {}).get(ledger_id, {})
            if not isinstance(override, dict):
                raise ValueError("文献修正必须是对象：" + ledger_id)
            signature = hashlib.sha256(json.dumps(override, sort_keys=True).encode("utf-8")).hexdigest()
            if skip_existing and source.is_file() and previous.get("paper") == rebased and previous.get("source_sha256") == digest(source) and previous.get("overrides_sha256") == signature and previous.get("extraction", {}).get("dpi") == dpi:
                assets = recorded_assets(previous)
                if assets and all((target / value).is_file() and checksum and digest(target / value) == checksum for value, checksum in assets.items()):
                    report["skipped"].append(ledger_id)
                    prior_rows[ledger_id] = rebased
                    continue
            stage = Path(tempfile.mkdtemp(prefix=".figures-stage-", dir=target_base))
            try:
                if not source.is_file():
                    raise ValueError("原 PDF 不存在")
                result = build_paper(rebased, source, stage, previous, override, dpi, deps)
                result["overrides_sha256"] = signature
                write_json(stage / "figures.json", result)
                updated_rows = dict(prior_rows, **{ledger_id: rebased})
                publish(stage, target, lambda: publish_scope(output, updated_rows))
                prior_rows = updated_rows
                report["papers"] += 1
                report["figure_count"] += len(result["figures"])
            except Exception as error:
                report["ok"] = False
                message = str(error) if isinstance(error, ValueError) else "PDF 读取、渲染或归档失败（" + type(error).__name__ + "）"
                report["failures"].append({"ledger_id": ledger_id, "error": message})
            finally:
                if stage.exists():
                    shutil.rmtree(stage)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--overrides", type=Path)
    parser.add_argument("--ids", nargs="*")
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()
    report = extract(args.scope, args.output, args.overrides, args.ids, args.dpi, args.skip_existing)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
