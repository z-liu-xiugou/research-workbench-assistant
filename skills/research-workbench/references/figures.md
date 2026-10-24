# 本地文献图片：提取、归档和离线检索

本功能把用户已有 PDF 中的完整 Figure 区域保存成可追溯图片，再生成离线检索页面。它不下载论文、不改写原图，不提供 OCR，也不自动证明整篇图目齐全。新结果先标记为待复核。

## 先准备输入

仅处理用户指定的文件，不扫描整个磁盘。将下面的虚构清单保存为 `scope.json`；`pdf_path` 和可选 `note_path` 相对清单所在目录解析，与启动命令的目录无关。

```json
{
  "schema_version": 1,
  "papers": [{
    "ledger_id": "DEMO-001",
    "title": "虚构的图片提取示例",
    "authors": ["示例作者"],
    "year": 2026,
    "section": "方法参考",
    "tags": ["演示"],
    "pdf_path": "原文/示例.pdf",
    "note_path": "笔记/示例.md"
  }]
}
```

ID 必须唯一且能安全用作文件夹名。推荐只用英文字母、数字、短横线和下划线。不要使用真实课题资料制作公开反馈。

## 安装可选组件并运行

下面示例从仓库根目录运行。使用安装副本时，把脚本和 requirements 路径改为实际技能目录。使用你当前 Python 环境，也可以另外创建虚拟环境；这些组件不是基础工作台的安装要求。

```powershell
python -m pip install -r skills/research-workbench/requirements-figures.txt
python -X utf8 skills/research-workbench/scripts/workbench.py figures extract --scope scope.json --output figure-gallery
python -X utf8 skills/research-workbench/scripts/workbench.py figures verify --root figure-gallery
python -X utf8 skills/research-workbench/scripts/workbench.py figures build --root figure-gallery
```

然后双击图库目录中的 `index.html`。页面内嵌检索数据，无需网络或本地服务；默认显示全部正式图，支持按文献/按图、中文关键词及组合筛选、放大和来源导航。它是快照，修改清单后重新 build；网页中没有导入、裁切或编辑按钮。

也可以在 Codex 说：

```text
$research-workbench 请按我指定的 scope.json 提取论文完整图，建立独立图库并生成离线检索页面。先保留待复核状态，不改原PDF，不把AI检查写成人工已读。
```

`extract` 可用 `--ids DEMO-001` 只处理指定文献、`--dpi 300` 指定导出分辨率。`--skip-existing` 只跳过来源、修正和资产均未变化的结果；裁切修正后不要依赖旧结果。`verify` 只读检查结构、来源和资产，不代表视觉核验；退出码 0 为结构通过，1 为发现问题，2 为参数或运行错误。没有检测到图注时仍须检查原页，不能直接记为“无图”。

## 修正裁切并填写说明

完整图应包括子图、坐标、图例和箭头。查看原页校对图后，在修正文件中填写 PDF 页序与区域，页序从封面开始为 1。坐标单位为 PDF 点（72 点约为 1 英寸），按页面显示方向的左上角计 `[左, 上, 右, 下]`。

```json
{
  "papers": {
    "DEMO-001": {
      "figures": [{
        "figure_number": "1",
        "caption": "Fig. 1. Synthetic demonstration",
        "segments": [{"page": 1, "bbox": [40, 70, 550, 330]}]
      }]
    }
  }
}
```

跨页图按阅读顺序添加多个 `segments`，重新运行 extract 并传入 `--overrides overrides.json`。程序输出完整图 PNG、缩略图、保留原内容的裁切 PDF、分段资产、原页校对图和逐篇 `figures.json`。跨页 PNG 按顺序拼接，PDF 按段保留页面。自动定位是候选区域，必须对照原页检查，不保证自动排除所有正文。

中文解释与原图注分开维护在逐篇 `figures.json` 的 `annotations`：`summary_zh` 表示图意，`reference_use_zh` 表示参考建议，`limitation_zh` 表示适用限制。填写来自人工或 Codex 的实际阅读结果，不由提取程序编造。

检查通过后才将该图 `review_status` 设为 `verified`，并以 `review_method=human` 或 `ai` 区分复核方式。AI 检查不等于人工已读；逐图通过也不等于整篇覆盖通过。来源或裁切变化会撤回旧核验，须重新查看。修改说明后重新 build，不要分别手改网页、汇总清单和 Markdown 导航。

## 保存、移动与备份

`papers/文献ID/figures.json` 与该篇资产是归档记录；`gallery_manifest.json`、网页和 Markdown 导航是可重新生成的视图。生成器拒绝覆盖同名人工页面。提取按篇暂存，失败保留该篇旧归档；批次部分失败需要按输出重新处理失败文献。

本功能引用原 PDF 和笔记，不搬动它们。归档使用相对来源链接，整体移动项目时保持原文、笔记与图库的相对目录关系。只搬图库时图像仍在，原文和笔记链接可能失效，应修改清单并重建。

现有工作台 `backup/restore` 只覆盖受管理记录，不包含此图库、论文或实验数据。备份图库须另行复制完整图库目录、输入清单、修正文件、原文和需要的笔记；恢复后 verify 并重新 build。不要只备份 HTML。

**裁切 PDF 是显示范围裁切，不是脱敏删除。** 页内其他内容可能仍可恢复；对外分享前核对，图片可选 PNG。工具不自动公开任何论文、图片或生成页面。依赖许可证见[第三方组件说明](https://github.com/z-liu-xiugou/research-workbench-assistant/blob/main/docs/THIRD_PARTY_NOTICES.md)。
