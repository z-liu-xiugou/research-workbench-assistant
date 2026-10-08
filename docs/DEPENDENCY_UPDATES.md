# GitHub Actions 依赖更新提醒

Dependabot 是 GitHub 提供的更新机器人：它检查工作流引用的 Action 是否有新版本，并提出 PR（合并请求）供维护者审查。本仓库的配置位于 [`.github/dependabot.yml`](../.github/dependabot.yml)，范围仅为 GitHub Actions。

## 配置及含义

```yaml
version: 2
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "09:30"
      timezone: "Asia/Shanghai"
    open-pull-requests-limit: 3
```

- `version: 2`：采用 Dependabot 的第 2 版配置格式。
- `github-actions` 和 `directory: "/"`：检查 `.github/workflows` 下的工作流及根目录的 `action.yml` / `action.yaml`；不检查 Python 包或运行器系统镜像版本。
- `weekly`、`monday`、`09:30`、`Asia/Shanghai`：每周一北京时间 09:30 检查。首次添加或修改配置也可能触发检查，不应只等待下周一。
- `open-pull-requests-limit: 3`：同一时间最多保留 3 个版本更新 PR。已有 PR 合并或关闭后才能继续提出新 PR；这不是每周更新数量上限。GitHub 的安全更新 PR 不受此上限限制。

配置进入默认分支后，Dependabot 默认向该分支提出更新 PR。配置方法参见 [GitHub Actions 更新说明](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/secure-your-dependencies/auto-update-actions)；字段定义和 PR 数量限制参见 [Dependabot 配置参考](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference)。

## 完整 SHA 和现有 CI

工作流中的 Action 使用完整提交 SHA：`uses: actions/checkout@<40 位提交 SHA>`。SHA 是一份确定的代码版本标识；使用完整值可以避免版本标签被移动后，同一配置运行了不同代码。同一行的版本注释方便人工对应发布版本。

Dependabot 支持更新这种提交引用，并支持更新同一行的版本注释。如果原提交不对应发布标签，机器人可能改为最新提交，因此审查时仍要核对上游仓库及发布记录。参见 [GitHub Actions 支持范围](https://docs.github.com/en/code-security/reference/supply-chain-security/supported-ecosystems-and-repositories#github-actions)。

更新 PR 会由当前 [`tests` 工作流](../.github/workflows/tests.yml) 的 `pull_request` 事件触发检查。当前矩阵包含 Ubuntu 24.04 / Windows 和 Python 3.10 / 3.12，共 4 组环境；每组运行单元测试、`scripts/check_public_tree.py` 公开文件检查和 `scripts/verify_distribution.py --ref HEAD` 分发包验证。仓库未设置自动合并流程，维护者应等待检查完成后人工决定是否合并。

Dependabot PR 的 GitHub token 默认只读，且不能取得普通 Actions secrets。当前测试不依赖这些 secrets，并显式使用 `contents: read`。参见 [Dependabot 触发 Actions 的限制](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-on-actions)。

这里配置的是版本更新提醒。GitHub 对固定 SHA 的 Actions 不生成 Dependabot 漏洞警报，不能把本配置等同于完整安全漏洞扫描。参见 [GitHub Actions 安全使用参考](https://docs.github.com/en/actions/reference/security/secure-use)。

## 人工审查和失败处理

1. 看 PR 差异：仍应使用上游 Action 仓库的 40 位提交 SHA，并核对同一行版本注释。阅读发布说明，尤其留意大版本升级及最低运行器要求。
2. 在 PR 的 Checks 页面确认 4 组测试、公开文件检查及分发包验证全部通过。失败时先打开具体任务日志定位原因，再修复或关闭该更新 PR；不为合并而跳过测试或扩大 token 权限。
3. 检查没有额外权限、私有地址或无关改动，通过后人工合并。测试成功并不能替代阅读 Action 发布说明。
4. 若没有 PR，先确认配置已在默认分支，再查看仓库的 Dependabot 更新任务日志：依赖已经最新、达到 PR 上限或配置错误，处理方式各不相同。没有新版本时，不出现 PR 是正常情况。

## 验证边界

提交配置前，可以本地解析 YAML，核对官方字段，并检查当前工作流的 PR 触发、权限和测试矩阵。这些检查能够确认配置结构和仓库准备情况。

只有实际观察到 Dependabot 更新 PR、SHA 差异以及该 PR 的 4 组 CI 结果，才能记录机器人更新行为已验证。本地解析通过、普通提交的 CI 通过或暂时没有更新 PR，都不能代替这项观察。

2026-10-08 配置推送后，GitHub 的 Dependabot 检查任务 [37724330712](https://github.com/z-liu-xiugou/research-workbench-assistant/actions/runs/37724330712)、[37724336115](https://github.com/z-liu-xiugou/research-workbench-assistant/actions/runs/37724336115) 均成功，说明 GitHub 已执行检查。核对时仍无开放 PR；尚未观察实际更新 PR、SHA 差异及其 CI，不将检查任务成功记作完整更新流程验收。
