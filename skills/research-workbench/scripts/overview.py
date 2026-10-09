"""把已有记录整理成一个离线 HTML 快照；不保存记录、不请求网络。"""
import base64
from datetime import datetime, timezone
import hashlib
from html import escape
from pathlib import Path
import re
from urllib.parse import quote, urlsplit


OWNER_MARKER = "<!-- research-workbench-overview:v1 -->"
TASK_LABELS = {"todo": "待办", "in_progress": "执行中", "done": "完成",
               "cancelled": "取消", "unspecified": "状态未指定"}
CANDIDATE_LABELS = {"pending": "待筛选", "kept": "保留", "excluded": "排除", "noted": "已有笔记"}
READING_LABELS = {"metadata": "元数据", "abstract": "摘要", "full_text": "全文"}
RELATION_LABELS = {"references": "引用", "informs": "提供参考", "depends_on": "依赖"}
FIXED_LOCAL_FILES = {"PROJECT_MANUAL.md", "PERSONAL_NOTES.md", "ACTIVE_CONTEXT.md",
                     "CURRENT_STATUS.md", "WORKLOG.md", "TASKS.md", "PAPER_INDEX.md",
                     "CANDIDATES.md", "RELATIONS.md", "DECISIONS_AND_ISSUES.md"}


def text(value, fallback="未知"):
    """缺失信息显示未知；所有显示文字随后统一进行 HTML 转义。"""
    if value is None or value == "" or value == []:
        return fallback
    if isinstance(value, list):
        return "、".join(str(item) for item in value) or fallback
    return str(value)


def html(value, fallback="未知"):
    return escape(text(value, fallback), quote=True)


def short(value, limit=240):
    value = " ".join(text(value).split())
    return value if len(value) <= limit else value[:limit] + "…"


def event_path(identifier, known_ids):
    if isinstance(identifier, str) and re.fullmatch(r"[0-9a-f]{32}", identifier) and identifier in known_ids:
        return "events/" + identifier + ".json"
    return None


def note_path(identifier, note_ids):
    if isinstance(identifier, str) and re.fullmatch(r"[0-9a-f]{32}", identifier) and identifier in note_ids:
        return "notes/" + identifier + ".md"
    return None


def source_url(value, known_ids, note_ids):
    """仅生成 HTTP(S)、DOI 或明确允许的工作台相对链接。"""
    if not isinstance(value, str) or not value:
        return None
    value = value.strip()
    if any(character.isspace() or ord(character) < 32 for character in value) or "\\" in value:
        return None
    if value.startswith("event:"):
        return event_path(value[6:], known_ids)
    if value.startswith("file:"):
        local = value[5:]
        if local in FIXED_LOCAL_FILES:
            return local
        event = re.fullmatch(r"events/([0-9a-f]{32})\.json", local)
        note = re.fullmatch(r"notes/([0-9a-f]{32})\.md", local)
        return event_path(event[1], known_ids) if event else note_path(note[1], note_ids) if note else None
    doi = re.sub(r"^doi:", "", value, flags=re.IGNORECASE)
    if re.fullmatch(r"10\.\d{4,9}/\S+", doi):
        return "https://doi.org/" + quote(doi, safe="/")
    try:
        url = urlsplit(value)
        if (url.scheme.casefold() in ("http", "https") and url.hostname
                and url.username is None and url.password is None):
            url.port  # 无效端口不能产生可点击来源。
            return value
    except ValueError:
        pass
    return None


def anchor(url, label):
    if not url:
        return html(label)
    external = ' target="_blank" rel="noopener noreferrer" referrerpolicy="no-referrer"' if url.casefold().startswith(("http:", "https:")) else ""
    return '<a href="' + escape(url, quote=True) + '"' + external + ">" + html(label) + "</a>"


def _timestamp(generated_at):
    if generated_at is None:
        stamp = datetime.now(timezone.utc)
    elif isinstance(generated_at, datetime):
        stamp = generated_at
    elif isinstance(generated_at, str):
        stamp = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    else:
        raise ValueError("总览生成时间必须是带时区的日期时间")
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("总览生成时间必须包含时区")
    return stamp.astimezone(timezone.utc).isoformat(timespec="seconds")


def _csp(template):
    """只允许本模板里的固定 CSS/JS；资料文字从不进入脚本。"""
    script = re.findall(r"<script>([\s\S]*?)</script>", template)
    style = re.findall(r"<style>([\s\S]*?)</style>", template)
    if len(script) != 1 or len(style) != 1:
        raise ValueError("总览模板必须各有一个内嵌脚本和样式")

    def digest(value):
        return base64.b64encode(hashlib.sha256(value.encode("utf-8")).digest()).decode("ascii")

    return ("default-src 'none'; script-src 'sha256-" + digest(script[0]) + "'; style-src 'sha256-" +
            digest(style[0]) + "'; connect-src 'none'; img-src 'none'; object-src 'none'; "
            "base-uri 'none'; form-action 'none'")


def render_overview(config, rows, *, current_rows, candidate_state, relations, generated_at=None):
    """返回页面文字。当前记录、候选和关系均由工作台现有函数计算后传入。"""
    stamp = _timestamp(generated_at)
    known = {row["id"]: row for row in rows}
    known_ids = set(known)
    live = list(current_rows)
    papers = [row for row in live if row["record"].get("kind") == "paper"]
    note_ids = {row["id"] for row in rows if row["record"].get("kind") == "paper"}
    nodes = {node["id"]: node for node in relations.get("nodes", [])}
    queue = list(candidate_state)

    def provenance(row):
        data = row["record"]
        pieces = ['<details class="provenance"><summary>依据与原记录</summary>',
                  '<p class="muted">记录时间：' + html(row.get("created_at")) + "</p>",
                  "<p>" + anchor(event_path(row["id"], known_ids), "原事件（JSON）") + " · " +
                  '<span class="identifier">' + html(row["id"]) + "</span></p>"]
        if data.get("supersedes"):
            pieces.append("<p>修订自历史版本：" + anchor(event_path(data["supersedes"], known_ids),
                                                    data["supersedes"]) + "</p>")
        evidence = data.get("evidence", [])
        pieces.append('<p class="muted">证据入口仅表示原记录的引用，不代表已核验真实性。</p>')
        if evidence:
            pieces.append('<ul class="evidence">' + "".join(
                "<li>" + anchor(source_url(value, known_ids, note_ids), value) + "</li>" for value in evidence) + "</ul>")
        else:
            pieces.append('<p class="muted">未记录证据入口。</p>')
        confirmation = data.get("confirmation")
        if isinstance(confirmation, dict):
            pieces.append("<p>用户确认出处（记录者声明）：" + html(confirmation.get("reference")) + "</p>")
        for link in data.get("links", []):
            target = link.get("target")
            node = nodes.get(target, {})
            target_title = known.get(target, {}).get("record", {}).get("title", target)
            pieces.append('<p class="relation">显式关联：' + html(RELATION_LABELS.get(link.get("relation"), link.get("relation"))) +
                          " → " + anchor(event_path(target, known_ids), target_title) + "；理由：" + html(link.get("reason")))
            if node.get("is_current") is False:
                pieces.append(' <span class="history">历史目标；' +
                              anchor(event_path(node.get("latest_id"), known_ids), "查看最新版本") +
                              "，原引用仍指向历史记录。</span>")
            pieces.append("</p>")
        pieces.append("</details>")
        return "".join(pieces)

    def row_card(row, scope, extra="", state=""):
        data = row["record"]
        return ('<article class="card" data-card="' + scope + '" data-state="' + html(state, "") +
                '" data-status="' + html(data.get("status"), "未知") + '" data-record-id="' + html(row["id"]) + '">' +
                '<div class="card-heading"><h3>' + html(data.get("title")) + '</h3><span class="badge">研究状态：' +
                html(data.get("status")) + '</span></div><p class="body">' + html(short(data.get("body"))) + "</p>" +
                extra + provenance(row) + "</article>")

    def group(title, cards, css=""):
        return ('<div class="card-group ' + css + '" data-group><h3 class="group-title">' + html(title) +
               ' <span class="group-count">' + str(len(cards)) + '</span></h3><div class="cards">' + "".join(cards) +
               '</div><p class="empty" data-empty' + (' hidden' if cards else '') + ">暂无符合条件的条目。</p></div>")

    def section(scope, title, intro, content):
        return ('<section class="panel" data-scope="' + scope + '"><div class="section-heading"><h2>' +
                html(title) + '</h2><p class="muted">' + html(intro) + "</p></div>" + content + "</section>")

    checkpoints = [row for row in live if row["record"].get("kind") == "checkpoint"]
    checkpoints.sort(key=lambda row: (row.get("created_at", ""), row["id"]))
    latest = checkpoints[-1] if checkpoints else None
    checkpoint_cards = []
    if latest:
        next_step = '<div class="next-step"><strong>下一步</strong><p>' + html(short(latest["record"].get("next_step"), 500)) + "</p></div>"
        checkpoint_cards.append(row_card(latest, "checkpoint", next_step))
    current = section("checkpoint", "当前目标与下一步", "仅展示最新的当前有效断点；没有记录时不推断目标。",
                      group("最新断点", checkpoint_cards))
    recent = sorted((row for row in live if row["record"].get("kind") == "progress"),
                    key=lambda row: (row.get("created_at", ""), row["id"]), reverse=True)[:5]
    progress = section("progress", "最近进展", "最多展示 5 条当前有效的 progress 进展记录；完整历史见 WORKLOG.md。",
                       group("最近进展记录", [row_card(row, "progress") for row in recent]))

    tasks = [row for row in live if row["record"].get("kind") == "task"]
    task_groups = []
    for state, label in TASK_LABELS.items():
        selected = [row for row in tasks if row["record"].get("task_state", "unspecified") == state]
        selected.sort(key=lambda row: (row.get("created_at", ""), row["id"]), reverse=True)
        task_groups.append(group(label, [row_card(row, "tasks", '<p class="task-state">执行情况：' + label +
                                                "</p>", state) for row in selected], "task-column"))
    task_section = section("tasks", "任务分组", "执行情况和研究状态分别显示；完成任务不等于研究结论已确认。",
                           '<div class="task-board">' + "".join(task_groups) + "</div>")

    review_ids = {}
    for row in rows:
        candidate = row["record"].get("candidate")
        if row["record"].get("kind") == "candidate_review" and isinstance(candidate, dict):
            review_ids[candidate.get("doi")] = row["id"]

    def candidate_card(item):
        state = item.get("state", "pending")
        doi = item.get("doi")
        source = known.get(item.get("discovery_id"), {}).get("record", {}).get("discovery", {})
        paper_link = note_path(item.get("note_id"), note_ids)
        parts = ['<article class="card" data-card="candidates" data-state="' + html(state) +
                 '" data-status="" data-doi="' + html(doi) + '"><div class="card-heading"><h3>' +
                 html(item.get("title")) + '</h3><span class="badge">候选状态：' +
                 html(CANDIDATE_LABELS.get(state, state)) + "</span></div>",
                 '<p class="metadata">作者：' + html(item.get("authors")) + " · 年份：" + html(item.get("year")) +
                 " · 来源刊物：" + html(item.get("venue")) + "</p>",
                 "<p>DOI：" + anchor(source_url(doi, known_ids, note_ids), doi) + "</p>",
                 '<p class="body">摘要：' + html(short(item.get("abstract"))) + "</p>",
                 "<p>筛选决定：" + html(CANDIDATE_LABELS.get(item.get("decision"), item.get("decision"))) +
                 "；理由：" + html(item.get("review_reason")) + "</p>"]
        if state == "noted":
            parts.append('<p class="notice">已有同 DOI 的当前笔记，不代表人工已读。 ' +
                         anchor(paper_link, "打开笔记") + "</p>")
        parts.extend(['<details class="provenance"><summary>检索来源与原记录</summary>',
                      "<p>检索来源：" + html(source.get("source")) + "；检索词：" + html(item.get("query")) + "</p>",
                      "<p>检索时间：" + html(item.get("retrieved_at")) + "</p>",
                      "<p>" + anchor(event_path(item.get("discovery_id"), known_ids), "原检索事件（JSON）") + "</p>",
                      "<p>" + anchor(source_url(source.get("request_url"), known_ids, note_ids), "检索请求来源") + "</p>"])
        if doi in review_ids:
            parts.append("<p>" + anchor(event_path(review_ids[doi], known_ids), "最近筛选事件（JSON）") + "</p>")
        parts.append("</details></article>")
        return "".join(parts)

    candidate_section = section("candidates", "候选文献", "每条对应候选队列里的一个 DOI；筛选决定与已有笔记状态分别保留。",
                                group("候选条目", [candidate_card(item) for item in queue]))
    note_cards = []
    for row in sorted(papers, key=lambda row: (row.get("created_at", ""), row["id"]), reverse=True):
        paper = row["record"].get("paper", {})
        extra = ('<p class="metadata">作者：' + html(paper.get("authors")) + " · 年份：" + html(paper.get("year")) +
                 " · 来源刊物：" + html(paper.get("venue")) + "</p><p>读取依据：" +
                 html(READING_LABELS.get(paper.get("reading_basis"), paper.get("reading_basis"))) +
                 ' <span class="muted">（字段 reading_basis，不是人工阅读确认）</span></p>' +
                 "<p>资料出处：" + anchor(source_url(paper.get("source"), known_ids, note_ids), paper.get("source")) + "</p>" +
                 "<p>DOI：" + anchor(source_url(paper.get("doi"), known_ids, note_ids), paper.get("doi")) + "</p>" +
                 "<p>标签：" + html(paper.get("tags")) + "</p>" +
                 "<p>笔记摘要：" + html(short(paper.get("summary"))) + "</p>" +
                 "<p>局限：" + html(short(paper.get("limitations"))) + "</p>" +
                 "<p>" + anchor(note_path(row["id"], note_ids), "打开笔记（Markdown）") + "</p>")
        note_cards.append(row_card(row, "papers", extra))
    note_section = section("papers", "已有文献笔记", "数量指当前有效的 paper 笔记事件，不是去重论文数，也不是人工已读数。",
                           group("当前笔记", note_cards))

    open_tasks = sum(row["record"].get("task_state", "unspecified") not in ("done", "cancelled") for row in tasks)
    stats = "".join('<div class="stat"><strong>' + str(count) + "</strong><span>" + label + "</span></div>"
                    for count, label in ((len(tasks), "当前任务记录"), (open_tasks, "未关闭任务记录"),
                                         (len(queue), "候选 DOI 条目"), (len(papers), "当前笔记事件")))
    # 页面资料只拼入已转义的 HTML 槽位，不进入 JS、CSS 或 JSON 脚本块。
    template = (Path(__file__).resolve().parent.parent / "assets/overview.html").read_text(encoding="utf-8")
    replacements = {"@@PROJECT@@": html(config.get("name"), "未命名项目"), "@@GENERATED@@": html(stamp),
                    "@@STATS@@": stats, "@@CONTENT@@": current + progress + task_section + candidate_section + note_section,
                    "@@CSP@@": escape(_csp(template), quote=True)}
    return re.sub(r"@@(?:PROJECT|GENERATED|STATS|CONTENT|CSP)@@", lambda match: replacements[match[0]], template)
