# 项目决策记录与待决定事项

这些内容会实质影响公开项目。已经因本次公开授权确定的事项单独标记为“已确定”。

## D-001 正式项目名称

- 状态：已确定。
- 展示名称：`Research Workbench Assistant｜科研工作台助手`。
- GitHub 仓库名：`research-workbench-assistant`。

## D-002 开源许可证

- 状态：已确定。
- 许可证：Apache-2.0。
- 原因：允许社区使用和修改，并包含明确的专利授权条款。

## D-003 首个交付形态

- 候选 A：Python 命令行工具 + Codex Skills；
- 候选 B：仅 Codex Plugin；
- AI建议：先做可独立测试的 Python 核心，再用 Plugin 分发多个 Skills。

## D-004 首批支持系统

- 候选：先保证 Windows，再补 Linux；或从第一版开始双平台 CI。
- AI建议：开发环境继续使用 Windows，但从 v0.1 起建立 Windows/Linux CI，避免把绝对路径带入设计。

## D-005 模型接口

- 待确认首版是否只支持 OpenAI，还是同时保留其他模型提供方适配接口。
- AI建议：首版实现 OpenAI，内部接口保持可替换，但不要同时维护多个未经测试的后端。

## D-006 文献检索来源

- 待确认首批支持的公开元数据和开放全文来源；
- 不把需要页面抓取、验证码或机构登录的来源作为核心自动化依赖。

## D-007 数据存储

- 候选：纯 JSONL；JSONL + SQLite；JSONL + 图数据库。
- AI建议：v0.1 使用 JSON/JSONL 和可重建索引，稳定后再评估 SQLite；首版不引入图数据库。
