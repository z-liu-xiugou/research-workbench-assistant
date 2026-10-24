# 可选图库组件与许可

本仓库自有源码保持 Apache-2.0。PDF 功能通过用户另行安装的组件运行，不在源码包中夹带 vendor、wheel、PDFium 二进制或第三方原始实现。第三方组件各自保留原许可证，不能将其一概标成 Apache-2.0。

| 可选组件 | 锁定版本 | 上游许可与用途 |
| --- | --- | --- |
| pdfplumber | 0.11.10 | MIT；文字、图注和图元区域分析 |
| pdfminer.six | 20260107，pdfplumber 的固定依赖 | MIT；PDF 文字分析 |
| pypdfium2 | 5.14.0 | 包装器使用 Apache-2.0 / BSD-3-Clause；渲染 PDF |
| pypdf | 6.21.2 | BSD-3-Clause；保留原 PDF 内容的页面变换和裁切 |
| Pillow | 12.2.0 | MIT-CMU；PNG、缩略图和跨页拼接 |

PDFium 及其二进制依赖有单独的许可证和 notices；pip 安装的发行包随包提供这些材料。若以后重新分发二进制，应保留对应版本全部许可文件。本仓库的依赖清单不替代上游许可全文；其他间接依赖也以安装包随附许可为准。

- [pdfplumber 许可证](https://github.com/jsvine/pdfplumber/blob/stable/LICENSE.txt)
- [pdfminer.six 许可证](https://github.com/pdfminer/pdfminer.six/blob/master/LICENSE)
- [pypdfium2 许可说明](https://pypdfium2.readthedocs.io/en/stable/readme.html#licensing)
- [pypdf 许可证](https://github.com/py-pdf/pypdf/blob/main/LICENSE)
- [Pillow 许可证](https://github.com/python-pillow/Pillow/blob/main/LICENSE)

原本地实现使用的 PyMuPDF 为 AGPL / 商业双许可；公开图库采用上表后端，不引入该依赖。当前源码包不分发任何论文全文、真实论文图片或作者源码素材，使用者应自行处理其已有资料的使用与分享权限。
