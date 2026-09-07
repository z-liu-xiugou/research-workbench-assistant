# 当前项目断点

更新时间：2026-09-07
轻量续接有效：是
需要完整审计：否
最近一次关键验证：2026-09-07

## 当前项目主线

把现有本地科研助手中可复用的科研记忆、工作台和文献笔记能力迁移为面向研究生的通用开源科研助手，同时保证原助手和原课题工作台不被修改或公开。

## 当前子任务

阶段 0“独立复制、隐私隔离和开源规划”已经完成；尚未开始迁移通用代码。

## 最近已确认

- 新项目目录为 `D:/pycharm_workplace/PycharmProjects/科研工作台`。
- 原助手与原工作台只读复制到 `_private_reference/`，共 37 个文件。
- 源文件与副本的 SHA-256 核对结果为：源变化 0，副本差异 0。
- `_private_reference/` 已由 Git 忽略。
- 已建立 README、产品范围、总体架构、迁移审计、路线图、隐私检查和申请准备文档。
- 已建立通用工作台 Markdown 模板。
- 副本文献笔记工具测试结果为 52 passed。
- 当前 Git 仓库尚无提交，也没有连接远程仓库。

## 下一步

1. 用户确认 v0.1 是否采用“Python 核心 + Codex Skills”的交付方式。
2. 设计通用结构化记录 Schema 和配置文件。
3. 先迁移路径安全、哈希、事件记录和 Markdown 视图生成能力。
4. 建立 Windows/Linux CI 后再迁移文献笔记功能。
5. 收集第一批社区使用场景和 Feature Request。

## 当前未决问题

- `I-003`：首个交付形态尚待用户确认。
- `I-004`：首版模型接口范围尚待确认。
- `I-005`：首批文献检索来源尚待设计与核验。

## 本阶段按需读取文件

- `README.md`
- `docs/PRODUCT_SCOPE.md`
- `docs/ARCHITECTURE.md`
- `docs/MIGRATION_AUDIT.md`
- `docs/OPEN_SOURCE_ROADMAP.md`
- `docs/DECISIONS_REQUIRED.md`
- `docs/COMMUNITY_LAUNCH_PLAN.md`
- `project-workbench/CURRENT_STATUS.md`
- `project-workbench/DECISIONS_AND_ISSUES.md`
