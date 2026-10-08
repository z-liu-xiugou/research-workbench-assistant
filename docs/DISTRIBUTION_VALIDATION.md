# 分发包安装与流程验证

`scripts/verify_distribution.py` 验证指定 Git 提交的源码 ZIP 能否安装，以及安装副本能否完成基本操作。它先从提交打包，再解包、安装、运行；不会直接使用源码树中的工作台 CLI，也不会安装到维护者正在使用的技能目录。

## 运行方式

需要 Python 3.10+ 和 Git，无额外 Python 依赖。在仓库根目录执行：

```powershell
python -X utf8 scripts/verify_distribution.py
```

默认检查 `HEAD`，也就是最新的**已提交**版本。文件刚改好但尚未提交时，检查的包仍然来自旧提交。确认准备发布的准确提交时，显式指定版本：

```powershell
python -X utf8 scripts/verify_distribution.py --ref HEAD
python -X utf8 scripts/verify_distribution.py --ref v0.1.0-alpha.1
```

第二行只是指定标签的方法示例；旧标签若缺少当前必需文件或命令，会正常报告失败。也可以把标签替换为完整提交 SHA。Git 先把输入解析为提交，再用解析出的完整 SHA 打包，避免检查期间分支移动造成版本混用。

终端输出 JSON；成功退出码为 `0`，失败为 `1`。`commit` 是实际被测的完整提交 SHA；`archive` 记录 ZIP 格式、成员数量和 SHA-256；`environment` 记录 Python、系统和处理器；`steps` 记录实际执行的步骤和子进程退出码。拒绝重复安装的预期退出码是 `1`，这一步通过时仍标记为 `ok: true`。

需要保存本轮证据时，可重定向到本地报告文件，再核对其中的 SHA 与待发布提交一致：

```powershell
python -X utf8 scripts/verify_distribution.py --ref HEAD > distribution-report.json
```

不要仅凭生成了报告文件判断通过：还须核对命令退出码和报告中的 `ok`。报告不打印用户名、个人绝对路径、虚构工作台正文或子进程原始日志；失败会显示检查阶段和规则。

## 实际检查内容

1. 用 `git archive --format=zip` 从指定提交生成源码包；未提交文件、Git 忽略的本地参考副本不会被打包。
2. 在解包前检查安装器、技能说明、工作台 CLI、文献模块、记录说明和结构文件是否存在且非空。
3. 拒绝已知私有目录、论文/表格/密钥文件、缓存、真实工作台的 `events/` 和 `notes/` 目录；同时拒绝越界路径、链接、特殊文件、重复名字、大小写冲突及不适用于 Windows 的文件名。ZIP 限制为 64 MiB、10000 个成员；解压后的总大小也限制为 64 MiB。
4. 在包含中文和空格的临时目录中解包，用包内的 `scripts/install.py --dest` 安装到临时技能目录，并逐文件比对安装内容。再次安装必须被拒绝，已有文件原字节必须保持不变。
5. 删除临时解包源码，再运行**安装副本**的 CLI，完成 `init → record → search → show → resume → backup → restore`。输入只有脚本生成的虚构记录，包含一次修订，以检查旧历史不会丢失。
6. 核对恢复后的配置、全部事件、手写笔记和项目约定的原字节；检查 `.gitignore`、当前版本及历史版本的 `show` 输出、`resume` 输出，并运行 `audit`。恢复不能改动原工作台。

临时目录在运行结束后清理，包括虚构记录和备份。安装命令始终传入 `--dest`，不调用用户级默认安装。

## 回归测试与 CI

只运行本项回归测试：

```powershell
python -X utf8 -m unittest discover -s tests -p test_distribution.py -v
```

测试先取得真实提交的 `git archive`，再故意删除 CLI、文献模块或结构文件，放入私有材料、越界路径和链接，确认这些包在创建解包目录前就被拒绝。另建临时 Git 仓库：让最新提交缺文件、让工作目录中的 CLI 故意报错，仍要求指定的较早完整提交能通过流程，以防检查脚本误用本地源码或错误的提交。还会让安装后的 CLI 退出码为 `0`、却返回错误的 JSON 类型，确认检查不能只凭退出码误判通过。

CI 使用同一条分发检查命令：

```text
python -X utf8 scripts/verify_distribution.py --ref HEAD
```

仓库工作流在 Ubuntu 24.04 / Windows、Python 3.10 / 3.12 的四组环境执行。源码单元测试负责具体功能和失败场景；分发检查负责已提交包的完整性、隔离安装和基本流程，不重复运行完整功能测试。是否已经通过四组 CI，须以该提交的实际 Actions 结果为准。

## 验收边界与本地记录

这项验证的是 `git archive` 生成的源码包，不是 pip 安装包；暂不下载 GitHub Release，也不证明某个已发布资产与被测包完全一致。发布时仍须核对标签、实际下载入口和下载后的包。包成员规则用于发现已知私有材料和误打包，不能证明任意正文都不含隐私；公开文件扫描与人工审查仍按仓库现有流程执行。

`resume` 检查只证明安装副本能返回一致的续接读取计划，不证明 Codex 已发现技能，也不替代 [外部真人试用](USER_TRIAL.md) 或 Issue #9。

2026-10-08 的本轮实现提交复核记录：

| 项目 | 实测结果 |
| --- | --- |
| 被测包源码 SHA | `9e0ea70c6f7d8ce8090b86e9464709f05b6de66d` |
| 环境 | Windows / AMD64 / Python 3.10.20 |
| 打包产物 | 87 个 ZIP 成员，72 个文件；`git archive --format=zip` |
| ZIP SHA-256 | `b6ea0ef10ae49ff5cdb951a6883a4e34dda7efcd28257fc2a735908798504dca` |
| 安装后 CLI | `0.1.0a9` |
| 基本流程 | 24 个实际步骤通过；恢复 2 条事件，1 条当前记录 |
| 本项回归测试 | 14 项通过，含多个破包子样例 |
| 完整本地测试 | 114 项中 112 通过、2 项 Windows 链接权限跳过；公开扫描 0 命中 |
| 远端 CI | [37724325620](https://github.com/z-liu-xiugou/research-workbench-assistant/actions/runs/37724325620)：四组源码测试、公开扫描及包安装验证全部通过 |

上述是实现提交的验证快照，包含只读诊断和完整分发检查。后续文档提交、标签和 Release 不能沿用该结果作为自身通过证据，应重新执行并保存新的完整 SHA；CI 会继续检查每次提交的包。
