# 发布流程

## 为什么 EPUB 不直接提交

当前 EPUB 文件大小约 109MB，超过 GitHub 普通 Git 单文件 100MB 硬限制。

因此仓库本体只提交：

- 构建工具
- 供应链说明
- 审计报告
- 发布清单
- Release 操作说明

EPUB 成品通过 GitHub Release 附件发布。

## 当前发布文件

```text
dist/斯坦福哲学百科全书（中文版） - The Metaphysics Research Lab, Department of Philosophy, Stanford University.epub
```

发布清单：

```text
reports/epub/release-manifest.json
```

## 发布命令

确认已经切到 TradeCatLabs 账号或具备 `tradecatlabs/SEP-editing-cn` 发布权限后执行：

```bash
epub_source="$(find dist -maxdepth 1 -type f -name '*.epub' ! -name '*sample*' | head -n 1)"
epub_asset="/tmp/SEP-Chinese-The-Metaphysics-Research-Lab-Stanford-University.epub"
cp "$epub_source" "$epub_asset"

gh release create v2026.07.01 \
  "$epub_asset" \
  "reports/epub/release-manifest.json" \
  "reports/epub/epub-audit.json" \
  "reports/epub/resource-manifest.json" \
  --repo tradecatlabs/SEP-editing-cn \
  --title "SEP Chinese EPUB" \
  --notes "EPUB artifact, release manifest, resource manifest, and audit report."
```

如 Release 已存在，可改用：

```bash
epub_source="$(find dist -maxdepth 1 -type f -name '*.epub' ! -name '*sample*' | head -n 1)"
epub_asset="/tmp/SEP-Chinese-The-Metaphysics-Research-Lab-Stanford-University.epub"
cp "$epub_source" "$epub_asset"

gh release upload v2026.07.01 \
  "$epub_asset" \
  "reports/epub/release-manifest.json" \
  "reports/epub/epub-audit.json" \
  "reports/epub/resource-manifest.json" \
  --repo tradecatlabs/SEP-editing-cn \
  --clobber
```

## 校验

发布后对照 `reports/epub/release-manifest.json` 中的 `sha256` 校验下载文件。
