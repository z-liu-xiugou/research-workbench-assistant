# v0.1 Issue 验收说明

本次版本：0.1.0a7。只修改独立开源仓库，不迁移或改动原始私有助手。

2026-09-08 已验收并关闭 #1–#6。[实现提交 3bcdb40](https://github.com/z-liu-xiugou/research-workbench-assistant/commit/3bcdb40e733584df318640ebfe961d5a7d1d3f25) 的 [四组 CI 全部通过](https://github.com/z-liu-xiugou/research-workbench-assistant/actions/runs/34224205999)。本地 75 项测试：74 通过、1 项 Windows 符号链接权限跳过；Skill 静态校验通过、已知隐私模式扫描无命中。各 Issue 已留下对应验收证据与限制。

| Issue | 实现与验收入口 |
| --- | --- |
| #1 配置及记录结构 | references/schemas 提供配置 v1、事件 v2、记录 v2 JSON Schema；fact/task/decision/issue/experiment/artifact 共享类型化结构；examples/record-v2-examples.json 由真实 record 写入测试验证。进行中和已确认缺证据会拒绝。 |
| #2 初始化 | init 在新目录建立结构化事件存储和可读视图；独立安装副本在临时中文/空格路径运行，已有目录拒绝覆盖。Windows/Linux CI 执行同一套测试。 |
| #3 追加与证据 | 写入前校验引用位置/格式，已确认必须记录用户明确确认出处；修订生成新事件，旧字节不变。模拟事件替换失败不留半条记录，视图失败保留已成功事件并提示 render。 |
| #4 派生视图 | ACTIVE_CONTEXT、CURRENT_STATUS、WORKLOG、DECISIONS_AND_ISSUES 等全部从同一事件源生成；删除全部派生文件后重建逐字相同，当前汇总排除旧修订，日志保留历史。 |
| #5 轻量续接 | 默认 resume 只打开有界 ACTIVE_CONTEXT，不调用 load；缺失、冲突、范围变化、正式交付、证据不足及明确审计请求返回 review_required 计划。Skill 按请求选择相关事件，不把新对话当新阶段。 |
| #6 跨平台与隐私 | Windows/Linux × Python 3.10/3.12；回归覆盖路径、结构、原子失败、默认 Git 忽略；check_public_tree 扫描已跟踪文件的已知密钥和个人路径模式，测试使用合成字符串且诊断不打印密钥。 |

## 本地复现

在仓库根目录运行：

```powershell
python -X utf8 -m unittest discover -s tests -v
python -X utf8 scripts/check_public_tree.py
```

核心新回归位于 `tests/test_issue_acceptance.py`，既有测试位于其他 `tests/test_*.py`。以具体提交的 [GitHub Actions](https://github.com/z-liu-xiugou/research-workbench-assistant/actions/workflows/tests.yml) 结果为准；没有跑过的环境不宣称已验证。

## 验收不代表什么

- confirmation 是记录者对用户明确确认的声明，不是身份认证；不能阻止恶意直接改文件或伪造授权。
- 文件证据检查位置和存在性，不阅读正文；URL/DOI 只检查格式，不证明真实、可访问或足以支持结论。
- 旧 v1 事件不自动变成已验证状态；audit 给出警告，用户复核后可追加 v2 修订。证据文件不一定在备份里，恢复后需另行核对。
- resume 是可验证的读取路由，不是科研结论自动审查器。除缺失/空/过长断点外，语义冲突等触发由使用者或 Codex 根据当前请求判断；没有通过全盘读取来暗中检查。尚无独立用户端 Codex 对话端到端验收。
- 隐私扫描只查已知模式及已跟踪工作树，不扫描完整 Git 历史，不保证识别全部密钥或未发表材料，发布前仍需人工审查。
- 关闭这些 v0.1 Issue 不等于未来功能全部完成；其他来源、PDF 解析、自动关系推断仍未实现。
