# 只读环境与安装诊断

`doctor` 用于排查“脚本版本不对、安装缺文件、目录权限有问题、发现锁、配置损坏”等问题。它只观察本地文件状态，不修改工作台，不删除锁，也不读取科研事件正文。

## 在 PowerShell 中运行

在下载的仓库目录运行安装检查：

```powershell
python -B -X utf8 .\skills\research-workbench\scripts\workbench.py doctor
$LASTEXITCODE
```

`-X utf8` 让 Python 按 UTF-8 处理中文；`-B` 避免 Python 生成导入缓存文件。输出是一份 JSON 报告。省略 `--root` 时只检查安装和运行环境，不搜索个人项目。

同时检查指定工作台：

```powershell
python -B -X utf8 .\skills\research-workbench\scripts\workbench.py doctor --root .\research-workbench
```

`--root` 指向存放 `config.json` 和 `events/` 的工作台。它不是技能安装目录。默认待检查技能目录是**正在运行的脚本所属的技能目录**，所以从安装副本运行时会检查该副本。

如果使用仓库里的脚本检查另一个安装副本，可显式指定技能目录：

```powershell
python -B -X utf8 .\skills\research-workbench\scripts\workbench.py doctor --skill-dir .\installed-skills\research-workbench --root .\research-workbench
```

脚本不会导入或执行 `--skill-dir` 内的程序；只读取版本声明和观察必要文件。目标脚本与当前运行脚本版本不同会提示核对。

## 如何读取报告

`checks` 中每一项包含 `scope`、`code`、`status`、`message` 和 `advice`。`scope` 区分环境、安装和工作台；`code` 是便于反馈的固定状态码；中文说明及建议解释发现的问题。`status` 有四种：

| status | 含义 |
| --- | --- |
| ok | 本次观察通过，仍受检查范围限制 |
| warning | 需要核对，例如发现锁、静态观察不可写或派生视图缺失 |
| error | 存在必要文件缺失、配置错误或该项无法读取等问题 |
| skipped | 未选择工作台、目录未建立等情况，未执行该项观察 |

报告整体的 `status` 和 `exit_code` 对应以下结果。PowerShell 的 `$LASTEXITCODE` 与 JSON 内的 `exit_code` 相同：

| 退出码 | 含义 |
| --- | --- |
| 0 | 检查没有 error 或 warning；skipped 不计为故障 |
| 1 | 至少一项 warning，没有 error |
| 2 | 至少一项 error |

例如，工作台锁存在时，这一项会返回 `code=WORKBENCH_LOCK`、`status=warning`，建议先核实相关进程。锁可能对应正在运行的程序，也可能来自此前中断；**仅凭存在不能判断锁失效**。诊断不会读取或删除锁。

## 检查范围和状态码

| scope | code | 检查内容 |
| --- | --- | --- |
| environment | PYTHON_VERSION | 当前 Python 版本是否符合 3.10+；运行平台和工具版本见 runtime |
| environment | DOCTOR_PATH | 仅在无法定位诊断目录时报告 |
| installation | SKILL_FILES | SKILL.md、三份脚本、离线页面模板、记录/检索/入门说明、项目约定模板及三份结构定义是否存在、类型是否正确 |
| installation | TOOL_VERSION | 静态读取目标脚本 VERSION；不执行目标程序，不验证文件哈希 |
| installation | SKILL_LOCATION | 识别用户技能目录、项目 `.agents/skills` 或源码/自定义目录；不查询 Codex 实际加载状态 |
| installation | SKILL_ACCESS | 技能目录的静态读取、访问和写入权限观察 |
| installation | INSTALL_PARENT_ACCESS | 技能父目录权限观察，安装和升级通常需要此处写入权限 |
| installation | INSTALL_LOCK | 技能父目录 `.research-workbench.install.lock` 是否存在 |
| workbench | WORKBENCH_NOT_SELECTED | 未传入 `--root`，跳过工作台检查 |
| workbench | WORKBENCH_PATHS | 原始 config/events、派生视图、手写文件和 `.gitignore` 的存在及类型；越界链接会报错 |
| workbench | WORKBENCH_CONFIG | 配置 JSON 及配置结构是否有效；不输出工作台名称或原文 |
| workbench | WORKBENCH_ACCESS / EVENTS_ACCESS / NOTES_ACCESS | 对应目录的静态权限观察；空工作台尚无 notes 目录时跳过 |
| workbench | WORKBENCH_LOCK | 工作台 `.write.lock` 是否存在 |

必要原始文件缺失属于 error。派生视图或手写文件缺失属于 warning：应先核对备份和原始记录，不能一律当作空工作台重建。`doctor` 不比较派生视图内容，也不扫描事件数量或记录结构；这类检查另用 `audit`。

## 脱敏和只读边界

默认报告只用 `<skill>`、`<workbench>` 标记位置，不输出个人绝对路径、项目名称、事件内容、锁正文或异常原文。公开反馈时优先使用默认报告。

只有本地排查确实需要实际路径时，增加 `--include-paths`：

```powershell
python -B -X utf8 .\skills\research-workbench\scripts\workbench.py doctor --root .\research-workbench --include-paths
```

此时 `redacted=false`，`locations` 包含实际路径。即使显式显示路径，报告仍不输出记录或配置正文。公开提交前请移除个人路径。

每项检查分别捕获错误，返回异常类别而不返回异常文本。坏 JSON、无法读取文件或损坏目标脚本不会阻止其他项输出。命令参数用法错误，例如 `--root` 后没有值，仍由 argparse 输出使用说明到 stderr 并返回 2；这类错误不产生诊断 JSON。

目录权限通过 `os.access` 静态观察，不创建测试文件。ACL（账户访问控制）、只读挂载、磁盘状态、并发变化等仍可能让之后的实际操作失败；“观察通过”不保证写入成功。观察也可能更新系统维护的访问时间，不承诺文件系统元数据完全不变。

诊断只读取已知安装文件及配置：目标脚本读取上限 1 MiB，配置读取上限 64 KiB。不会联网、建立目录、获取写入锁、运行 `render`、调用 `load` 读取事件，或自动修复问题。必要文件存在和版本声明一致不证明发布包未被修改，也不证明 Codex 成功加载了技能、科研结论成立或外部服务可访问。

## 维护者验证

```powershell
python -B -X utf8 -m unittest discover -s tests -p test_doctor.py -v
```

测试覆盖正常安装副本、缺少检索模块仍能输出 JSON、必要路径缺失、静态不可写/不可读观察、两类锁保留、坏配置、默认脱敏、目标脚本静态版本读取、单项故障隔离，以及不读事件、不调用写入或视图重建的约束。
