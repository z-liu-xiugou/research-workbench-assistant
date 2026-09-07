# 安装与使用

## 1. 安装 Skill，不复制个人研究数据

下载仓库后执行 `python -X utf8 scripts/install.py`。默认目标是用户目录下 `.agents/skills/research-workbench`；Windows、macOS、Linux 使用同一个安装器。仅安装到指定项目时：

```powershell
python -X utf8 scripts/install.py --dest "目标项目/.agents/skills"
```

将“目标项目”替换成真实路径。避免同时用户级和项目级安装同名 Skill。安装位置依据 [Codex 官方文档](https://learn.chatgpt.com/docs/build-skills)；本版本是本地 Skill 安装包，不是已上架插件商店的产品。

若 python 不存在，先安装 Python 3.10+ 并重新打开终端；Windows 可用 `py -3` 替换命令中的 python。工具无额外 Python 依赖。

更新时先 `git pull --ff-only`，把已安装的旧 research-workbench 文件夹移动到**技能扫描目录之外**备份，再运行安装器。安装器拒绝自动覆盖，避免丢失本地修改。卸载只移走安装的 Skill 文件夹，项目内科研记录仍保留。不要删除整个 .agents 目录。

## 2. 在真正的研究项目中使用

在 Codex 打开研究项目，使用 `$research-workbench` 请求初始化。Skill 会调用随包脚本，在项目内创建 research-workbench/。它不修改已有 AGENTS.md，也不迁移已有私有助手。

希望减少每次输入技能名，可自行向项目 AGENTS.md 追加以下约定，保留已有规则：

```markdown
科研记录和跨对话续接使用 $research-workbench，先读 research-workbench/ACTIVE_CONTEXT.md，按需读证据。仅在有实质进展时写入记录，不覆盖其他科研工作台。
```

这是项目提示规则，不是每轮强制执行的后台程序。定期检查记录是否完整，尤其在任务中断时。

## 3. 文件各自负责什么

| 文件 | 用途 | 可否手改 |
| --- | --- | --- |
| config.json | 名称、结构版本 | 不建议；改动前备份 |
| events/*.json | 原始事件与修订历史 | 不要修改；用 record 追加 |
| ACTIVE_CONTEXT.md | 当前断点及最近进展 | 自动生成 |
| CURRENT_STATUS.md | 未被替代的记录 | 自动生成 |
| WORKLOG.md | 完整历史，包括旧版本 | 自动生成 |
| LEDGERS.md | 按类型分组的记录 | 自动生成 |
| notes/*.md、*.json | 逐条文献笔记视图 | 自动生成 |
| PERSONAL_NOTES.md | 用户自由笔记 | 可以 |
| PROJECT_MANUAL.md | 研究范围、资料位置和约定 | 可以 |

“当前记录”不表示任务全部未完成；本版用 status 和正文表达状态，没有独立完成/关闭字段。更正通过 supersedes 追加新版本。notes 保留历史文献版本；用 search 查询当前有效版本。

## 4. 直接使用脚本

完整命令、字段和例子见 [记录格式](../skills/research-workbench/references/records.md)。输入文件由 Codex 用编辑工具生成，或自己保存 UTF-8 JSON。不要在参数中放密钥。

例如对论文说：

```text
$research-workbench 请阅读我提供的摘要，生成文献笔记并入库。标记仅基于摘要，保留出处和不确定性，不要声称精读全文或替我标记已读。
```

脚本不生成学术内容；Codex 根据来源写笔记，脚本验证字段、保存和生成两种格式。内容仍需要你核对。

## 5. 故障恢复

- 目标目录已存在：换一个新目录或继续使用原工作台，不要清空重建。
- 同名 Skill 已存在：备份移走旧 Skill，再安装；不要覆盖其他助手。
- “记录已保存，视图更新失败”：保留 ID，修复权限/磁盘问题，再 render；不要重复提交。
- audit 返回 stale_views：先将想保留的人工改动复制到 PERSONAL_NOTES，再 render。
- 提示 .write.lock：可能有进程写入；等它结束再重试。确认没有写入进程后，才移走遗留锁。
- JSON 损坏：工具报错，不自动丢掉历史。先备份，从可靠备份修复；不要随意删事件。

单文件替换是原子的，多个视图不是整体事务。audit 检查结构与一致性，不检查科学正确性，也不是安全审计。
