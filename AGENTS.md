# SEP-editing-cn 项目结构说明

## 架构定位

SEP-editing-cn 是 SEP-CN Markdown 内容到标准 EPUB 的构建与发布仓库。它不内嵌 SEP-CN 正文源仓库，只通过 `source/SEP-CN` 与 `SOURCE.md` 指向上游资料源：<https://github.com/Rivensa/SEP-CN>。

## 目录结构

```text
.
├── README.md                         # 公开仓库入口说明
├── CODE_OF_CONDUCT.md                # 协作行为准则
├── CONTRIBUTING.md                   # 贡献指南、问题反馈边界与 PR 要求
├── LICENSE                           # TradeCatLabs 新增代码与文档许可证
├── NOTICE.md                         # SEP/SEP-CN/Release EPUB 版权边界说明
├── README-EPUB.md                    # EPUB 构建、扫描、审计与发布说明
├── RELEASE.md                        # Release 附件发布与校验流程
├── SECURITY.md                       # 安全与供应链问题报告规则
├── SOURCE.md                         # 上游资料源与许可证边界说明
├── SUPPLY_CHAIN.md                   # 资源供应链、上下游与发布边界
├── TRADECATLABS.md                   # TradeCatLabs 实验室信息与项目职责
├── requirements.txt                  # Python 构建依赖
├── .github/                          # Issue 模板、PR 模板与 GitHub Actions
├── docs/LESSONS.md                   # EPUB 事故复盘、长期门禁与执行清单
├── docs/README_PATTERNS.md           # README 调研、同类项目模式与目录结构沉淀
├── docs/SOURCE_GAPS.md               # 用户提供的待补充资料缺口备忘
├── source/README.md                  # 资料源指针目录说明
├── source/SEP-CN                     # 指向 ../.source/SEP-CN 的软链接，不是正文副本
├── tools/build_sep_epub.py           # 标准 EPUB 构建、资源锁定与审计工具
├── tools/check_repo_health.py        # 本地仓库结构、报告一致性与发布引用检查
├── tools/check_release_assets.py     # GitHub Release 附件与 SHA256 一致性检查
├── tools/patch_epub_nav_targets.py   # 修复 nav.xhtml 父级目录无目标项并守住结构不变量
├── tools/patch_epub_tradecatlabs_notice.py # 保持元数据、封面和目录不变的标题页补丁工具
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
- TradeCatLabs 正文说明只能通过 `tools/patch_epub_tradecatlabs_notice.py` 写入既有标题页，不得新增 spine/nav 页面，不得改动 OPF 元数据、封面、manifest、spine、nav 或 NCX。
- EPUB3 nav 父级目录项不得使用无目标 `span` 作为最终发布形态；分组节点必须指向首个子页面，既有成品用 `tools/patch_epub_nav_targets.py` 最小修复。
- TradeCatLabs 展示信息集中维护在 `TRADECATLABS.md`，供应链声明集中维护在 `SUPPLY_CHAIN.md`。
- EPUB 目录、元数据、封面、打包和发布事故经验集中维护在 `docs/LESSONS.md`。
- README 调研依据与目录结构模式集中维护在 `docs/README_PATTERNS.md`。
- 贡献边界和 Issue/PR 入口分别维护在 `CONTRIBUTING.md` 与 `.github/`。
- 仓库健康检查入口是 `tools/check_repo_health.py`，GitHub Actions 必须至少执行该检查。
- Release 附件上传后必须用 `tools/check_release_assets.py --verify-epub` 验证远端 EPUB 与本地发布清单一致。
- `LICENSE` 不覆盖 SEP 正文、SEP-CN 上游资料和 Release EPUB 内部正文；相关边界必须同步维护在 `NOTICE.md`、`SOURCE.md` 和 `SUPPLY_CHAIN.md`。

## 维护规则

- 修改 `tools/*.py` 后必须运行 `python3 -m py_compile tools/build_sep_epub.py tools/patch_epub_tradecatlabs_notice.py tools/patch_epub_nav_targets.py tools/check_repo_health.py tools/check_release_assets.py`。
- 修改仓库结构、发布报告或 Release 引用后必须运行 `python3 tools/check_repo_health.py`。
- 重新发布 EPUB 前必须用真实 SEP-CN 克隆目录运行完整构建。
- 发布前必须确认 `epub-audit.json` 中 XML 错误、缺失图片、内部坏链、资源错误均为 0。
- 发布后必须确认 GitHub Release 附件包含 EPUB、`release-manifest.json`、`epub-audit.json`、`completion-report.json`、`user-style-diff-report.json`、`resource-manifest.json`、`resource-scan.json`、`orphan-pages.json`、`tradecatlabs-notice-report.json` 和 `nav-targets-report.json`。
- 不要把上游 SEP-CN 正文目录复制进本仓库；需要内容源时克隆到 `.source/SEP-CN` 或使用外部路径并通过 `--root` 指定。
