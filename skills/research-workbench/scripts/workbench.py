"""本地科研记录工具；仅使用 Python 标准库，不发送网络请求。"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import hashlib
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import uuid

VERSION = "0.1.0a5"
BACKUP_LIMIT = 64 * 1024 * 1024
BACKUP_CORE = ("config.json", "PERSONAL_NOTES.md", "PROJECT_MANUAL.md")
STATUSES = ("已确认", "进行中", "计划中", "候选方案", "待确认", "AI建议")
TASK_STATES = ("todo", "in_progress", "done", "cancelled")
RELATIONS = ("references", "informs", "depends_on")
KINDS = ("progress", "task", "decision", "issue", "experiment", "material", "checkpoint", "paper")


def encode(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def atomic_write(path, content):
    """先写临时文件，再替换目标；失败时旧文件仍然存在。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".rwa-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def bounded(root, relative):
    path = root / relative
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("路径越出工作台边界：" + relative)
    return path


@contextmanager
def locked(root):
    path = bounded(root, ".write.lock")
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise ValueError("工作台正在写入或上次异常退出留下 .write.lock；确认没有写入进程后再移走锁文件。") from None
    try:
        os.close(fd)
        yield
    finally:
        path.unlink()


def required_text(data, key):
    if not isinstance(data.get(key), str) or not data[key].strip():
        raise ValueError("缺少非空文本字段：" + key)


def normalize_doi(value):
    """统一常见 DOI 输入形式；只校验格式，不联网验证存在性。"""
    value = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", value.strip(), flags=re.I).lower()
    if not re.fullmatch(r"10\.\d{4,9}/\S+", value):
        raise ValueError("DOI 格式无效；未知 DOI 请省略该字段")
    return value


def validate(data):
    if not isinstance(data, dict):
        raise ValueError("记录必须是 JSON 对象")
    allowed = {"kind", "status", "title", "body", "evidence", "next_step", "paper", "supersedes", "task_state", "links"}
    if set(data) - allowed:
        raise ValueError("未知字段：" + ", ".join(sorted(set(data) - allowed)))
    for key in ("kind", "status", "title", "body"):
        required_text(data, key)
    if data["kind"] not in KINDS or data["status"] not in STATUSES:
        raise ValueError("无效的 kind 或 status")
    evidence = data.get("evidence", [])
    if not isinstance(evidence, list) or any(not isinstance(x, str) or not x.strip() for x in evidence):
        raise ValueError("evidence 必须是非空字符串组成的数组")
    if data["status"] == "已确认" and not evidence:
        raise ValueError("已确认记录必须提供 evidence；工具不替用户判断证据真实性")
    links = data.get("links", [])
    if not isinstance(links, list):
        raise ValueError("links 必须是关联对象数组")
    seen_links = set()
    for link in links:
        if not isinstance(link, dict) or set(link) != {"target", "relation", "reason"}:
            raise ValueError("每条关联必须包含 target、relation、reason")
        for key in link:
            required_text(link, key)
        if not re.fullmatch(r"[0-9a-f]{32}", link["target"]) or link["relation"] not in RELATIONS:
            raise ValueError("关联目标 ID 或关系类型无效")
        pair = (link["target"], link["relation"])
        if pair in seen_links:
            raise ValueError("同一目标和关系不能重复")
        seen_links.add(pair)
    if "task_state" in data:
        if data["kind"] != "task" or data["task_state"] not in TASK_STATES:
            raise ValueError("task_state 仅用于 task，取值为 todo/in_progress/done/cancelled")
        if data["task_state"] == "done" and not evidence:
            raise ValueError("完成任务必须提供 evidence；不自动判定证据真实性")
    for key in ("next_step", "supersedes"):
        if key in data:
            required_text(data, key)
    if data["kind"] == "checkpoint":
        required_text(data, "next_step")
    if data["kind"] == "paper":
        paper = data.get("paper")
        if not isinstance(paper, dict):
            raise ValueError("文献记录必须有 paper 对象")
        required = {"source", "reading_basis", "summary", "limitations"}
        optional = {"authors", "year", "doi", "venue", "tags"}
        if not required <= set(paper) or set(paper) - required - optional:
            raise ValueError("paper 缺少必填字段或包含未知字段")
        for key in required | (set(paper) & {"doi", "venue"}):
            required_text(paper, key)
        for key in ("authors", "tags"):
            if key in paper and (not isinstance(paper[key], list) or any(not isinstance(x, str) or not x.strip() for x in paper[key])):
                raise ValueError(key + " 必须为字符串数组")
        if "year" in paper and (type(paper["year"]) is not int or not 1000 <= paper["year"] <= 9999):
            raise ValueError("year 必须为四位整数年份")
        if "doi" in paper:
            normalize_doi(paper["doi"])
        if paper["reading_basis"] not in ("metadata", "abstract", "full_text"):
            raise ValueError("reading_basis 必须为 metadata、abstract 或 full_text")
    elif "paper" in data:
        raise ValueError("只有 paper 类型可包含 paper 字段")


def load(root):
    config = read_json(bounded(root, "config.json"))
    if not isinstance(config, dict) or config.get("schema_version") != 1:
        raise ValueError("不支持的工作台 schema_version")
    required_text(config, "name")
    if not bounded(root, "events").is_dir():
        raise ValueError("原始事件目录 events 缺失；请从备份恢复，不要按空工作台继续")
    rows = []
    for path in sorted(bounded(root, "events").glob("*.json")):
        row = read_json(bounded(root, "events/" + path.name))
        if not isinstance(row, dict) or set(row) != {"id", "created_at", "schema_version", "record"}:
            raise ValueError("无效事件：" + path.name)
        if row["schema_version"] != 1 or row["id"] != path.stem or not re.fullmatch(r"[0-9a-f]{32}", row["id"]):
            raise ValueError("无效事件标识：" + path.name)
        datetime.fromisoformat(row["created_at"])
        validate(row["record"])
        rows.append(row)
    rows.sort(key=lambda row: (row["created_at"], row["id"]))
    known = set()
    replaced = set()
    for row in rows:
        previous = row["record"].get("supersedes")
        if previous and (previous not in known or previous in replaced):
            raise ValueError("supersedes 必须指向尚未被替代的历史记录")
        if previous:
            replaced.add(previous)
        if any(link["target"] not in known for link in row["record"].get("links", [])):
            raise ValueError("关联必须指向先前已存在的事件，不能自引或悬空")
        known.add(row["id"])
    return config, rows


def current(rows):
    replaced = {row["record"].get("supersedes") for row in rows}
    return [row for row in rows if row["id"] not in replaced]


def tasks(rows, state="open"):
    """旧任务不推断完成情况，归为 unspecified 并列入未关闭任务。"""
    result = []
    for row in current(rows):
        data = row["record"]
        actual = data.get("task_state", "unspecified")
        if data["kind"] == "task" and (state == "all" or state == actual or
                (state == "open" and actual not in ("done", "cancelled"))):
            result.append(row)
    return result


def brief(row):
    """断点只保留有界导航；全文仍在原始事件中。"""
    data = row["record"]
    title = " ".join(data["title"].split())[:120]
    body = " ".join(data["body"].split())[:240]
    return (f"- [{data['status']}] {title} ({data.get('task_state', data['kind'])})\n"
            f"  {body}\n  [完整记录](events/{row['id']}.json)\n")


def relationship_graph(rows):
    """当前记录的显式关联；保留引用的准确历史版本，不静默重定向。"""
    live = current(rows)
    live_ids = {row["id"] for row in live}
    edges = [dict(source=row["id"], **link) for row in live for link in row["record"].get("links", [])]
    included = live_ids | {edge["target"] for edge in edges}
    successors = {row["record"]["supersedes"]: row["id"] for row in rows if row["record"].get("supersedes")}
    nodes = []
    for row in rows:
        if row["id"] not in included:
            continue
        latest = row["id"]
        while latest in successors:
            latest = successors[latest]
        nodes.append({"id": row["id"], "title": row["record"]["title"], "kind": row["record"]["kind"],
                      "status": row["record"]["status"], "is_current": row["id"] in live_ids, "latest_id": latest})
    return {"nodes": nodes, "edges": edges,
            "note": "仅展示显式记录的关系，不代表已验证的因果关系或科学证据"}


def related(rows, identifier):
    if identifier not in {row["id"] for row in rows}:
        raise ValueError("找不到事件 ID：" + identifier)
    graph = relationship_graph(rows)
    return {"id": identifier,
            "outgoing": [edge for edge in graph["edges"] if edge["source"] == identifier],
            "incoming": [edge for edge in graph["edges"] if edge["target"] == identifier],
            "note": "仅查询当前来源记录的关联；历史来源的关联请读取其原始事件。目标版本不自动替换。"}


def section(row, prefix=""):
    data = row["record"]
    result = f"## [{data['status']}] {data['title']}\n\n{data['body']}\n\n"
    result += f"类型：{data['kind']} · ID：{row['id']} · UTC：{row['created_at']}\n\n"
    if data["kind"] == "task":
        result += "任务状态：" + data.get("task_state", "unspecified（旧记录未指定）") + "\n\n"
    if data.get("next_step"):
        result += "下一步：" + data["next_step"] + "\n\n"
    if data.get("evidence"):
        result += "证据（引用不等于已核验）：\n\n" + "\n".join("- " + x for x in data["evidence"]) + "\n\n"
    if data.get("links"):
        result += "显式关联（不自动验证）：\n\n" + "".join(
            f"- {link['relation']} → [{link['target']}]({prefix}events/{link['target']}.json)：{link['reason']}\n"
            for link in data["links"]) + "\n"
    if "paper" in data:
        paper = data["paper"]
        for key, label in (("authors", "作者"), ("year", "年份"), ("doi", "DOI"), ("venue", "期刊/会议"), ("tags", "标签")):
            if key in paper:
                value = ", ".join(paper[key]) if isinstance(paper[key], list) else str(paper[key])
                result += label + "：" + value + "\n\n"
        result += f"来源：{paper['source']}\n\n阅读依据：{paper['reading_basis']}\n\n摘要笔记：{paper['summary']}\n\n局限：{paper['limitations']}\n\n人工阅读状态：未由工具确认\n\n"
    return result


def views(config, rows):
    banner = "> 自动生成，请通过 record 追加或修订；手写内容请放到 PERSONAL_NOTES.md。\n\n"
    live = current(rows)
    checkpoints = [row for row in live if row["record"]["kind"] == "checkpoint"]
    active = (brief(checkpoints[-1]) + "\n下一步：" + " ".join(checkpoints[-1]["record"]["next_step"].split())[:500] + "\n\n"
              if checkpoints else "尚无断点，请记录当前目标和下一步。\n\n")
    active += "最近进展（最多 5 条；完整记录见 CURRENT_STATUS.md 和 WORKLOG.md）：\n\n"
    recent = [row for row in live if row["record"]["kind"] not in ("checkpoint", "paper")][-5:]
    active += "".join(brief(row) for row in recent)
    open_tasks = tasks(rows)
    active += f"\n未关闭任务：{len(open_tasks)} 项（最多展示 5 项；完整清单见 TASKS.md）。\n\n"
    active += "".join(brief(row) for row in open_tasks[:5])
    result = {
        "ACTIVE_CONTEXT.md": "# " + config["name"] + "：续接断点\n\n" + banner + active,
        "CURRENT_STATUS.md": "# 当前记录\n\n" + banner + "".join(section(row) for row in live),
        "WORKLOG.md": "# 历史记录（含被替代版本）\n\n" + banner + "".join(section(row) for row in rows),
        "LEDGERS.md": "# 分类台账\n\n" + banner + "".join("# " + kind + "\n\n" + "".join(section(row) for row in live if row["record"]["kind"] == kind) for kind in KINDS),
    }
    result["TASKS.md"] = "# 任务清单\n\n" + banner + "".join(
        "# " + state + "\n\n" + "".join(section(row) for row in tasks(rows, state))
        for state in (*TASK_STATES, "unspecified"))
    papers = [row for row in live if row["record"]["kind"] == "paper"]
    result["PAPER_INDEX.md"] = "# 当前文献目录\n\n" + banner + "".join(
        "- " + row["record"]["title"].replace("\n", " ") + " — [笔记](notes/" + row["id"] + ".md) · "
        + str(row["record"]["paper"].get("year", "年份未知")) + "\n" for row in papers)
    graph = relationship_graph(rows)
    result["RELATIONS.json"] = encode(graph)
    labels = {node["id"]: " ".join(node["title"].split())[:120] for node in graph["nodes"]}
    result["RELATIONS.md"] = "# 显式关联清单\n\n" + banner + graph["note"] + "\n\n" + "".join(
        f"- {labels[edge['source']]} [来源](events/{edge['source']}.json) — {edge['relation']} → "
        f"{labels[edge['target']]} [目标版本](events/{edge['target']}.json)\n  理由：{edge['reason']}\n"
        for edge in graph["edges"])
    historical = [node for node in graph["nodes"] if not node["is_current"]]
    if historical:
        result["RELATIONS.md"] += "\n## 引用了旧版本，需人工核对\n\n" + "".join(
            f"- {node['id']} → [最新版本](events/{node['latest_id']}.json)（原关联未自动改变）\n" for node in historical)
    for row in rows:
        if row["record"]["kind"] == "paper":
            result["notes/" + row["id"] + ".md"] = banner + section(row, prefix="../")
            result["notes/" + row["id"] + ".json"] = encode(row)
    return result


def render(root):
    config, rows = load(root)
    outputs = views(config, rows)
    # 写入前先检查所有路径，防止外部符号链接导致部分越界写入。
    paths = {name: bounded(root, name) for name in outputs}
    for name, content in outputs.items():
        atomic_write(paths[name], content)


def initialize(root, name):
    if not name.strip():
        raise ValueError("项目名称不能为空")
    root.mkdir(parents=True, exist_ok=False)
    (root / "events").mkdir()
    atomic_write(root / "config.json", encode({"schema_version": 1, "name": name}))
    atomic_write(root / ".gitignore", "*\n!.gitignore\n")
    atomic_write(root / "PERSONAL_NOTES.md", "# 手写笔记\n\n这个文件不会被工具重新生成。\n")
    atomic_write(root / "PROJECT_MANUAL.md", "# 项目约定\n\n在这里填写范围、证据规则和资料位置；工具不会覆盖本文件。\n")
    render(root)


def record(root, data):
    validate(data)
    # 复制后规范化，避免修改调用者持有的输入对象。
    data = json.loads(encode(data))
    if data["kind"] == "paper" and "doi" in data["paper"]:
        data["paper"]["doi"] = normalize_doi(data["paper"]["doi"])
    with locked(root):
        _, rows = load(root)
        previous = data.get("supersedes")
        if previous and previous not in {row["id"] for row in current(rows)}:
            raise ValueError("supersedes 必须指向当前有效记录的 ID")
        if any(link["target"] not in {row["id"] for row in rows} for link in data.get("links", [])):
            raise ValueError("关联目标尚不存在，请先入库目标记录")
        doi = data.get("paper", {}).get("doi")
        if doi:
            for existing in current(rows):
                old_doi = existing["record"].get("paper", {}).get("doi")
                if old_doi and normalize_doi(old_doi) == doi and existing["id"] != previous:
                    raise ValueError("DOI 已入库，ID=" + existing["id"] + "；更新笔记请使用 supersedes，不能重复新增")
        row = {"schema_version": 1, "id": uuid.uuid4().hex,
               "created_at": datetime.now(timezone.utc).isoformat(), "record": data}
        atomic_write(bounded(root, "events/" + row["id"] + ".json"), encode(row))
        # 事件已保存；如果视图失败，提示 ID，避免重试造成重复事件。
        try:
            render(root)
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise ValueError(f"记录已保存，ID={row['id']}；视图更新失败，请修复后执行 render，不要重复 record：{error}") from error
        return row["id"]


def audit(root):
    config, rows = load(root)
    stale = [name for name, value in views(config, rows).items()
             if not bounded(root, name).exists() or bounded(root, name).read_text(encoding="utf-8") != value]
    return {"events": len(rows), "current": len(current(rows)), "stale_views": stale,
            "note": "仅检查结构与视图一致性，不代表已验证科研结论或证据真实性"}


def backup_name(name):
    return isinstance(name, str) and (name in BACKUP_CORE or
            re.fullmatch(r"events/[0-9a-f]{32}\.json", name) is not None)


def backup(root, output):
    """只保存受管理的原始记录和手写文件，不打包论文、密钥或派生视图。"""
    output = output.absolute()
    if output.resolve().is_relative_to(root.resolve()):
        raise ValueError("备份文件必须放在工作台目录之外")
    with locked(root):
        _, rows = load(root)
        names = list(BACKUP_CORE) + ["events/" + row["id"] + ".json" for row in rows]
        if len(names) > 10000:
            raise ValueError("备份最多支持 10000 个文件")
        files = {}
        total = 0
        for name in names:
            path = bounded(root, name)
            if not path.exists() and name != "config.json":
                if name in BACKUP_CORE:
                    continue
            total += path.stat().st_size
            if total > BACKUP_LIMIT:
                raise ValueError("备份超过 64 MiB 限制，请改用可信文件备份工具")
            raw = path.read_bytes()
            files[name] = {"text": raw.decode("utf-8"), "sha256": hashlib.sha256(raw).hexdigest()}
        content = encode({"backup_version": 1, "files": files})
        if len(content.encode("utf-8")) > BACKUP_LIMIT:
            raise ValueError("备份文件超过 64 MiB 限制")
        # 排他创建：已有备份（包括同名链接）绝不被覆盖。
        with output.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        return {"files": len(files), "events": len(rows), "output": str(output),
                "warning": "未加密；仅含配置、事件、PERSONAL_NOTES、PROJECT_MANUAL，不含论文和其他自建文件"}


def restore(archive, root):
    """验证全部内容后恢复到新目录；不执行备份中的任何内容。"""
    if root.exists() or root.is_symlink():
        raise ValueError("恢复目标必须是尚不存在的新目录")
    if archive.stat().st_size > BACKUP_LIMIT:
        raise ValueError("备份文件超过 64 MiB 限制")
    payload = read_json(archive)
    if not isinstance(payload, dict) or set(payload) != {"backup_version", "files"} or type(payload["backup_version"]) is not int or payload["backup_version"] != 1:
        raise ValueError("不支持的备份格式")
    files = payload["files"]
    if not isinstance(files, dict) or not 1 <= len(files) <= 10000 or "config.json" not in files:
        raise ValueError("备份文件清单无效")
    for name, entry in files.items():
        if not backup_name(name) or not isinstance(entry, dict) or set(entry) != {"text", "sha256"} or not isinstance(entry["text"], str):
            raise ValueError("备份含非法文件路径或内容")
        if hashlib.sha256(entry["text"].encode("utf-8")).hexdigest() != entry["sha256"]:
            raise ValueError("备份完整性校验失败：" + name)
    # 在隔离临时目录验证事件结构并重建视图，验证失败不创建恢复目标。
    with tempfile.TemporaryDirectory(prefix="rwa-restore-") as temporary:
        stage = Path(temporary)
        (stage / "events").mkdir()
        for name, entry in files.items():
            atomic_write(stage / name, entry["text"])
        config, rows = load(stage)
        atomic_write(stage / ".gitignore", "*\n!.gitignore\n")
        render(stage)
        # copytree 默认拒绝现有目标；磁盘失败可能留下不完整的新目录，绝不覆盖旧项目。
        shutil.copytree(stage, root)
    return {"events": len(rows), "name": config["name"], "root": str(root)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=VERSION)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("init", "record", "resume", "render", "audit", "search", "tasks", "backup", "restore", "graph", "related"):
        sub = commands.add_parser(command)
        sub.add_argument("--root", type=Path, required=True, help="工作台目录，不是技能安装目录")
        if command == "init":
            sub.add_argument("--name", required=True)
        elif command == "record":
            sub.add_argument("--input", type=Path, required=True, help="UTF-8 JSON 记录")
        elif command == "search":
            sub.add_argument("--query", required=True)
            sub.add_argument("--kind", choices=KINDS)
        elif command == "tasks":
            sub.add_argument("--state", choices=("open", "all", "unspecified", *TASK_STATES), default="open")
        elif command == "backup":
            sub.add_argument("--output", type=Path, required=True)
        elif command == "restore":
            sub.add_argument("--input", type=Path, required=True)
        elif command == "related":
            sub.add_argument("--id", required=True, help="精确事件 ID，不自动跳到最新版本")
    args = parser.parse_args(argv)
    try:
        root = args.root.absolute() if args.command == "restore" else args.root.resolve()
        if args.command == "init":
            initialize(root, args.name)
            print("工作台已创建：" + str(root))
        elif args.command == "record":
            print(record(root, read_json(args.input)))
        elif args.command == "render":
            with locked(root):
                render(root)
            print("视图已重建；历史记录未修改。")
        elif args.command == "resume":
            # 轻量续接只读取断点；完整一致性检查按需 audit。
            print(bounded(root, "ACTIVE_CONTEXT.md").read_text(encoding="utf-8"))
        elif args.command == "audit":
            report = audit(root)
            print(encode(report))
            return 1 if report["stale_views"] else 0
        elif args.command == "search":
            _, rows = load(root)
            for row in current(rows):
                if (not args.kind or row["record"]["kind"] == args.kind) and args.query.casefold() in encode(row).casefold():
                    print(encode(row))
        elif args.command == "tasks":
            _, rows = load(root)
            print(encode(tasks(rows, args.state)))
        elif args.command == "backup":
            print(encode(backup(root, args.output)))
        elif args.command == "restore":
            print(encode(restore(args.input, root)))
        elif args.command in ("graph", "related"):
            _, rows = load(root)
            print(encode(relationship_graph(rows) if args.command == "graph" else related(rows, args.id)))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print("错误：" + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
