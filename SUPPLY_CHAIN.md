# 资源供应链与上下游说明

## 供应链总览

```text
Stanford Encyclopedia of Philosophy
        │
        │ 版权、ISSN、原始百科内容来源
        ▼
Rivensa/SEP-CN
        │
        │ Markdown 中文资料源、目录、图片引用
        ▼
SEP-editing-cn / tools/build_sep_epub.py
        │
        │ 资源锁定、远程图片下载、回退匹配、占位保底、XHTML/OPF/nav/NCX 生成、EPUB 打包、审计
        ▼
dist/*.epub + reports/epub/*.json
        │
        │ 公开发布、阅读器导入、归档、后续人工校对
        ▼
读者 / 研究者 / 电子书阅读器
```

## 上游资源

### Stanford Encyclopedia of Philosophy

- 角色：百科内容、版权声明、ISSN 与目录识别信息来源。
- 版权声明：The Stanford Encyclopedia of Philosophy is copyright © 2026 by The Metaphysics Research Lab, Department of Philosophy, Stanford University.
- Library of Congress Catalog Data：ISSN 1095-5054
- EPUB 元数据中使用该机构作为 `dc:creator` 与 `dc:publisher`。

### Rivensa/SEP-CN

- 角色：中文 Markdown 资料源。
- 链接：<https://github.com/Rivensa/SEP-CN>
- 本仓库不复制该仓库正文内容，只通过 `source/SEP-CN` 和 `SOURCE.md` 指向上游。
- 本地构建时需要把该仓库克隆到 `.source/SEP-CN` 或通过 `--root` 指向外部克隆路径。

## 本仓库处理链路

- `tools/build_sep_epub.py`：构建主工具。
- 输入：外部 SEP-CN 本地克隆目录。
- 输出：EPUB 3 包、资源清单、孤儿 Markdown 清单、EPUB 审计报告。
- 资源策略：本地图片直接复制，远程图片下载并哈希命名，失效资源优先回退匹配，仍失败则生成占位 SVG，保证 EPUB 内无缺失图片引用。
- 审计策略：检查 mimetype、manifest、spine、XHTML/XML、图片引用、内部链接和锚点。

## 下游产物

- `dist/斯坦福哲学百科全书（中文版） - The Metaphysics Research Lab, Department of Philosophy, Stanford University.epub`
- `reports/epub/epub-audit.json`
- `reports/epub/release-manifest.json`
- `reports/epub/resource-manifest.json`
- `reports/epub/orphan-pages.json`
- `reports/epub/resource-scan.json`

## 发布边界

- 本仓库发布的是 EPUB 构建链、审计证据和 Release 附件发布流程；整理后的 EPUB 成品通过 GitHub Release 附件分发。
- 正文版权、原始 Markdown 源、原始目录维护和贡献历史以上游为准。
- TradeCatLabs 负责实验性整理、构建、审计、发布说明和自动化改进，不替代 SEP 或 SEP-CN 上游项目。
