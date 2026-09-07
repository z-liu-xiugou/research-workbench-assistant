# 当前项目状态

更新时间：2026-09-07

## 1. 当前阶段

阶段 0：独立复制、隐私隔离、开源规划和 pre-alpha 公开发布已完成；阶段 1 通用科研记忆核心尚未开始。

## 2. 当前主要目标

在不修改原助手的前提下公开独立项目，建立社区维护入口，并确定 v0.1 的交付形态和通用数据模型。

## 3. 功能状态

| 功能 | 状态 | 证据 |
|---|---|---|
| 原助手只读副本 | 已确认 | `_private_reference/SOURCE_MANIFEST.json` |
| Git 隐私隔离 | 已确认 | `.gitignore` 与 `git check-ignore` 验证 |
| 开源产品规划 | 已确认 | `docs/` 下规划文档 |
| 通用工作台模板 | 已确认 | `templates/research-workbench/` |
| 通用结构化记录核心 | 计划中 | `docs/OPEN_SOURCE_ROADMAP.md` |
| 自动文献发现 | 计划中 | `docs/PRODUCT_SCOPE.md` |
| 通用 Markdown/JSON 文献笔记 | 计划中 | `docs/MIGRATION_AUDIT.md` |
| 文献记忆网络 | 候选方案 | `docs/ARCHITECTURE.md` |
| 可安装插件 | 候选方案 | `docs/DECISIONS_REQUIRED.md` |
| GitHub 公开仓库 | 已确认 | `https://github.com/z-liu-xiugou/research-workbench-assistant` |
| v0.1 公开维护计划 | 已确认 | GitHub Milestone #1 和 Issue #1—#6 |

## 4. 验证结果

- 复制文件数：37。
- 源文件哈希变化：0。
- 副本哈希差异：0。
- 副本文献笔记测试：52 passed。
- 已知私人标识公开文件扫描：0 个命中。
- Git 主分支为 `main`，初始公开提交为 `c9daaa0`，远程仓库为 `origin`。
- GitHub 仓库可见性为 `PUBLIC`，Issues 和 Discussions 已开启。

## 5. 当前阻塞问题

- v0.1 交付形态尚未确认；
- 通用 Schema 尚未设计，暂不能安全迁移代码。

## 6. 最近实际工作

- 2026-09-07：完成独立目录核验、只读复制、私有隔离、规划文档、模板和验证。
- 2026-09-07：创建 GitHub 公开仓库、推送初始提交并建立 v0.1 里程碑和 6 个维护 Issue。
