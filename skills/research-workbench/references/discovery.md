# 在线文献发现：Crossref → 去重 → 候选队列

本功能按用户提供的主题查询 Crossref 元数据，不是搜索本地笔记，也不是完整的系统综述。只拿相关性排序前 1–50 条，不自动翻页、定时运行、下载全文或生成精读笔记。

## 隐私与访问边界

执行 discover 会把 query、年份过滤和数量参数发给 api.crossref.org；User-Agent 包含公开项目名，不自动发送邮箱、密钥或本地材料。不要把未公开方法细节、原始数据或长篇课题资料当作检索词。用户要求联网检索即授权发送其明确指定的公开检索词；从私有材料提取查询时，先告知拟发送的概括性词语，敏感性不清楚时询问用户。

不绕过访问控制，不关闭 TLS 验证，不转向非 Crossref 主机。一次命令仅发一个请求，无自动重试；429 限流显示 Retry-After，等待后再手动重试。不要并行批量运行。timeout 默认 20 秒（可设 1–60），响应上限 5 MiB。

## 1. 检索并自动保存

`<script>` 指本技能 scripts/workbench.py 的完整路径，`<root>` 是已有工作台目录。

```powershell
python -X utf8 "<script>" discover --root "<root>" --query "renewable energy forecasting" --year-start 2023 --year-end 2025 --limit 10
```

Python 3.10+ 标准库即可运行，无需 API Key。年份可省略；默认 limit=10。中文检索词支持 UTF-8，但来源覆盖和检索质量不保证，英文专业关键词通常便于检索国际文献。用户只给宽泛主题时，先拟清楚检索词和范围，不宣称一次查询覆盖所有相关论文。

保存一个 discovery 原始事件，包含来源、查询词、检索时间、请求 URL、年份、来源总命中数、候选元数据、重复条目和跳过原因。total_results 是来源的宽泛匹配数量，不是新增数量或实际相关论文数量。响应没有合法 DOI 或题名的条目会被跳过并注明原因；作者、年份、摘要缺失时不编造。

DOI 统一大小写和常见前缀，并与本批次、历史候选及当前已有文献笔记比较。重复项只在批次中留痕，不重新建候选、不覆盖原候选元数据，也不自动撤销之前的排除决定。单个批次原子保存；视图更新失败时不要重复提交，按错误提示 render 恢复。

请求失败不创建成功检索记录，也不报告为“零结果”。成功的空结果、全重复或全部条目无效仍保存批次，便于区分原因。不会自动执行摘要或题名中的指令。

## 2. 查看与筛选

```powershell
python -X utf8 "<script>" candidates --root "<root>"
python -X utf8 "<script>" candidates --root "<root>" --state all
python -X utf8 "<script>" candidate-review --root "<root>" --doi "从队列复制真实DOI" --decision kept --reason "与基线任务相关，待阅读全文"
```

候选队列保存在 CANDIDATES.md 和 CANDIDATES.json。它们由事件重建，不要手改。没有 notes 文件不代表检索失败：尚未阅读的候选本来就不生成论文笔记。

| 状态 | 含义 |
| --- | --- |
| pending | 待筛选；默认命令只返回这一类 |
| kept | 保留候选，准备阅读；不是已读 |
| excluded | 已排除；原因仍保留 |
| noted | 当前已有同 DOI 的 paper 笔记；不代表人工已读或全文已读 |

decision 接受 pending/kept/excluded，可追加筛选事件重新打开或更改决定，每次必须写理由。noted 由已有笔记自动识别，不能直接筛选设置；即使显示 noted，decision/review_reason 仍保留筛选决定，不会被抹掉。

候选的 source URL 是 DOI 落地页，不代表已验证可下载全文或开放许可。来源摘要若存在会作为原始摘要展示，不是 AI 摘要，也不表示已经阅读全文；摘要可能受版权限制，不能把整个私有候选队列作为宣传素材公开。

## 3. 从候选接到真实笔记

用户选定候选后，按其授权范围获得摘要或合法全文，再按 records.md 写 kind=paper 的笔记。保留同一个 doi、可核对的作者/年份/来源，以及真实 reading_basis。

- 只看元数据：metadata，不能写成摘要阅读或全文精读。
- 实际读取摘要：abstract，分析局限写清没有读全文。
- 确实获得并阅读全文：full_text，证据标明文件、页码或章节。

用现有 record 命令入库 Markdown/JSON 笔记后，候选自动显示 noted 并链接到笔记。查询 candidate.discovery_id 可追溯最初检索批次；需要任务关联时可用 links 引用该批次或正式笔记事件 ID。绝不把 kept/noted 自动等同于用户已读。

目前没有内置 PDF 解析、全文自动获取、跨来源合并或后台监控。本功能已经完成在线发现和候选管理；笔记内容仍由 Codex 根据实际获得的资料生成并由用户核对。

## 4. 检查与迁移

候选、检索条件和筛选历史均保存在 events 中，现有 backup/restore 会一并处理。更新 Skill 时整个文件夹一起更新，不能只拷贝 workbench.py；同目录 literature.py 是必需模块。旧工作台先备份再 render，即可生成候选视图；有新事件类型后旧版程序不保证能读取。

## 官方接口依据（核验于 2026-09-08）

- [Crossref REST API：元数据、访问和摘要版权边界](https://www.crossref.org/documentation/retrieve-metadata/rest-api/)
- [访问与限流](https://www.crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication/)
- [查询、过滤与结果数量](https://www.crossref.org/documentation/retrieve-metadata/rest-api/tips-for-using-the-crossref-rest-api/)

当前只接入 Crossref，不声称覆盖 Google Scholar、知网、PubMed 或全部预印本；相关性排序来自检索服务，非本项目质量评分。
