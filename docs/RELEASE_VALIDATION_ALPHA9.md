# alpha.9 发布验收

日期：2026-10-29。M03 已完成；本页记录实际发布与下载复核，历史开发记录不作为替代证据。

| 项目 | 实际结果 |
| --- | --- |
| Release | [v0.1.0-alpha.9](https://github.com/z-liu-xiugou/research-workbench-assistant/releases/tag/v0.1.0-alpha.9)，公开，`prerelease=true`，非草稿 |
| 标签提交 | `bfd6e097a8548f0f1dda2af23d33a3f77651daf4`；发布后已获取远端标签并核对 |
| CLI | `0.1.0a9` |
| 远端检查 | [CI 40854871236](https://github.com/z-liu-xiugou/research-workbench-assistant/actions/runs/40854871236)，准确对应发布提交；Ubuntu 24.04 / Windows × Python 3.10 / 3.12 四组均成功 |
| 各组检查范围 | 源码测试、公开文件扫描、基础分发包隔离安装、可选 PDF 图库测试与安装副本验证 |
| 本地完整测试 | Windows / Python 3.10.20，安装 PDF 组件时共 183 项，179 通过、4 项链接权限跳过；不安装 PDF 组件时 164 通过、19 跳过（含 15 项 PDF 集成） |
| 基础分发流程 | `verify_distribution.py --ref bfd6e097a8548f0f1dda2af23d33a3f77651daf4`，28 步通过 |
| 可选图库流程 | 同一准确提交增加 `--figures`，32 步通过 |
| ZIP 内容 | `git archive --format=zip`，111 个成员、94 个文件，仅跟踪源码与虚构示例 |
| 下载与安装复核 | 上传草稿后下载全部 4 个资产，哈希逐一匹配；从下载 ZIP 隔离安装，版本为 `0.1.0a9`。公开发布后再次下载 ZIP，SHA-256 仍一致 |

## 公开资产

- `research-workbench-assistant-v0.1.0-alpha.9.zip`：源码与 Skill，255609 字节。
- `distribution-core.json`：基础隔离验证报告。
- `distribution-figures.json`：可选图库隔离验证报告。
- `SHA256SUMS.txt`：上述 3 个文件的 SHA-256。

源码 ZIP 的 SHA-256：

```text
0c420e7487b3a0df8d1d4ea81bafa073da904e79fbe1d272d0fa215e75199673
```

两个报告记录的归档哈希与实际 ZIP 一致。GitHub 自动生成的 “Source code” 包包含顶层目录，不能用本资产的哈希直接核对它。

## 范围与限制

- 发布只包含公开源码，不包含私人参考、真实研究记录、论文、图库或本地环境。可选第三方库另行安装，许可见 THIRD_PARTY_NOTICES.md。
- 自动检查和虚构数据安装验证不等同于真人 Codex 技能发现、新聊天续接体验或科研结论验证；#9/#12/#13 保持开放，未代填外部用户记录。
- 本验收页及发布后工作台状态是随后追加的维护文档；发布标签保持指向上表的已验证提交，不移动到后续状态提交。
