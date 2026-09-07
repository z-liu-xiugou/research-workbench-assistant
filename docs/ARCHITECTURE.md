# 总体架构

## 1. 设计原则

项目采用“结构化事实层 + Markdown 阅读层 + AI 工作流层”。

- 结构化事实层保存可校验的数据，是状态计算的依据；
- Markdown 阅读层供研究者直接查看；
- AI 工作流层负责读取、执行、提出变更并调用确定性脚本保存记录。

## 2. 推荐目录

```text
research-workbench/
├─ .research-assistant/
│  ├─ config.yaml
│  ├─ events.jsonl
│  ├─ facts.jsonl
│  ├─ tasks.jsonl
│  ├─ decisions.jsonl
│  ├─ issues.jsonl
│  ├─ experiments.jsonl
│  ├─ artifacts.jsonl
│  └─ literature/
│     ├─ papers.jsonl
│     ├─ records/
│     ├─ graph_nodes.jsonl
│     └─ graph_edges.jsonl
├─ research-workbench/
│  ├─ ACTIVE_CONTEXT.md
│  ├─ PROJECT_MANUAL.md
│  ├─ CURRENT_STATUS.md
│  ├─ WORKLOG.md
│  ├─ DECISIONS_AND_ISSUES.md
│  ├─ EXPERIMENT_STATUS.md
│  └─ LITERATURE_WATCH.md
└─ research-library/
   ├─ notes/
   ├─ records/
   └─ indexes/
```

## 3. 对话生命周期

```text
新对话开始
  → 识别项目和配置
  → 读取 ACTIVE_CONTEXT
  → 按问题检索相关结构化记录
  → 检查必要原始证据
  → 执行科研任务
  → 追加事件和验证结果
  → 更新结构化状态
  → 重新生成受影响的 Markdown 视图
  → 保存下一次对话断点
```

## 4. 记录之间的职责

| 记录 | 职责 | 是否允许覆盖 |
|---|---|---|
| `events.jsonl` / `WORKLOG.md` | 记录实际发生过什么 | 只追加 |
| `facts.jsonl` | 保存事实、来源和证据 | 通过修订更新，不删除历史 |
| `CURRENT_STATUS.md` | 展示当前状态 | 可以重新生成 |
| `ACTIVE_CONTEXT.md` | 为下一次对话提供简短导航 | 可以重新生成 |
| `decisions.jsonl` | 保存决策、依据和有效状态 | 追加新版本 |
| `issues.jsonl` | 保存问题、阻塞和关闭条件 | 更新状态并保留历史 |
| `experiments.jsonl` | 保存实验配置、运行和结果 | 只追加运行，允许补充验证 |
| `papers.jsonl` | 文献索引 | 可从逐篇记录重建 |
| `graph_edges.jsonl` | 保存显式研究关系 | 通过带来源的新记录修订 |

## 5. 状态与证据

通用状态固定为：

- `confirmed`：已有原始证据、运行验证或用户明确确认；
- `in_progress`：已有实际工作，但尚未完成；
- `planned`：已经确定为下一步，尚未开始；
- `candidate`：尚未选型或验证；
- `needs_confirmation`：证据不足或存在冲突；
- `ai_suggestion`：AI 提议，尚未被用户采纳。

每条 `confirmed` 和 `in_progress` 记录必须包含证据路径。AI 不能自行把 `candidate` 或 `ai_suggestion` 升级为 `confirmed`。

## 6. 文献记忆网络

节点至少支持：论文、观点、研究问题、方法、数据集、实验、任务、决策和成果。

关系至少支持：`supports`、`contradicts`、`uses_method`、`evaluated_on`、`relevant_to`、`derived_from`、`produces`、`blocks` 和 `cites`。

向量检索只负责寻找语义相近内容；关系网络负责保存明确关系。每条关系都要记录来源、证据位置、生成方式和人工确认状态。
