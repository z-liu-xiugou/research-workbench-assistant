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

- 首版已采用自包含 Codex Skill + Python 标准库命令行工具，依据用户要求社区可以在本地 Codex 使用。
- 插件商店打包与上架留待后续，不是当前安装前提。

## D-004 首批支持系统

- 首版已配置 Windows/Linux、Python 3.10/3.12 四组 CI，结果以 GitHub Actions 为准。macOS 尚未运行 CI。

## D-005 模型接口

- 首版不单独连接模型 API；利用用户已有 Codex，脚本只做本地记录操作。多模型后端仍为候选。

## D-006 文献检索来源

- 待确认首批支持的公开元数据和开放全文来源；
- 不把需要页面抓取、验证码或机构登录的来源作为核心自动化依赖。

## D-007 数据存储

- 首版已采用独立 JSON 事件 + 可重建 Markdown/JSON 视图，不引入数据库。替代修订保留旧事件，详细约定见 skills/research-workbench/references/records.md。
