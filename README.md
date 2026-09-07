# Research Workbench Assistant｜科研工作台助手

[English](README_EN.md) | 简体中文

> **Pre-alpha / 公开开发阶段**：当前仓库已经公开产品范围、架构、工作台模板和实施路线，但尚未提供可安装运行的通用助手。欢迎参与需求讨论和早期设计。

这是一个开源科研助手项目，面向需要长期使用 AI 开展科研工作的研究生和科研人员。

项目首先解决一个基础问题：AI 对话会结束，但科研项目不会结束。研究目标、已确认事实、当前进展、决策、问题、实验、文献和成果需要保存在本地、能够核验，并在下一次对话中按需恢复。

## 当前状态

- **已确认**：现有本地科研助手和工作台已经复制到 `_private_reference/`，作为只读迁移依据。
- **已确认**：该目录被 Git 忽略，不属于未来公开内容。
- **计划中**：建立通用的科研记忆核心、工作台模板和结构化记录模型。
- **计划中**：迁移 PDF 校验、Markdown/JSON 双输出、去重、版本链和文献索引能力。
- **候选方案**：将多个科研工作流 Skill 打包为可安装插件。

仓库地址：[github.com/z-liu-xiugou/research-workbench-assistant](https://github.com/z-liu-xiugou/research-workbench-assistant)

- [提交功能建议或问题](https://github.com/z-liu-xiugou/research-workbench-assistant/issues)
- [参与社区讨论](https://github.com/z-liu-xiugou/research-workbench-assistant/discussions)
- [查看 v0.1 里程碑](https://github.com/z-liu-xiugou/research-workbench-assistant/milestone/1)

## 希望解决的问题

1. 每次新建 AI 对话时延续当前科研上下文，而不是重新解释整个项目。
2. 区分已经确认、正在进行、计划、候选方案、待确认问题和 AI 建议。
3. 自动记录实质工作、决策、问题、实验、材料和成果。
4. 自动检索文献、维护候选队列，并在合法来源范围内获取或接收全文。
5. 从论文生成可人工阅读的 Markdown 笔记和可检索的结构化 JSON 笔记。
6. 建立论文、观点、方法、数据、实验和研究任务之间的记忆网络。
7. 让所有记录能够审计、重建、迁移和由用户人工确认。

## 项目边界

本项目不会绕过付费墙或机构权限，不会自动公开用户论文和研究资料，也不会把 AI 生成内容自动标记为事实或“已经阅读”。

## 规划文档

- [产品范围](docs/PRODUCT_SCOPE.md)
- [总体架构](docs/ARCHITECTURE.md)
- [现有能力迁移审计](docs/MIGRATION_AUDIT.md)
- [开源实施路线图](docs/OPEN_SOURCE_ROADMAP.md)
- [隐私与发布检查清单](docs/PRIVACY_AND_RELEASE_CHECKLIST.md)
- [OpenAI 开源计划准备路线](docs/OPENAI_OSS_APPLICATION_PLAN.md)
- [社区启动与推广计划](docs/COMMUNITY_LAUNCH_PLAN.md)
- [待用户决定事项](docs/DECISIONS_REQUIRED.md)

## 本项目自己的开发工作台

本项目从初始化开始使用同一套科研记忆思想管理自身开发。当前断点见 [project-workbench/ACTIVE_CONTEXT.md](project-workbench/ACTIVE_CONTEXT.md)。

## 公开前置条件

项目采用 [Apache License 2.0](LICENSE)。当前允许公开讨论和共同设计，但尚未完成通用代码迁移，不能把规划中的功能描述为已经实现。

## 参与项目

- 功能需求和使用场景：提交 Feature Request；
- 架构、Schema 和科研工作流建议：参与 Discussions 或相关 Issue；
- 代码贡献：先阅读 [CONTRIBUTING.md](CONTRIBUTING.md)；
- 安全或隐私问题：按照 [SECURITY.md](SECURITY.md) 私下报告。
