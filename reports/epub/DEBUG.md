# SEP EPUB 元数据、封面与目录回归调试记录

## Bug

向 EPUB 正文加入 TradeCatLabs 信息后，使用重建方式生成的 EPUB 与旧发布基准相比改变了阅读器关键结构：缺少旧版 Calibre 元数据细节和封面条目，并通过新增 `about-tradecatlabs.xhtml` 改动了 spine、nav 与 NCX。

## Environment

- 本地目标：`C:\Users\13208\Desktop\斯坦福哲学百科全书（中文版） - The Metaphysics Research Lab, Department of Philosophy, Stanford University.epub`
- 旧版基准：`D:\iCloudDrive\下载\斯坦福哲学百科全书（中文版） - The Metaphysics Research Lab, Department of Philosophy, Stanford University.epub`
- 回归版本：`\\wsl.localhost\Ubuntu\home\lenovo\.projects\SEP-editing-cn\dist\斯坦福哲学百科全书（中文版） - The Metaphysics Research Lab, Department of Philosophy, Stanford University.epub`
- 工具：Python `zipfile`、Calibre `ebook-meta`

## Reproduction

1. 对比桌面 EPUB、iCloud 旧版 EPUB、repo/dist 重建 EPUB 的 OPF、nav、NCX、spine、封面条目和元数据。
2. 结果显示桌面 EPUB 与 iCloud 旧版主体一致，仅多出 `META-INF/calibre_bookmarks.txt`。
3. repo/dist 重建 EPUB 多出 `OPS/text/about-tradecatlabs.xhtml`，spine 数量由 `2618` 变为 `2619`，XHTML 数量由 `2619` 变为 `2620`，并缺少旧版封面条目。

## Observations

- 旧版/桌面 EPUB 的 `content.opf` 保留 `dc:date`、多个 `dc:identifier`、Calibre title sort 与 creator refine 元数据。
- 旧版/桌面 EPUB 的 manifest 中存在 `cover` 条目，封面文件 SHA256 为 `43d48aeb40ca06f3bb0b71c205044def57ed81b648de5e8740a3ded157ecb677`。
- 重建 EPUB 只保留构建脚本生成的最小 OPF 元数据，且没有旧版封面条目。
- 新增独立 TradeCatLabs 页面会改变 spine、nav、NCX，严格阅读器会把它识别为目录结构变化。

## Hypotheses

### H1 重建 EPUB 是元数据和封面回归的根因

- Supports：repo/dist 重建 EPUB 的 OPF 元数据少于旧版，封面条目为空。
- Conflicts：正文内容大体可读，说明不是 ZIP 打包失败。
- Test：比较旧版和重建版本的 OPF、manifest、spine、cover 条目。

### H2 新增独立正文页是目录变化的根因

- Supports：重建版本新增 `about-tradecatlabs.xhtml`，nav/NCX/spine 计数均增加。
- Conflicts：未发现 nav/NCX XML 解析错误。
- Test：只改既有 `title.xhtml`，验证 nav/NCX/spine 哈希不变。

### H3 桌面 EPUB 本体并非损坏源

- Supports：桌面 EPUB 与 iCloud 旧版只有 `META-INF/calibre_bookmarks.txt` 差异，OPF、nav、NCX、封面内容哈希一致。
- Conflicts：桌面 EPUB 文件大小多 300 字节。
- Test：逐条比较 ZIP entry 内容哈希。

## ROOT HYPOTHESIS

H1 与 H2 共同成立：错误路径是“重建整个 EPUB 并新增 spine/nav 页面”；正确路径应是“基于旧版成品做最小补丁，只修改 `OPS/text/title.xhtml`”。

## Experiments

### E1 对桌面 EPUB 执行最小补丁

- Hypothesis：H2
- Action：只向 `OPS/text/title.xhtml` 的 titlepage section 插入 TradeCatLabs 提示。
- Expected：元数据、OPF、nav、NCX、封面、manifest/spine 数量全部不变。
- Result：通过；唯一变化 entry 为 `OPS/text/title.xhtml`。

### E2 验证阅读器关键结构不变

- Hypothesis：H1、H2
- Action：比较补丁前后 `content.opf`、`nav.xhtml`、`toc.ncx`、封面条目、目录计数与 ZIP CRC。
- Expected：所有结构不变量保持一致。
- Result：通过；`zip_bad_crc=null`，`opf_sha256/nav_sha256/ncx_sha256/cover_items` 均保持不变。

## Root Cause

根因是把“补充实验室说明”错误实现成完整 EPUB 重建和新增目录页，导致阅读器可见的 OPF 元数据、封面条目、spine、nav 与 NCX 相对旧版发生变化。

## Fix

- 新增 `tools/patch_epub_tradecatlabs_notice.py`：只修改既有标题页 `OPS/text/title.xhtml`。
- 回退 `tools/build_sep_epub.py` 中新增独立 about 页、spine、nav、NCX、manifest 的逻辑。
- 更新文档和 AGENTS 规则：TradeCatLabs 正文说明不得通过新增 spine/nav 页面实现。

## Regression Evidence

- 桌面 EPUB 修复报告：`C:\Users\13208\Desktop\SEP-EPUB-tradecatlabs-fix-report.json`
- 验证结果：补丁后仅 `OPS/text/title.xhtml` 内容哈希变化；OPF/nav/NCX/封面/元数据/目录数量均不变。
