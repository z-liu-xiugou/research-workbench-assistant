# 当前项目断点

更新时间：2026-09-27

## 当前目标

将独立开源仓库完善为可在本地 Codex 安装试用的科研助手，原助手保持不变。

## 本次维护

2026-09-27：#10 已完成，提交 5d15643 升级 Node 24 Actions 并固定 Ubuntu 24.04；CI 36306592914 四组全部通过。本地 85 项测试中 84 通过、1 权限跳过，公开扫描 0 命中。#9 文档齐备，仍无外部真人反馈，保持开放。

## 已实现

- 2026-09-27：M01 完成。主分支统一为 alpha.9 未发布预览版（CLI 0.1.0a9）；累计差异、兼容性和发布说明见 docs/RELEASE_PREPARATION.md。Release 仍为 alpha.1，未建立新标签；下一步先做 M02。

- 2026-09-21：#7 安装失败完整性修复、#8 分页升级说明已实现；#9 试用清单和反馈模板已建立，外部验收仍待真人反馈。85 项本地测试：84 通过、1 权限跳过。

- alpha.8：本地摘要分页检索、类型/状态筛选、标题优先排序、按 ID 查看精确版本；search 输出格式升级，旧事件无需迁移。本地 81 项测试中 80 通过、1 权限跳过。

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

- 持续维护任务以 `docs/MAINTENANCE_PLAN.md` 为唯一计划清单，共 15 项；M01 已完成，其余按表推进。
- 下次默认处理 **M02：验证分发包的安装与基本流程**。用户指定编号时优先执行指定项；每轮一个可验收的小任务，完成后回写任务状态与证据。
- #7/#8/#10 已完成并关闭；#9 由用户后续安排外部真人试用，对应 M15，不阻塞其他任务。
- 每日 Actions 仅运行测试和公开文件检查，未启用后台 AI 自动维护。

## 按需读取

- docs/MAINTENANCE_PLAN.md（先查看本轮任务及依赖）
- docs/RELEASE_PREPARATION.md（M01 差异与待发布范围）
- README.md
- skills/research-workbench/SKILL.md
- skills/research-workbench/references/records.md
- skills/research-workbench/scripts/workbench.py
- tests/test_workbench.py
- docs/GETTING_STARTED.md
- docs/LAUNCH_POST.md
