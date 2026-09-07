# Changelog

## 0.1.0-alpha.1 — 2026-09-07

首个本地 Codex 可用版本，适合个人试用。

### 已实现

- 自包含 research-workbench Skill 和拒绝覆盖的安装器。
- Python 3.10+ 标准库工具：init、record、resume、search、audit、render。
- JSON 原始事件、替代修订链、自动生成的工作台与分类台账。
- 由同一来源生成 Markdown/JSON 文献笔记，保留阅读范围。
- 写入锁、单文件原子替换、失败后视图重建。
- 虚构示例、双语首页、安装说明、社区推广文案和自动测试。

### 已知限制

- 不自带联网检索、PDF 解析、DOI 去重、Zotero、知识图谱和后台调度。
- 多个视图不构成整体事务；异常退出后可 audit/render 恢复。
- 证据真实性和用户已读状态不由程序自动验证。
- 早期 schema，不承诺后续版本无需迁移。
