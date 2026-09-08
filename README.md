# Research Workbench Assistant｜科研工作台助手

[English](README_EN.md) · [安装与使用](docs/GETTING_STARTED.md) · [反馈问题](https://github.com/z-liu-xiugou/research-workbench-assistant/issues) · [参与讨论](https://github.com/z-liu-xiugou/research-workbench-assistant/discussions)

[![tests](https://github.com/z-liu-xiugou/research-workbench-assistant/actions/workflows/tests.yml/badge.svg)](https://github.com/z-liu-xiugou/research-workbench-assistant/actions/workflows/tests.yml)

**让 AI 对话结束后，科研进度仍然留在你自己的项目里。**

面向研究生的本地科研记录助手，以 Codex Skill 形式使用：记录目标、进展、问题和下一步，在新对话中按需续接；文献笔记保存为 Markdown 和 JSON。

> **v0.1.0-alpha.7：早期可用版。** 已提供可安装 Skill、科研记录和 Crossref 在线文献发现，适合个人试用。尚不是全自动科研平台，也不保证 AI 内容准确。

本次补齐 v0.1 的证据约束与验收：进行中/已确认记录需要可定位证据，已确认还须记录用户明确确认的出处；增加决策与问题汇总和可测试的轻量续接路由。旧事件不改写，升级审计会提示需人工复核。[升级规则与格式](skills/research-workbench/references/records.md) · [验收证据](docs/ISSUE_ACCEPTANCE.md)

## 五分钟开始

需要：可用的本地 Codex、Python 3.10+、Git。脚本无第三方 Python 依赖，无需另填 API Key；Codex 本身仍需可用账户，可能产生使用费用。

在 PowerShell 或终端执行：

```powershell
git clone https://github.com/z-liu-xiugou/research-workbench-assistant.git
cd research-workbench-assistant
python -X utf8 scripts/install.py
```

安装器只复制 research-workbench Skill 到用户 `.agents/skills`，不会覆盖已有同名技能，不触碰其他助手。未识别时重启 Codex。也可让 `$skill-installer` 从本仓库 `skills/research-workbench` 安装，两种方式选一种。[Codex 官方技能说明](https://learn.chatgpt.com/docs/build-skills)

在 Codex 打开**你自己的科研项目**，输入：

```text
$research-workbench 请为这个项目初始化科研工作台。先了解我的研究目标，不要编造进展，也不要覆盖已有记录。
```

完成一项工作后：

```text
$research-workbench 请保存这次实质进展、证据位置和下一步，并更新续接断点。还没确认的方案不要写成已确认。
```

新建对话时：

```text
$research-workbench 继续上次研究。先读当前断点，只加载这次任务需要的资料。
```

## 现在能做什么

| 能力 | 当前范围 |
| --- | --- |
| 初始化工作台 | 独立目录，拒绝覆盖现有目录 |
| 跨对话续接 | 保存本地断点，由 Codex 在新任务中读取；不是云端聊天记忆 |
| 进展和分类台账 | 进展、任务、决策、问题、实验、材料、断点、文献记录 |
| 修订留痕 | 追加新记录并标记替代关系，旧版本保留 |
| 任务执行跟踪 | 待办、执行中、完成、取消；筛出未关闭任务，保留修订历史 |
| 文献笔记库 | 将 Codex/用户提供的笔记生成 Markdown + JSON；区分摘要与全文 |
| 本地检索 | 当前有效记录的关键词搜索，可限定文献类型 |
| 在线文献发现 | Crossref 主题/年份查询，DOI 去重，来源与检索批次留痕 |
| 候选文献队列 | 待筛选、保留、排除；已有笔记自动关联，不等于人工已读 |
| 检查与恢复 | 校验结构、发现视图不一致、从历史记录重建 |

**还不能做：** 自动下载/解析 PDF、内置 Google Scholar/知网/PubMed 等多来源检索、Zotero 同步、后台定时跟踪、自动推断/交互式文献图谱、多人实时协作。Crossref 查询并不覆盖全部论文，候选与实际阅读笔记严格分开。

## 在线找论文并保存候选

在已经初始化的工作台上运行：

```powershell
python -X utf8 skills/research-workbench/scripts/workbench.py discover --root demo-workbench --query "renewable energy forecasting" --year-start 2023 --year-end 2025 --limit 10
python -X utf8 skills/research-workbench/scripts/workbench.py candidates --root demo-workbench
```

也可直接在 Codex 中输入：

```text
$research-workbench 用 Crossref 检索 renewable energy forecasting，限定 2023–2025 年，取前 10 条，去重后保存候选，不要标记为已读。
```

打开 CANDIDATES.md/JSON 查看结果。保留/排除候选要写理由；实际阅读并生成同 DOI 笔记后，候选自动关联到笔记。详见 [完整检索—筛选—笔记衔接流程](skills/research-workbench/references/discovery.md)。

查询使用 Crossref 公开元数据接口，无需 API Key；一次只取相关性排序前 1–50 条，不代表穷尽检索。检索词会发送给 Crossref，不能含未公开研究细节。[官方接口说明](https://www.crossref.org/documentation/retrieve-metadata/rest-api/)

## 不用 Codex 也能验证记录流程

在仓库根目录运行，demo-workbench 必须尚不存在：

```powershell
python -X utf8 skills/research-workbench/scripts/workbench.py init --root demo-workbench --name "示例科研项目"
python -X utf8 skills/research-workbench/scripts/workbench.py record --root demo-workbench --input examples/checkpoint.json
python -X utf8 skills/research-workbench/scripts/workbench.py record --root demo-workbench --input examples/paper.json
python -X utf8 skills/research-workbench/scripts/workbench.py resume --root demo-workbench
python -X utf8 skills/research-workbench/scripts/workbench.py audit --root demo-workbench
```

打开 demo-workbench/ACTIVE_CONTEXT.md 和 demo-workbench/notes/ 查看结果。示例全部虚构，不可作为真实文献引用。详见 [使用指南](docs/GETTING_STARTED.md)。

## 数据与安全

新增任务示例为 examples/task.json。入库后可运行：

```powershell
python -X utf8 skills/research-workbench/scripts/workbench.py tasks --root demo-workbench
```

默认返回未关闭任务；`--state done` 查看已完成。完成需提供证据，不能将“任务做完”混同于“研究结论已确认”。续接断点只展示短摘要与原始事件链接，完整任务见 TASKS.md。旧工作台升级先备份，再用新版 render 重建视图。

- 只有 discover 向 Crossref 发送明确查询参数，不上传工作台或论文；其他记录命令不联网。使用 Codex 模型或外部工具也不等于完全离线，请遵守课题数据要求。
- 工作台默认忽略 Git 提交，但 .gitignore 不是隐私保证。已跟踪文件、强制添加、同步盘需要另外检查。
- 证据字段保留来源，不自动证明结论；生成笔记不等于你已读过原文。
- 自动生成页面请勿手改；自由笔记放 PERSONAL_NOTES.md。重要资料仍需自行备份。

## 参与与维护

欢迎先试用“初始化 → 记录 → 新对话续接”，反馈最容易丢失的研究上下文。报告问题请附系统、Python 版本、命令和脱敏错误，不上传真实论文或密钥。

```powershell
python -X utf8 -m unittest discover -s tests -v
```

[贡献说明](CONTRIBUTING.md) · [安全报告](SECURITY.md) · [变更记录](CHANGELOG.md) · [推广文案](docs/LAUNCH_POST.md) · [历史规划](docs/OPEN_SOURCE_ROADMAP.md)

历史架构、迁移审计和路线图描述长期目标；当前能力以本 README、实际代码和测试为准。

Apache-2.0 开源。非 OpenAI 官方项目；开源或获得 Star 不保证获得任何赞助计划资格。

文献库现支持作者、年份、DOI、期刊/会议和标签；同 DOI 重复入库会被拒绝，修订保留历史。PAPER_INDEX.md 提供当前文献目录。DOI 仅检查格式，不联网验证；无 DOI 不自动去重。

## 备份与恢复

新增 backup/restore：备份配置、原始事件、PERSONAL_NOTES.md 和 PROJECT_MANUAL.md；恢复前校验完整性与结构，只写入新目录，不覆盖已有项目。命令见[记录格式](skills/research-workbench/references/records.md#本地备份与安全恢复)。备份未加密，不包含论文、实验数据或其他自建文件，请另行保存这些材料。

## 文献与任务关联

现支持 links 显式关联，以及 related 双向查询、RELATIONS.md/JSON 关系清单。每条关联记录理由；引用旧版本会提示核对，不自动改为新版。适合追踪“任务引用了哪些文献”“材料被哪些当前记录引用”。这不是自动推断或交互式图谱，关联也不等于结论已验证。详见[使用指南](docs/GETTING_STARTED.md#5-关联文献任务和实验)。
