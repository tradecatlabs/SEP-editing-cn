# SEP-CN EPUB 构建与发布说明

本仓库不直接保存 SEP-CN Markdown 正文源。构建时需要通过 `--root` 指定一个本地 SEP-CN 源目录。

资料源链接：<https://github.com/Rivensa/SEP-CN>

## 已包含内容

- `tools/build_sep_epub.py`：EPUB 构建、资源锁定、打包与审计工具。
- `tools/patch_epub_tradecatlabs_notice.py`：只修改标题页正文提示，并验证 OPF、nav、NCX、封面、manifest、spine 不变。
- `tools/patch_epub_nav_targets.py`：把 EPUB3 `nav.xhtml` 中没有 `href` 的父级目录项指向首个子目录页面，并验证 OPF、NCX、封面、元数据、manifest、spine 不变。
- `dist/斯坦福哲学百科全书（中文版） - The Metaphysics Research Lab, Department of Philosophy, Stanford University.epub`：当前本地 EPUB 成品；不直接进入 Git 历史，发布时作为 GitHub Release 附件上传。
- `reports/epub/`：发布清单、资源清单、孤儿页面清单、人工规范化差异与 EPUB 审计报告。
- `source/SEP-CN`：指向上游资料源的软链接，不是正文副本。

## 环境要求

- Python 3.10+
- Pandoc
- Python 包：`lxml`

当前构建工具不强依赖 Java/epubcheck；内置审计会检查 EPUB 打包、OPF manifest、spine、XHTML/XML、图片引用、内部链接与锚点。

## 准备资料源

```bash
git clone https://github.com/Rivensa/SEP-CN .source/SEP-CN
```

也可以把 `--root` 指向任意已经存在的 SEP-CN 本地目录。

## 重新构建

```bash
python3 tools/build_sep_epub.py \
  --root .source/SEP-CN \
  --build-dir build/epub \
  --dist-dir dist \
  --jobs 8 \
  --timeout 60 \
  --retries 3 \
  --keep-work
```

输出：

```text
dist/斯坦福哲学百科全书（中文版） - The Metaphysics Research Lab, Department of Philosophy, Stanford University.epub
build/epub/reports/epub-audit.json
build/epub/reports/resource-manifest.json
build/epub/reports/orphan-pages.json
```

公开仓库内的当前产物发布清单为：

```text
reports/epub/release-manifest.json
```

## 只扫描资源

```bash
python3 tools/build_sep_epub.py --root .source/SEP-CN --scan-only
```

扫描报告输出到：

```text
build/epub/reports/resource-scan.json
```

`--scan-only` 不会覆盖正式构建后的 `resource-manifest.json`。

## EPUB 元数据规则

- `dc:title`：斯坦福哲学百科全书（中文版）
- 标题页展示标题：斯坦福哲学百科全书简体中文版
- `dc:creator`：The Metaphysics Research Lab, Department of Philosophy, Stanford University
- `dc:publisher`：The Metaphysics Research Lab, Department of Philosophy, Stanford University
- `dc:rights`：The Stanford Encyclopedia of Philosophy is copyright © 2026 by The Metaphysics Research Lab, Department of Philosophy, Stanford University.
- `dc:identifier`：必须写入 `issn:1095-5054` 与构建生成的 `bookid`；`calibre:*`、随机 `uuid:*` 和 `dcterms:modified` 属于工具刷新痕迹，不作为固定常量。
- `dc:source`：Library of Congress Catalog Data: ISSN 1095-5054
- `dc:description`：说明该 EPUB 基于 SEP-CN 整理，面向哲学学习、研究与检索阅读，并记录来源、版权、ISSN 与 TradeCatLabs 工程审计职责。
- `dc:subject`：至少包含“哲学、百科全书、Stanford Encyclopedia of Philosophy、SEP-CN、中文、简体中文”。
- `schema:*` accessibility 元数据：构建器写入 accessMode、accessModeSufficient、accessibilityFeature、accessibilityHazard 与 accessibilitySummary。
- `nav.xhtml`：必须包含 `toc` 与 `landmarks`，目录项不得保留无目标 `span`。
- 图片替代文本：构建器会为缺失 `alt` 的图片补入通用替代文本，审计报告中 `missing_alt_count` 必须为 0。
- EPUB 标题页正文提示固定为两行：第一行声明 `TradeCatLabs` 的 EPUB 工程整理、资源锁定与发布审计职责；第二行显示工程仓库 `tradecatlabs/SEP-editing-cn` 与 X `@123olp`；不得新增单独 PI 行，不得通过新增 spine/nav 页面实现。

## 保持元数据/封面/目录不变地补充 TradeCatLabs 信息

```bash
python3 tools/patch_epub_tradecatlabs_notice.py \
  input.epub \
  output.epub \
  --report reports/epub/tradecatlabs-notice-report.json
```

该工具的通过条件是：`content.opf`、`nav.xhtml`、`toc.ncx`、封面条目、元数据、manifest 数量、spine 数量、目录链接数量全部保持不变，只允许 `OPS/text/title.xhtml` 内容变化。

## 修复 EPUB3 nav 父级目录无目标项

```bash
python3 tools/patch_epub_nav_targets.py \
  input.epub \
  output.epub \
  --report reports/epub/nav-targets-report.json
```

该工具只允许修改 `OPS/nav.xhtml`：把 `Table of contents`、字母分组等父级目录项从无目标 `span` 转为指向首个子项的 `a href`。通过条件是 OPF、NCX、封面、元数据、manifest 数量、spine 数量、XHTML 数量全部不变，且 `nav.xhtml` 内部链接坏目标为 0。

## 当前成品审计摘要

- EPUB XML 错误：0
- 缺失图片：0
- 内部坏链：0
- EPUB3 nav 无目标目录项：0
- 资源下载/锁定错误：0
- 资源总数：1095
- 源站失效但已占位保底图片：28
- 源站失效但通过回退匹配恢复图片：23

## 发布注意

- `dist/` 中的 EPUB 超过 GitHub 普通 Git 单文件 100MB 限制，默认只作为 GitHub Release 附件发布。
- `build/` 是本地中间构建目录，不建议提交。
- `reports/epub/` 是可追溯审计证据，建议随发布产物保留。
