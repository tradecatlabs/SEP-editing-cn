# SEP-editing-cn 项目结构说明

## 架构定位

SEP-editing-cn 是 SEP-CN Markdown 内容到标准 EPUB 的构建与发布仓库。它不内嵌 SEP-CN 正文源仓库，只通过 `source/SEP-CN` 与 `SOURCE.md` 指向上游资料源：<https://github.com/Rivensa/SEP-CN>。

## 目录结构

```text
.
├── README.md                         # 公开仓库入口说明
├── CONTRIBUTING.md                   # 贡献指南、问题反馈边界与 PR 要求
├── README-EPUB.md                    # EPUB 构建、扫描、审计与发布说明
├── SOURCE.md                         # 上游资料源与许可证边界说明
├── SUPPLY_CHAIN.md                   # 资源供应链、上下游与发布边界
├── TRADECATLABS.md                   # TradeCatLabs 实验室信息与项目职责
├── .github/                          # Issue 模板与 PR 模板
├── docs/README_PATTERNS.md           # README 调研、同类项目模式与目录结构沉淀
├── source/SEP-CN                     # 指向上游资料源的软链接，不是正文副本
├── tools/build_sep_epub.py           # 标准 EPUB 构建、资源锁定与审计工具
├── reports/epub/                     # 已发布产物对应的发布清单与审计证据
├── build/epub/                       # 本地构建中间产物，不提交
└── dist/                             # 本地 EPUB 产物目录；EPUB 文件不直接提交
```

## EPUB 构建边界

- 构建器通过 `--root` 读取外部 SEP-CN 本地克隆目录，不从本仓库读取正文源。
- 图片资源必须在构建期复制、下载、回退匹配或占位保底，最终 EPUB 不允许出现缺失图片引用。
- `reports/epub/resource-manifest.json` 是随发布产物保留的资源完整性证据。
- `reports/epub/epub-audit.json` 是随发布产物保留的最终 EPUB 门禁证据。
- `build/` 与 `.source/` 是本地工作目录，不作为公开仓库提交对象。
- `dist/*.epub` 超过 GitHub 普通 Git 单文件限制，默认通过 GitHub Release 附件发布，不直接提交到 Git 历史。
- EPUB 标题元数据必须使用 `斯坦福哲学百科全书（中文版）`。
- EPUB 作者/创建者元数据必须使用 `The Metaphysics Research Lab, Department of Philosophy, Stanford University`，并保留 `ISSN 1095-5054`。
- EPUB 正文前置页必须包含 `工程整理说明`，用于声明 TradeCatLabs 的工程整理、资源锁定、审计与发布职责。
- TradeCatLabs 展示信息集中维护在 `TRADECATLABS.md`，供应链声明集中维护在 `SUPPLY_CHAIN.md`。
- README 调研依据与目录结构模式集中维护在 `docs/README_PATTERNS.md`。
- 贡献边界和 Issue/PR 入口分别维护在 `CONTRIBUTING.md` 与 `.github/`。

## 维护规则

- 修改 `tools/build_sep_epub.py` 后必须运行 `python3 -m py_compile tools/build_sep_epub.py`。
- 重新发布 EPUB 前必须用真实 SEP-CN 克隆目录运行完整构建。
- 发布前必须确认 `epub-audit.json` 中 XML 错误、缺失图片、内部坏链、资源错误均为 0。
- 不要把上游 SEP-CN 正文目录复制进本仓库；需要内容源时克隆到 `.source/SEP-CN` 或使用外部路径并通过 `--root` 指定。
