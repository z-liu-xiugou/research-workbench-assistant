# 当前项目断点

更新时间：2026-10-08

## 当前目标

维护独立开源 research-workbench-assistant，让用户可以安装、记录、诊断和恢复科研工作台。维护任务以 docs/MAINTENANCE_PLAN.md 为入口。

## 最新授权与已确认产出

- 用户要求批量维护并提交远端；本轮完成 M02/M04/M12/M13，M01 已于前轮完成。
- M02：指定 Git 提交的 ZIP 在中文/空格临时路径安装；删除解包源码后运行安装副本，24 步验证通过，恢复前后原始记录字节一致；14 项故障回归通过。
- M04：doctor 只读诊断版本、技能文件、静态目录权限、两类锁、工作台配置和必要路径；默认隐藏个人路径，输出中文建议，退出 0/1/2。不读取研究事件、不删除锁、不修复视图。
- M12：每周一北京时间 09:30 检查 Actions 版本，最多 3 个更新 PR，完整 SHA 固定、人工审查。GitHub Dependabot 检查任务成功，尚无实际更新 PR。
- M13：现有 Windows/Linux × Python 3.10/3.12 四组 CI 新增当前提交包的独立安装流程检查。

## 实现证据与边界

- 实现提交：9ec8302（M12）、e535573（M04）、bbbff1c（M02）、9e0ea70（M13）；均已推送。
- 本地完整 114 项：112 通过、2 项 Windows 链接权限跳过；公开扫描 0 命中、git diff --check 通过。
- 实现 SHA 9e0ea70c6f7d8ce8090b86e9464709f05b6de66d 的 tests CI 37724325620 四组测试/扫描/分发包检查全部成功。收尾文档及后续提交应按各自 SHA 检查，不沿用这项证据。
- 主分支仍为未发布 alpha.9 / CLI 0.1.0a9，Release 仅 alpha.1；本轮没有创建标签或 Release。#9 外部真人试用保持开放。
- 静态权限通过不保证实际写入成功；锁存在不能判断失效；脚本与包验证不能证明 Codex 加载技能或替代真人试用。

## 下一步与按需读取

- 下一默认项 M03：核对届时最终提交、CI、标签和实际下载包后发布预览版；若继续开发，可优先 M05 升级预检。
- docs/MAINTENANCE_PLAN.md、docs/RELEASE_PREPARATION.md、docs/DISTRIBUTION_VALIDATION.md。
- doctor 相关读取 docs/DIAGNOSTICS.md、skills/research-workbench/scripts/workbench.py、tests/test_doctor.py。
- CI/依赖读取 .github/workflows/tests.yml、.github/dependabot.yml、docs/DEPENDENCY_UPDATES.md。
- project-workbench/CURRENT_STATUS.md 首条和 WORKLOG.md 最新条保留详细记录。
