# README 调研与目录结构沉淀

本文件记录 `SEP-editing-cn` README 优化时参考的同类仓库模式，以及落到本项目的目录结构决策。

## 参考样本

### Standard Ebooks tools

- 链接：<https://github.com/standardebooks/tools>
- 观察：README 首屏先说明工具定位，再给安装与命令入口；仓库结构包含工具代码、测试、许可证和变更记录。
- 对本项目的启发：README 顶部必须先说明“这是 EPUB 构建/审计工具链”，而不是只介绍成品。

### Standard Ebooks Manual of Style

- 链接：<https://github.com/standardebooks/manual>
- 观察：项目把电子书制作标准、结构、语义和元数据作为长期文档资产维护。
- 对本项目的启发：供应链、元数据、发布边界必须文档化，不能只藏在脚本里。

### EbookFoundation/free-programming-books

- 链接：<https://github.com/EbookFoundation/free-programming-books>
- 观察：README 首屏使用徽章、入口链接和清晰资源分组；大型内容项目强调贡献、分享和资源分类。
- 对本项目的启发：README 首屏需要有 Release 下载、审计报告、供应链文档等直接入口。

### mdbook-epub

- 链接：<https://github.com/Michael-F-Bryan/mdbook-epub>
- 观察：README 使用“Getting Started → Configuration → Planned Features → Contributing”的结构，适合构建工具型项目。
- 对本项目的启发：构建命令、环境要求、产物路径、配置边界要明确列出。

## README 通用结构

适合本项目的 README 顺序：

1. 项目名与一句话定位。
2. 徽章与关键入口。
3. 快速下载。
4. 元数据与版权边界。
5. 当前审计状态。
6. 供应链模型。
7. 本地构建命令。
8. 仓库目录结构。
9. 实验室信息。
10. 边界声明。

## 推荐目录结构

```text
.
├── README.md                         # 首页，不承载过深细节
├── README-EPUB.md                    # 构建与审计细节
├── RELEASE.md                        # GitHub Release 发布流程
├── SOURCE.md                         # 上游来源与版权边界
├── SUPPLY_CHAIN.md                   # 供应链与上下游关系
├── TRADECATLABS.md                   # 实验室说明
├── docs/README_PATTERNS.md           # README 调研和信息架构沉淀
├── dist/README.md                    # 本地产物目录说明；EPUB 不入 Git
├── reports/epub/                     # 可追溯审计证据
├── source/SEP-CN                     # 上游资料源指针
└── tools/build_sep_epub.py           # 构建工具
```

## 本项目取舍

- `README.md` 保持短而可读，重点服务第一次访问 GitHub 的读者。
- 深层技术细节放入独立文档，避免首页膨胀。
- EPUB 文件超过 GitHub 普通 Git 单文件限制，继续通过 Release 附件发布。
- `reports/epub/` 保留机器可读证据，方便未来自动化校验。
- `source/SEP-CN` 只作为资料源指针，避免复制上游正文仓库。