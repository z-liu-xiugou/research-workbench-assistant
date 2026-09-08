"""Crossref 单次有界检索；只发送显式查询，不读取或上传本地科研材料。"""
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

ENDPOINT = "https://api.crossref.org/works"
MAX_RESPONSE = 5 * 1024 * 1024


def doi_key(value):
    if not isinstance(value, str):
        raise ValueError("DOI 必须是文本")
    value = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", value.strip(), flags=re.I).lower()
    if not re.fullmatch(r"10\.\d{4,9}/\S+", value):
        raise ValueError("DOI 格式无效")
    return value


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def plain(value):
    if not isinstance(value, str):
        return ""
    parser = PlainText()
    parser.feed(value)
    return " ".join(" ".join(parser.parts).split())


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # 不跟随返回内容或跳转去访问其他主机。
        return None


def fetch_json(url, timeout):
    request = Request(url, headers={"Accept": "application/json", "User-Agent":
        "ResearchWorkbenchAssistant/0.1 (+https://github.com/z-liu-xiugou/research-workbench-assistant)"})
    try:
        with build_opener(NoRedirect()).open(request, timeout=timeout) as response:
            raw = response.read(MAX_RESPONSE + 1)
        if len(raw) > MAX_RESPONSE:
            raise ValueError("Crossref 响应超过 5 MiB 限制；请减小 limit")
        return json.loads(raw.decode("utf-8"))
    except HTTPError as error:
        if error.code == 429:
            raise ValueError("Crossref 限流（429）；请按 Retry-After 等待后手动重试：" + str(error.headers.get("Retry-After", "未指定"))) from None
        raise ValueError(f"Crossref HTTP {error.code}；此次检索未保存，不自动重试") from None
    except (URLError, TimeoutError, OSError) as error:
        raise ValueError("Crossref 网络失败；此次检索未保存，请检查网络后重试：" + str(error)) from None


def parse_item(raw):
    if not isinstance(raw, dict):
        raise ValueError("条目不是对象")
    titles = raw.get("title", [])
    title = plain(titles[0]) if isinstance(titles, list) and titles else ""
    if not title:
        raise ValueError("缺少题名")
    doi = doi_key(raw.get("DOI"))
    item = {"doi": doi, "title": title, "url": "https://doi.org/" + quote(doi, safe="/"), "authors": []}
    authors = raw.get("author", [])
    if isinstance(authors, list):
        for author in authors:
            if isinstance(author, dict):
                name = " ".join(filter(None, (plain(author.get("given")), plain(author.get("family"))))) or plain(author.get("name"))
                if name:
                    item["authors"].append(name)
    for field in ("published", "published-print", "published-online", "issued"):
        date = raw.get(field)
        parts = date.get("date-parts") if isinstance(date, dict) else None
        if isinstance(parts, list) and parts and isinstance(parts[0], list) and parts[0]:
            year = parts[0][0]
            if type(year) is int and 1000 <= year <= 9999:
                item["year"] = year
                break
    venues = raw.get("container-title", [])
    if isinstance(venues, list) and venues and plain(venues[0]):
        item["venue"] = plain(venues[0])
    for source, target in (("abstract", "abstract"), ("type", "work_type")):
        value = plain(raw.get(source))
        if value:
            item[target] = value
    return item


def search_crossref(query, limit=10, year_start=None, year_end=None, timeout=20):
    if not isinstance(query, str) or not query.strip() or len(query) > 500:
        raise ValueError("query 必须为 1–500 字符的明确检索词")
    if type(limit) is not int or not 1 <= limit <= 50:
        raise ValueError("limit 必须为 1–50")
    if not 1 <= timeout <= 60:
        raise ValueError("timeout 必须为 1–60 秒")
    for year in (year_start, year_end):
        if year is not None and (type(year) is not int or not 1000 <= year <= 9999):
            raise ValueError("年份必须为四位整数")
    if year_start is not None and year_end is not None and year_start > year_end:
        raise ValueError("起始年份不能晚于结束年份")
    params = {"query.bibliographic": query.strip(), "rows": limit, "sort": "relevance", "order": "desc"}
    filters = []
    if year_start is not None:
        filters.append(f"from-pub-date:{year_start}-01-01")
    if year_end is not None:
        filters.append(f"until-pub-date:{year_end}-12-31")
    if filters:
        params["filter"] = ",".join(filters)
    url = ENDPOINT + "?" + urlencode(params)
    response = fetch_json(url, timeout)
    message = response.get("message") if isinstance(response, dict) else None
    if not isinstance(message, dict) or not isinstance(message.get("items"), list):
        raise ValueError("Crossref 响应结构无效；未保存检索")
    total = message.get("total-results")
    if type(total) is not int or total < 0:
        raise ValueError("Crossref total-results 无效")
    items, skipped = [], []
    for position, raw in enumerate(message["items"][:limit], start=1):
        try:
            items.append(parse_item(raw))
        except ValueError as error:
            skipped.append({"position": position, "reason": str(error)})
    return {"source": "crossref", "query": query.strip(), "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "request_url": url, "limit": limit, "year_start": year_start, "year_end": year_end,
            "total_results": total, "items": items, "skipped": skipped, "duplicates": []}


def validate_discovery(data):
    fields = {"source", "query", "retrieved_at", "request_url", "limit", "year_start", "year_end", "total_results", "items", "skipped", "duplicates"}
    if not isinstance(data, dict) or set(data) != fields or data["source"] != "crossref":
        raise ValueError("检索记录结构无效")
    for key in ("query", "retrieved_at", "request_url"):
        if not isinstance(data[key], str) or not data[key].strip():
            raise ValueError("检索记录缺少 " + key)
    stamp = datetime.fromisoformat(data["retrieved_at"])
    if stamp.tzinfo is None:
        raise ValueError("检索时间必须带时区")
    parsed = urlsplit(data["request_url"])
    if parsed.scheme != "https" or parsed.netloc != "api.crossref.org" or parsed.path != "/works":
        raise ValueError("检索来源 URL 无效")
    if type(data["limit"]) is not int or not 1 <= data["limit"] <= 50 or type(data["total_results"]) is not int or data["total_results"] < 0:
        raise ValueError("检索数量无效")
    for key in ("year_start", "year_end"):
        if data[key] is not None and (type(data[key]) is not int or not 1000 <= data[key] <= 9999):
            raise ValueError("检索年份无效")
    if data["year_start"] is not None and data["year_end"] is not None and data["year_start"] > data["year_end"]:
        raise ValueError("检索年份范围无效")
    for key in ("items", "skipped", "duplicates"):
        if not isinstance(data[key], list) or len(data[key]) > data["limit"]:
            raise ValueError("检索列表无效：" + key)
    seen = set()
    for item in data["items"]:
        if not isinstance(item, dict) or not {"doi", "title", "url", "authors"} <= set(item) or set(item) - {"doi", "title", "url", "authors", "year", "venue", "abstract", "work_type"}:
            raise ValueError("候选元数据结构无效")
        doi = doi_key(item["doi"])
        if doi != item["doi"] or doi in seen:
            raise ValueError("候选 DOI 非规范或重复")
        seen.add(doi)
        for key in set(item) - {"authors", "year"}:
            if not isinstance(item[key], str) or not item[key].strip():
                raise ValueError("候选字段必须为非空文本：" + key)
        if item["url"] != "https://doi.org/" + quote(doi, safe="/"):
            raise ValueError("候选来源链接与 DOI 不一致")
        if not isinstance(item["authors"], list) or any(not isinstance(x, str) or not x.strip() for x in item["authors"]):
            raise ValueError("候选作者字段无效")
        if "year" in item and (type(item["year"]) is not int or not 1000 <= item["year"] <= 9999):
            raise ValueError("候选年份无效")
    for item in data["skipped"]:
        if not isinstance(item, dict) or set(item) != {"position", "reason"} or type(item["position"]) is not int or not 1 <= item["position"] <= data["limit"] or not isinstance(item["reason"], str):
            raise ValueError("跳过条目记录无效")
    for item in data["duplicates"]:
        if not isinstance(item, dict) or set(item) != {"doi", "existing"} or item["existing"] not in ("candidate", "paper", "batch"):
            raise ValueError("去重记录无效")
        doi_key(item["doi"])
