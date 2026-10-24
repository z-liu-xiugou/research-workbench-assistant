# 当前项目断点

更新时间：2026-10-24

## 当前目标

实施并推送用户确认的 #9 最小验收缺口整理与 M18 可选文献图库；仓库为独立 research-workbench-assistant，原课题材料不在发布范围。

## 当前进展

- #9 原试用清单和反馈模板已增补，独立提交 f7f5755；收到外部建议与完整真人验收分开登记。尚无完整外部验收记录，#9 保持开放，不能用自动化或AI自测代填。
- 图库已本地实现：figures extract/build/verify、可选pdfplumber/pypdfium2/pypdf/Pillow、逐篇可追溯归档、完整图修正与跨页，以及离线检索页面。基础命令只需标准库，图像与源PDF不进入工作台backup，须另备份。
- 新图待复核，人/AI核验独立于人工阅读；图源、裁切或图目改变撤回相应核验。原文和真实图片未复制到公开树。
- 图库41项专项中40通过、1项Windows链接权限跳过；实际页面中文搜索、组合筛选、两种视图、放大/跨页/来源/零图待定位和窄屏已检查。

## 正在收尾

- 完整提交的基础/可选测试、公开扫描、分发包安装副本及远端四组CI仍需核对，不能复用旧59aa306的证明。详细运行记录放outputs/figure-validation（不提交）。
- 完成后补充维护台账中的精确提交与CI证据；不创建标签或Release、不关闭#9/#12/#13。
- 下一步：接收真人对话试用；另行推进M03发布核对或M05升级预检。git pull不会更新既有安装副本。

## 按需入口

- docs/FIGURES.md、skills/research-workbench/references/figures.md、docs/THIRD_PARTY_NOTICES.md。
- docs/USER_TRIAL.md、.github/ISSUE_TEMPLATE/user-trial.md、docs/DISTRIBUTION_VALIDATION.md。
- docs/MAINTENANCE_PLAN.md、project-workbench/CURRENT_STATUS.md、WORKLOG.md最新记录。
