# SEP-editing-cn

<div align="center">

# 斯坦福哲学百科全书（中文版）EPUB

一个可复现、可审计、面向电子书阅读器的 SEP-CN EPUB 构建与发布仓库。

[![Release](https://img.shields.io/github/v/release/tradecatlabs/SEP-editing-cn?style=flat-square)](https://github.com/tradecatlabs/SEP-editing-cn/releases)
[![Downloads](https://img.shields.io/github/downloads/tradecatlabs/SEP-editing-cn/total?style=flat-square)](https://github.com/tradecatlabs/SEP-editing-cn/releases)
[![Last commit](https://img.shields.io/github/last-commit/tradecatlabs/SEP-editing-cn?style=flat-square)](https://github.com/tradecatlabs/SEP-editing-cn/commits/main)
[![Format](https://img.shields.io/badge/format-EPUB%203-blue?style=flat-square)](https://www.w3.org/publishing/epub3/)
[![Lab](https://img.shields.io/badge/lab-TradeCatLabs-black?style=flat-square)](https://github.com/tradecatlabs)

[下载 EPUB](https://github.com/tradecatlabs/SEP-editing-cn/releases/download/v2026.07.02/SEP-Chinese-The-Metaphysics-Research-Lab-Stanford-University.epub) ·
[查看 Release](https://github.com/tradecatlabs/SEP-editing-cn/releases/tag/v2026.07.02) ·
[构建说明](README-EPUB.md) ·
[供应链说明](SUPPLY_CHAIN.md)

</div>

---

## 这是什么

`SEP-editing-cn` 把上游 SEP-CN Markdown 资料源整理为适合 iOS Books、Kindle、Calibre 等阅读器使用的 EPUB 文件，并保留完整的资源清单与审计证据。

本仓库不复制上游正文源仓库；正文资料源只保留指针：<https://github.com/Rivensa/SEP-CN>。

## 快速下载

当前发布版本：`v2026.07.02`

| 文件 | 用途 |
| --- | --- |
| [SEP-Chinese-The-Metaphysics-Research-Lab-Stanford-University.epub](https://github.com/tradecatlabs/SEP-editing-cn/releases/download/v2026.07.02/SEP-Chinese-The-Metaphysics-Research-Lab-Stanford-University.epub) | EPUB 成品 |
| [release-manifest.json](https://github.com/tradecatlabs/SEP-editing-cn/releases/download/v2026.07.02/release-manifest.json) | 发布清单与 SHA256 |
| [epub-audit.json](https://github.com/tradecatlabs/SEP-editing-cn/releases/download/v2026.07.02/epub-audit.json) | EPUB 审计报告 |
| [resource-manifest.json](https://github.com/tradecatlabs/SEP-editing-cn/releases/download/v2026.07.02/resource-manifest.json) | 资源锁定清单 |

EPUB 文件大小约 `109MB`，超过 GitHub 普通 Git 单文件 `100MB` 限制，因此通过 GitHub Release 附件分发，不写入 Git 历史。

## 当前 EPUB 元数据

| 字段 | 值 |
| --- | --- |
| 标题 | 斯坦福哲学百科全书（中文版） |
| 作者/创建者 | The Metaphysics Research Lab, Department of Philosophy, Stanford University |
| 出版者 | The Metaphysics Research Lab, Department of Philosophy, Stanford University |
| 版权声明 | The Stanford Encyclopedia of Philosophy is copyright © 2026 by The Metaphysics Research Lab, Department of Philosophy, Stanford University. |
| Library of Congress Catalog Data | ISSN 1095-5054 |
| 语言 | zh-CN |

EPUB 标题页包含 TradeCatLabs 工程整理说明；该信息通过补丁工具写入标题页，不改 OPF、nav、NCX、封面、manifest 或 spine。

## 构建与审计结果

| 检查项 | 结果 |
| --- | ---: |
| EPUB XML 错误 | 0 |
| 缺失图片 | 0 |
| 内部坏链 | 0 |
| 资源下载/锁定错误 | 0 |
| 资源总数 | 1095 |
| 源站失效但已占位保底图片 | 28 |
| 源站失效但通过回退匹配恢复图片 | 23 |

审计证据保存在 `reports/epub/`，当前发布清单为 `reports/epub/release-manifest.json`。

## 供应链模型

```text
Stanford Encyclopedia of Philosophy
        ↓ 版权、ISSN、原始百科来源
Rivensa/SEP-CN
        ↓ Markdown 中文资料源
SEP-editing-cn / tools/build_sep_epub.py
        ↓ 资源锁定、EPUB 打包、审计
GitHub Release + reports/epub/*.json
        ↓
读者 / 研究者 / 电子书阅读器
```

详细说明见 `SUPPLY_CHAIN.md`。

## 本地重新构建

```bash
git clone https://github.com/Rivensa/SEP-CN .source/SEP-CN
python3 tools/build_sep_epub.py \
  --root .source/SEP-CN \
  --build-dir build/epub \
  --dist-dir dist \
  --jobs 8 \
  --timeout 60 \
  --retries 3 \
  --keep-work
```

只扫描目录和资源：

```bash
python3 tools/build_sep_epub.py --root .source/SEP-CN --scan-only
```

## 反馈与贡献

- EPUB 阅读器显示、目录、图片、元数据和构建问题：请在本仓库提交 Issue。
- 正文翻译、词条内容和 Markdown 原文问题：请优先反馈到上游 `Rivensa/SEP-CN`。
- 贡献前请阅读 `CONTRIBUTING.md`。

## 仓库结构

```text
.
├── CONTRIBUTING.md                   # 贡献和问题反馈边界
├── README.md                         # 项目入口、下载和状态说明
├── README-EPUB.md                    # EPUB 构建与审计说明
├── RELEASE.md                        # Release 附件发布流程
├── SOURCE.md                         # 上游资料源与版权边界
├── SUPPLY_CHAIN.md                   # 资源供应链与上下游说明
├── TRADECATLABS.md                   # TradeCatLabs 实验室信息
├── .github/                          # Issue 模板与 PR 模板
├── docs/README_PATTERNS.md           # README 调研与项目目录模式沉淀
├── dist/README.md                    # 本地 EPUB 产物目录说明
├── reports/epub/                     # 发布清单、资源清单、审计报告
├── source/SEP-CN                     # 指向上游资料源的软链接
├── tools/build_sep_epub.py           # EPUB 构建、资源锁定与审计工具
└── tools/patch_epub_tradecatlabs_notice.py # 保持元数据/封面/目录不变的标题页补丁工具
```

## TradeCatLabs

TradeCatLabs 负责本项目的 EPUB 工程化整理、资源审计、发布说明和自动化改进。

- GitHub：<https://github.com/tradecatlabs>
- X：<https://x.com/tradecatlabs>

## 参考项目

README 与目录结构参考了 Standard Ebooks 工具链、Free Programming Books、mdBook EPUB backend 等公开项目的通用表达方式；具体调研记录见 `docs/README_PATTERNS.md`。

## 边界声明

- TradeCatLabs 不声明拥有 Stanford Encyclopedia of Philosophy 正文版权。
- 本仓库不替代 `Rivensa/SEP-CN` 上游内容仓库。
- 正文版权、原始 Markdown、原始许可证和贡献历史请以上游项目为准。
- 本仓库新增价值集中在 EPUB 构建链、资源完整性、审计证据和发布可追溯性。
