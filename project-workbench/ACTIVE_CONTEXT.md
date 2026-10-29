# 当前项目断点

更新时间：2026-10-29

## 本轮 M03 发布

- 已确认：用户授权发布 alpha.9，并在发布后准备 Codex for Open Source 申请。
- 已确认：M03 完成。[alpha.9 Release](https://github.com/z-liu-xiugou/research-workbench-assistant/releases/tag/v0.1.0-alpha.9) 为公开预览版，标签指向 bfd6e097a8548f0f1dda2af23d33a3f77651daf4；四组 CI 40854871236 和基础28/图库32步隔离安装通过。公开下载ZIP与测试包哈希一致，安装副本版本0.1.0a9。证据见 docs/RELEASE_VALIDATION_ALPHA9.md。
- 个人申请字段仅用于申请，不写入公开文件；#9/#12/#13 仍保留其真人验收边界。后续接收首版反馈，开发维护可推进 M05；申请提交需另核实官网回执。

以下保留上一轮开发背景，当前任务以本节为准。

## 当前目标与已完成

独立开源 research-workbench-assistant 的 #9 缺口文档与 M18 可选文献图库已实现并推送。原课题、论文和私人图库不在发布范围。

- f7f5755：原试用清单补充自动化覆盖与三项真人缺口；原模板增加完整SHA、协助情况、同演示ID、逐步结果和新聊天确认。已收到#12/#13建议，但完整外部验收仍待真实记录，#9保持开放。
- 28dfcf6：figures extract/build/verify、按篇可追溯归档、完整区域修正与跨页、300dpi PNG/缩略图/矢量裁切PDF/原页校对图，以及离线中文检索。基础命令只需标准库，PDF提取另装锁定依赖；图像与原PDF须另外备份。
- 新图待复核，人/AI核验独立于人工阅读；图源、裁切或图目改变撤回相应核验。来源、手写内容和人工页面保护、失败回滚均已检查。
- 实现提交28dfcf6的32步安装包及四组CI 40070835352全部通过。实际浏览器中文搜索、组合筛选、视图、放大/跨页/来源、无图注待定位、390像素窄屏及移动目录检查通过，无外部资源请求。
- 收尾补强分段/原页校对图哈希检查；完整本地183项中179通过、4项Windows链接权限跳过；无PDF组件时164通过、19跳过（含15项PDF集成）。最终包/CI按其自身SHA单独核对，报告保留outputs/figure-validation，不复用实现提交包哈希。

## 下一步与边界

- 接收至少一名自愿外部用户的完整Codex流程结果；不把AI自测、使用建议或图库自动检查视为#9通过。
- 后续独立任务可推进M03发布核对或M05升级预检；本轮未创建标签/Release，未关闭#9/#12/#13，未对外联系用户。git pull不会更新既有技能安装副本。
- 图库页面仅浏览检索，清单/Codex维护裁切及说明；没有网页编辑器、OCR、全文下载或自动论文解读。

## 按需入口

- docs/FIGURES.md、skills/research-workbench/references/figures.md、docs/THIRD_PARTY_NOTICES.md。
- docs/USER_TRIAL.md、.github/ISSUE_TEMPLATE/user-trial.md、docs/DISTRIBUTION_VALIDATION.md。
- docs/MAINTENANCE_PLAN.md、project-workbench/CURRENT_STATUS.md、WORKLOG.md最新记录。
