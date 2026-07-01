# 贡献指南

感谢关注 `SEP-editing-cn`。本仓库聚焦 EPUB 工程化整理、资源完整性、构建可复现性和发布审计，不接管上游 SEP-CN 正文维护。

## 适合提交到本仓库的问题

- EPUB 在 iOS Books、Kindle、Calibre、Readest 等阅读器中打开异常。
- 目录、内部链接、脚注、图片、公式、代码块、封面或元数据问题。
- 构建工具 `tools/build_sep_epub.py` 的 bug、性能问题或可维护性改进。
- `reports/epub/` 审计证据与实际 EPUB 不一致。
- README、供应链、Release 流程和 TradeCatLabs 展示说明改进。

## 不适合提交到本仓库的问题

- SEP-CN 正文翻译、词条内容、术语选择和 Markdown 原文维护。
- Stanford Encyclopedia of Philosophy 原始内容版权与授权问题。
- 直接把上游 SEP-CN 正文目录复制进本仓库。

正文源问题请优先前往上游资料源：<https://github.com/Rivensa/SEP-CN>。

## 本地构建

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

快速检查工具语法：

```bash
python3 -m py_compile tools/build_sep_epub.py
```

完整本地仓库健康检查：

```bash
python3 -m pip install -r requirements.txt
python3 -m py_compile tools/build_sep_epub.py tools/patch_epub_tradecatlabs_notice.py tools/patch_epub_nav_targets.py tools/check_repo_health.py tools/check_release_assets.py
python3 tools/check_repo_health.py
```

只扫描目录和资源：

```bash
python3 tools/build_sep_epub.py --root .source/SEP-CN --scan-only
```

## Pull Request 要求

- 保持改动范围小而清晰。
- 不提交 `dist/*.epub`、`build/` 或 `.source/`。
- 修改 EPUB 构建逻辑时，说明验证命令和审计结果。
- 修改发布产物时，同步更新 `reports/epub/release-manifest.json`。
- 涉及供应链、版权边界或上游来源时，同步更新 `SOURCE.md` 和 `SUPPLY_CHAIN.md`。
- 涉及 Release 附件或发布清单时，同步运行 `tools/check_release_assets.py` 并保留校验结果。

## 报告阅读器问题时请提供

- 阅读器名称与版本。
- 平台：iOS、macOS、Windows、Android、Kindle 等。
- EPUB Release 版本。
- 出错章节或截图。
- 是否可稳定复现。

## 发布边界

EPUB 成品超过 GitHub 普通 Git 单文件 `100MB` 限制，只通过 GitHub Release 附件发布，不进入 Git 历史。
