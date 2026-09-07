# 当前项目断点

更新时间：2026-09-07

## 当前目标

将独立开源仓库完善为可在本地 Codex 安装试用的科研助手，原助手保持不变。

## 已实现

- v0.1.0-alpha.1：自包含 Skill、安装器、初始化、记录、修订历史、续接、搜索、检查与视图重建。
- Markdown/JSON 文献笔记由同一记录生成；无内置联网检索或 PDF 解析。
- 本地单元测试覆盖安装、路径、写入失败与恢复；GitHub 配置 Windows/Linux 双版本测试。
- README、安装指南和社区首发文案已更新。

## 下一步

1. 核对发布后的 GitHub CI 结果。
2. 收集用户安装和新对话续接反馈；尚未进行独立用户端 Codex 对话验收。
3. 完善文献元数据、DOI 去重，再接入合法文献发现来源。

## 按需读取

- README.md
- skills/research-workbench/SKILL.md
- skills/research-workbench/references/records.md
- skills/research-workbench/scripts/workbench.py
- tests/test_workbench.py
- docs/GETTING_STARTED.md
- docs/LAUNCH_POST.md
