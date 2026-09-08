# 当前项目断点

更新时间：2026-09-08

## 当前目标

将独立开源仓库完善为可在本地 Codex 安装试用的科研助手，原助手保持不变。

## 已实现

- alpha.7：补齐证据/确认校验、v2 事件结构、决策问题视图、轻量路由和隐私回归；验收入口见 docs/ISSUE_ACCEPTANCE.md。旧历史保留并提示复核。
- 实现提交 3bcdb40 的四组 Windows/Linux CI 全部通过，GitHub #1–#6 已附证据关闭；本地 75 项中 74 通过、1 权限跳过。

- alpha.6：Crossref 在线主题/年份查询、批次留痕、DOI 去重、独立候选队列和筛选历史；已有同 DOI 笔记自动链接。真实联网新增 3 篇，重跑新增 0 篇。

- alpha.5：显式关联及理由、双向查询、关系 JSON/Markdown、历史目标版本提示；本地 42 项通过、1 项权限跳过。

- alpha.4：受管理记录的本地备份、哈希和结构校验、新目录安全恢复；不含论文或其他自建文件。

- alpha.3：任务执行状态、未关闭筛选、任务清单和限长续接摘要；本地 26 项测试中 25 通过、1 项权限跳过。

- alpha.2 增加文献作者/年份/DOI/期刊/标签、DOI 去重及当前文献目录；兼容旧记录。

- v0.1.0-alpha.1：自包含 Skill、安装器、初始化、记录、修订历史、续接、搜索、检查与视图重建。
- Markdown/JSON 文献笔记由同一记录生成；现已内置 Crossref 检索，仍无 PDF 解析。
- 本地单元测试覆盖安装、路径、写入失败与恢复；GitHub 配置 Windows/Linux 双版本测试。
- README、安装指南和社区首发文案已更新。

## 下一步

1. 收集 alpha.7 升级和旧历史复核反馈；后续新问题以 GitHub 实际清单为准。
2. 收集用户安装和新对话续接反馈；尚未进行独立用户端 Codex 对话验收。
3. 收集 Crossref 检索及筛选反馈；评估下一来源和合法全文阅读流程。仍无全文下载/PDF 解析、无 DOI 条目的自动去重或穷尽检索。

## 按需读取

- README.md
- skills/research-workbench/SKILL.md
- skills/research-workbench/references/records.md
- skills/research-workbench/scripts/workbench.py
- tests/test_workbench.py
- docs/GETTING_STARTED.md
- docs/LAUNCH_POST.md
