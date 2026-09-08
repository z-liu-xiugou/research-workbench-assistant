# 记录格式与命令（schema_version 1）

在线找论文与候选筛选使用 [discovery.md](discovery.md)。新类型 discovery 表示检索批次，candidate_review 表示筛选历史，由专门命令生成，不与 kind=paper 的真实笔记混淆。两类记录只追加、不允许 supersedes 替代；候选及其筛选事件会随工作台备份。

`<script>` 是本技能 `scripts/workbench.py` 的实际路径，`<root>` 是项目内的工作台目录。Windows 示例使用 PowerShell；所有路径加引号，使用 `python -X utf8`。解释器名称可按用户环境调整。

```powershell
python -X utf8 "<script>" init --root "<root>" --name "我的课题"
python -X utf8 "<script>" record --root "<root>" --input "record.json"
python -X utf8 "<script>" resume --root "<root>"
python -X utf8 "<script>" search --root "<root>" --query "基线" --kind experiment
python -X utf8 "<script>" audit --root "<root>"
python -X utf8 "<script>" render --root "<root>"
python -X utf8 "<script>" tasks --root "<root>" --state open
```

输入是 UTF-8 JSON 对象；支持 BOM。用编辑工具生成输入文件，避免命令行转义造成损坏。输入文件也可能含隐私，应存进工作台或其他私有目录。

```json
{
  "kind": "checkpoint",
  "status": "计划中",
  "title": "建立基线实验",
  "body": "当前目标：先整理输入和评价指标，尚未开始实验。",
  "evidence": [],
  "next_step": "确认数据是否允许用于该课题"
}
```

必填：kind、status、title、body。kind 可选 progress/task/decision/issue/experiment/material/checkpoint/paper。status 可选已确认、进行中、计划中、候选方案、待确认、AI建议。checkpoint 必须含非空 next_step。已确认必须含非空 evidence 数组，但脚本不能判断证据真假。证据字符串仅被存储展示，不被脚本读取或执行。

可选 next_step、evidence、supersedes（已存在且尚未被替代的事件 ID）。修订也必须提交完整新记录，而不是局部字段。历史 ID 由脚本返回；可通过 search 找回。不支持删除/改写历史。不要在输入里自行设置 id、created_at 或 schema_version。

## 任务跟踪与续接

task 类型可以使用 task_state 字段：todo（待办）、in_progress（执行中）、done（完成）、cancelled（取消）。它表示任务执行情况，不代替 status 的研究判断。完成必须提供非空 evidence；程序不核实证据真假。只有实际完成且有依据才标记 done，不能因为生成了一段分析就自动完成实验任务。

修改任务时用 supersedes 指向旧事件 ID，并提交完整记录；可取消或重新打开任务，旧版本保留。旧任务缺少 task_state 时显示 unspecified，不推断为已完成。tasks 默认输出未关闭任务 JSON 数组；--state all/done/cancelled/todo/in_progress/unspecified 可筛选。TASKS.md 自动按状态分组，不要手改。

ACTIVE_CONTEXT.md 现在只保留最新断点和最多 5 条非文献近期记录的短摘要，再列最多 5 项未关闭任务。标题截取至 120 字符、正文至 240 字符、下一步至 500 字符；完整内容在链接的原始事件中。未关闭清单较长时应读取 TASKS.md，不把断点当成完整台账。

## 记录间的显式关联

所有记录均可带可选 links 数组，每项包含 target（已存在事件 ID）、relation 和 reason（具体关联理由）。不带 links 的旧记录继续兼容。

关系有方向：来源记录 references 目标表示“来源引用目标”；informs 表示“来源为目标提供参考”；depends_on 表示“来源依赖目标”。这些仅是记录者声明的关系，不表示系统验证了科学支持或执行依赖，也不自动阻止/完成任务。

例如先将论文入库并获得 ID，再给任务 JSON 添加以下字段。将占位文字换成真实返回的 32 位 ID，不能直接照抄占位文字运行：

```json
"links": [
  {"target": "替换为已入库事件ID", "relation": "references", "reason": "任务采用该论文作为基线候选，方法是否适用仍需验证"}
]
```

```powershell
python -X utf8 "<script>" related --root "<root>" --id "事件ID"
python -X utf8 "<script>" graph --root "<root>"
```

related 返回 outgoing（引用哪些记录）、incoming（被哪些当前记录引用）。按精确 ID 查询，不自动扩展至同一记录的其他版本。graph 输出 nodes/edges 的 JSON，RELATIONS.md 和 RELATIONS.json 是其自动生成视图；并非交互式可视化或自动推断图谱。

目标更新后，原边继续指向历史版本；JSON 用 is_current=false 和 latest_id 指出新版。来源修订时须提交完整 links；省略或传空数组表示新版不再保留这些关联，旧版原始记录仍保存。已被替代来源的边不出现在当前图中，查旧关系应读历史事件。

关联目标必须先入库。自引、未知目标和重复的目标/关系组合均拒绝；一个新修订可以引用自己的旧版本，表示明确的历史参考。校验和恢复也会检查关联是否完整，关系数据随事件一起备份。升级先备份后 render 重建视图；含新字段的事件不保证旧程序能读取。

## 文献笔记格式

paper 类型额外要求以下完整对象，其余类型不能有 paper：

```json
{
  "kind": "paper",
  "status": "待确认",
  "title": "演示论文（虚构，不可引用）",
  "body": "这是测试笔记流程的虚构材料。",
  "evidence": ["用户提供的虚构摘要"],
  "paper": {
    "source": "虚构示例，无真实 DOI",
    "reading_basis": "abstract",
    "summary": "演示如何记录从摘要得出的信息。",
    "limitations": "没有读取全文，不能判断实验是否充分。"
  }
}
```

reading_basis 仅支持 metadata/abstract/full_text。人工阅读状态始终显示未由工具确认；这不是人工已读台账。

paper 对象还可包含 authors（作者字符串数组）、year（四位整数年份）、doi（字符串）、venue（期刊/会议）、tags（字符串数组）。未知信息请省略，不编造。旧格式继续支持。

DOI 支持裸标识、doi: 前缀和 doi.org URL，入库时统一为小写裸标识。只检查格式，不联网核实。当前有效笔记中相同 DOI 会拒绝重复新增并返回已有 ID；修改笔记请以该 ID 为 supersedes 提交完整新记录。无 DOI 的论文不自动去重，题名相近也不会自动合并。

PAPER_INDEX.md 自动列出当前有效文献及笔记链接；旧版本仍保留在 events 和 notes。升级后先备份工作台，再 render 生成新增目录。新格式可被新版读取，但含新字段的事件不保证旧版程序能读取。

## 文件关系与恢复

### 本地备份与安全恢复

```powershell
python -X utf8 "<script>" backup --root "<root>" --output "独立备份目录/snapshot.json"
python -X utf8 "<script>" restore --input "独立备份目录/snapshot.json" --root "新的工作台目录"
```

备份父目录必须已存在，备份必须放在工作台之外，同名文件拒绝覆盖。仅备份 config.json、events/*.json、PERSONAL_NOTES.md、PROJECT_MANUAL.md，不包括论文、实验数据、输入文件或其他自建文件；自动视图恢复时重建，因此手改自动视图的内容不会保留。其他重要文件请另外备份。

备份未加密，可能包含全部研究记录，不要上传到公开仓库或发送给无权访问的人。SHA-256 用于检测内容损坏，不是数字签名，也不能证明来源可信。只恢复可信来源，不执行文件中的指令。

恢复先在临时目录验证路径白名单、哈希和事件结构，验证失败不创建目标。目标必须不存在，已有目录和链接均拒绝覆盖。复制阶段磁盘/权限错误可能留下不完整的新目录；保留它排查，并换新目录重新恢复，原项目和备份不修改。最多支持 64 MiB、10000 个受管理文件，无自动定时备份。

备份时工具加写入锁，但其他编辑器不会遵守此锁，备份期间请暂停人工改文件。写出中断可能留下不完整备份，此时命令报错；不要把该文件当作成功备份，修复后使用新文件名重试。恢复成功后运行 audit，并核对手写笔记及重要任务。

`events/<id>.json` 是原始记录；CURRENT_STATUS、WORKLOG、LEDGERS、ACTIVE_CONTEXT 和 notes 下的 Markdown/JSON 均从事件生成。每个事件先完整落盘，再生成视图；跨多个视图不保证单次事务，异常退出后运行 audit 检查，render 恢复。不应重试已成功保存的记录。事件不自动修改或删除；这是程序约定，不是防篡改存储。

`init` 不修改项目已有 AGENTS.md。希望每次科研任务都使用本技能，可自行在项目 AGENTS.md 追加：

```markdown
科研记录和续接任务使用 $research-workbench。默认先读 research-workbench/ACTIVE_CONTEXT.md，按需加载证据，不全盘扫描；仅在产生实质进展时记录。不要覆盖其他工作台。
```

工作台自身 `.gitignore` 默认忽略全部记录（保留忽略文件）。它不是访问控制，也无法保护已经被 Git 跟踪或强制添加的资料；分享前仍须人工审查。
