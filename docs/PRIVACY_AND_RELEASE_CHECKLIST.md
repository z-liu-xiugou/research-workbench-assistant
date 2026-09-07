# 隐私与发布检查清单

## 永远不得公开

- `_private_reference/`；
- API Key、访问令牌、Cookie、账号和邮箱；
- Zotero 私人集合键及本地数据库；
- 用户电脑绝对路径和用户名；
- 未公开研究计划、数据、实验结果和合作方材料；
- 受版权保护的论文全文、CAJ、扫描件和批量正文提取结果；
- 当前课题的真实工作日志、问题、决策和文献笔记；
- 不能确认许可证来源的代码和资源。

## 每次提交前检查

```powershell
git status --short
git diff --check
git grep -n -I -E "api[_-]?key|token|password|secret"
git check-ignore -v _private_reference/SOURCE_MANIFEST.json
```

还应检查：

- 是否出现盘符开头的 Windows 绝对路径；
- 示例是否含真实姓名、邮箱、组织、课题编号和未公开题目；
- 测试夹具是否完全可再分发；
- README 是否把计划功能误写成已实现；
- 第三方 API 和文献来源是否符合服务条款。

## 发布前检查

- 选择并添加明确的开源许可证；
- 添加安全问题报告方式；
- 添加依赖许可证清单；
- 在干净的 Windows/Linux 环境执行安装和测试；
- 使用新的空白科研项目验证初始化、续接和迁移；
- 确认 Git 历史中从未提交私人副本；
- 若私人内容曾进入 Git 历史，发布前必须清理历史并重新验证。
