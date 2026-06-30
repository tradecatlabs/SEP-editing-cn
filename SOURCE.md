# 资料源说明

SEP-CN 正文资料源：<https://github.com/Rivensa/SEP-CN>

本仓库不复制上游 Markdown 正文、目录树、图片源目录和贡献历史，只保留构建工具、发布产物与审计报告。

## 本地构建方式

```bash
git clone https://github.com/Rivensa/SEP-CN .source/SEP-CN
python3 tools/build_sep_epub.py --root .source/SEP-CN --jobs 8 --timeout 60 --retries 3 --keep-work
```

`source/SEP-CN` 是公开仓库中的资料源指针；真正构建时请使用 `.source/SEP-CN` 或任意本地 SEP-CN 克隆目录作为 `--root`。

## EPUB 元数据来源

- The Stanford Encyclopedia of Philosophy is copyright © 2026 by The Metaphysics Research Lab, Department of Philosophy, Stanford University.
- Library of Congress Catalog Data: ISSN 1095-5054

## 版权与来源边界

- SEP 正文版权与目录识别信息归 The Metaphysics Research Lab, Department of Philosophy, Stanford University。
- SEP-CN Markdown 中文资料源、原始提交历史与原始许可证请以上游仓库为准。
- 本仓库的新增内容集中在 EPUB 构建工具、格式整理、资源锁定、审计报告和发布说明。
- TradeCatLabs 不声明拥有 SEP 正文版权；本仓库只提供面向 EPUB 阅读场景的整理、构建与审计链路。
