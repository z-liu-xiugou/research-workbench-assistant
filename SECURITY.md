# Security Policy

## Supported versions

项目目前处于 pre-alpha 阶段，尚无稳定发布版本。安全和隐私问题仍会被认真处理。

## Reporting a vulnerability

请不要在公开 Issue 中发布以下内容：

- API Key、Token、Cookie 或其他凭据；
- 可识别个人身份的信息；
- 未公开论文、数据或研究记录；
- 可以造成任意文件读取、路径逃逸或越权访问的完整利用细节。

请通过 GitHub 仓库的 **Security → Report a vulnerability** 私下报告。报告中请包含受影响文件、复现条件、可能影响和建议修复方向，但不要附带真实用户数据。

## Security priorities

本项目优先处理：

- 路径逃逸和越权文件访问；
- 密钥或私人研究内容泄漏；
- 不安全的外部命令执行；
- 文献来源和下载权限绕过；
- 结构化状态被部分写入或损坏；
- 插件、连接器和第三方依赖供应链风险。
