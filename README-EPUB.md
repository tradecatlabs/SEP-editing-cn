# SEP-CN EPUB 构建与发布说明

本仓库不直接保存 SEP-CN Markdown 正文源。构建时需要通过 `--root` 指定一个本地 SEP-CN 源目录。

资料源链接：<https://github.com/Rivensa/SEP-CN>

## 已包含内容

- `tools/build_sep_epub.py`：EPUB 构建、资源锁定、打包与审计工具。
- `dist/斯坦福哲学百科全书（中文版） - The Metaphysics Research Lab, Department of Philosophy, Stanford University.epub`：当前本地 EPUB 成品；不直接进入 Git 历史，发布时作为 GitHub Release 附件上传。
- `reports/epub/`：发布清单、资源清单、孤儿页面清单与 EPUB 审计报告。
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
- `dc:creator`：The Metaphysics Research Lab, Department of Philosophy, Stanford University
- `dc:publisher`：The Metaphysics Research Lab, Department of Philosophy, Stanford University
- `dc:rights`：The Stanford Encyclopedia of Philosophy is copyright © 2026 by The Metaphysics Research Lab, Department of Philosophy, Stanford University.
- `dc:identifier`：保留构建生成的 UUID，并写入 `issn:1095-5054`
- `dc:source`：Library of Congress Catalog Data: ISSN 1095-5054

## 当前成品审计摘要

- EPUB XML 错误：0
- 缺失图片：0
- 内部坏链：0
- 资源下载/锁定错误：0
- 资源总数：1095
- 源站失效但已占位保底图片：28
- 源站失效但通过回退匹配恢复图片：23

## 发布注意

- `dist/` 中的 EPUB 超过 GitHub 普通 Git 单文件 100MB 限制，默认只作为 GitHub Release 附件发布。
- `build/` 是本地中间构建目录，不建议提交。
- `reports/epub/` 是可追溯审计证据，建议随发布产物保留。
