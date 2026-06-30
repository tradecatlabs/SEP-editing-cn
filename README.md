# SEP-editing-cn

SEP-editing-cn 是一个面向公开传播的 SEP-CN EPUB 构建、清洗、审计与发布仓库。

本仓库不内嵌 SEP-CN Markdown 正文源仓库；正文资料源只保留链接：<https://github.com/Rivensa/SEP-CN>。

## 发布产物

- `dist/斯坦福哲学百科全书（中文版） - The Metaphysics Research Lab, Department of Philosophy, Stanford University.epub`：当前本地 EPUB 成品；因文件超过 GitHub 普通 Git 100MB 单文件限制，不直接提交到 Git 历史。
- `reports/epub/`：当前 EPUB 对应的发布清单、资源清单、孤儿页面清单和审计报告。
- `tools/build_sep_epub.py`：从外部 SEP-CN Markdown 源构建 EPUB 的工具。
- `source/SEP-CN`：指向上游资料源的软链接，不包含正文内容。

## EPUB 元数据

- 标题：斯坦福哲学百科全书（中文版）
- 作者/创建者：The Metaphysics Research Lab, Department of Philosophy, Stanford University
- 出版者：The Metaphysics Research Lab, Department of Philosophy, Stanford University
- 版权声明：The Stanford Encyclopedia of Philosophy is copyright © 2026 by The Metaphysics Research Lab, Department of Philosophy, Stanford University.
- Library of Congress Catalog Data：ISSN 1095-5054
- 语言：zh-CN

## 供应链

本仓库采用“上游内容源 + 本地构建工具 + 可审计发布产物”的供应链模型：

1. 内容上游：Stanford Encyclopedia of Philosophy 的版权与目录识别信息。
2. 中文资料源：`Rivensa/SEP-CN`，地址为 <https://github.com/Rivensa/SEP-CN>。
3. 构建链路：`tools/build_sep_epub.py` 读取外部 SEP-CN 克隆目录，锁定图片资源，生成 EPUB 3 结构。
4. 审计证据：`reports/epub/` 保存资源清单、孤儿页面清单和 EPUB 门禁结果。
5. 下游产物：`dist/` 中的 EPUB 供阅读器、归档、Release 分发使用。

完整说明见 `SUPPLY_CHAIN.md`。

当前发布清单见 `reports/epub/release-manifest.json`。

EPUB 文件通过 GitHub Release 附件发布，流程见 `RELEASE.md`。

## TradeCatLabs

TradeCatLabs 是本仓库的实验性整理与发布主体，负责 EPUB 构建链、格式清洗、资源审计、公开发布说明和后续自动化改进。

- GitHub：<https://github.com/tradecatlabs>
- X：<https://x.com/tradecatlabs>

更多说明见 `TRADECATLABS.md`。

## 本地重新构建

```bash
git clone https://github.com/Rivensa/SEP-CN .source/SEP-CN
python3 tools/build_sep_epub.py --root .source/SEP-CN --jobs 8 --timeout 60 --retries 3 --keep-work
```

## 当前成品审计摘要

- EPUB XML 错误：0
- 缺失图片：0
- 内部坏链：0
- 资源下载/锁定错误：0
- 资源总数：1095
- 源站失效但已占位保底图片：28
- 源站失效但通过回退匹配恢复图片：23

## 发布边界

本仓库用于传播 EPUB 构建工具、审计证据与 EPUB 发布说明，不替代上游 SEP-CN 内容仓库。正文内容、原始 Markdown、原始许可证与贡献历史请以上游仓库为准。
