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

---

# EPUB3 nav 父级目录无目标回归调试记录

## Bug

Calibre 目录编辑器显示 `Table of contents` 等父级目录项“指向位置：None / 此项指向的位置不存在”。这些父级项在 EPUB3 `OPS/nav.xhtml` 中是 `<span>`，不是带 `href` 的 `<a>`。

## Environment

- 本地成品：`dist/斯坦福哲学百科全书（中文版） - The Metaphysics Research Lab, Department of Philosophy, Stanford University.epub`
- 观察工具：Calibre 目录编辑器、Python `zipfile`、`xml.etree.ElementTree`
- 结构文件：`OPS/nav.xhtml`、`OPS/toc.ncx`、`OPS/content.opf`

## Reproduction

1. 解包并读取 `OPS/nav.xhtml`。
2. 统计目录内 `<span>` 与 `<a href>` 数量。
3. 对照 `OPS/toc.ncx` 中 `navPoint` 数量。

## Observations

- 修复前 `nav.xhtml` 中有 30 个无目标 `<span>`：`Table of contents`、`前言`、`关于`、`A` 到 `Z`、`补遗与未列入主目录文档`。
- 修复前 `nav.xhtml` 链接数为 `2618`，`toc.ncx` navPoint 数为 `2648`。
- Calibre 对 EPUB3 nav 中的无目标父级 `<span>` 显示为 `None`，即使其子项可以展开。
- OPF、NCX、封面、元数据、manifest、spine 本身没有损坏。

## Hypotheses

### H1 EPUB3 nav 父级 `<span>` 是目录无目标的根因

- Supports：30 个 Calibre 红色目录项与 30 个 nav `<span>` 一一对应。
- Conflicts：子目录可展开，说明不是整个 TOC 缺失。
- Test：把父级 `<span>` 指向首个子目录页面，验证红色无目标项消失。

### H2 OPF manifest/spine 缺项导致目录目标不存在

- Supports：Calibre 文案是“位置不存在”。
- Conflicts：内部目标校验为 0 个坏链，manifest/spine 计数稳定。
- Test：保持 OPF 不变，仅修改 nav。

### H3 NCX 与 nav 数量不一致导致 Calibre 报错

- Supports：修复前 nav 链接数 `2618`，NCX navPoint 数 `2648`。
- Conflicts：差值刚好等于 nav `<span>` 数量，说明不是 NCX 多出真实页面，而是 nav 父级没 href。
- Test：修复后 nav 链接数应变为 `2648`。

## ROOT HYPOTHESIS

H1 与 H3 成立：构建器把分组父节点输出为 EPUB3 nav `<span>`，但 Calibre/iOS 这类严格目录工具期望每个 TOC 节点都有可落地目标；正确做法是让分组父节点指向首个子页面。

## Experiments

### E1 最小修复既有 EPUB 的 nav.xhtml

- Hypothesis：H1
- Action：只修改 `OPS/nav.xhtml`，把父级目录 `<span>` 转为指向首个子项的 `<a href>`。
- Expected：`nav_span_count` 从 30 变为 0，OPF、NCX、封面、元数据和 spine 不变。
- Result：通过；`nav_span_count: 30 -> 0`，`nav_link_count: 2618 -> 2648`。

### E2 验证结构不变量

- Hypothesis：H2
- Action：对比修复前后 OPF、NCX、封面、元数据、manifest 数量、spine 数量和 XHTML 数量。
- Expected：除 `OPS/nav.xhtml` 外结构不变量不变，内部链接坏目标为 0。
- Result：通过；`nav_target_errors=[]`，OPF/NCX/封面 SHA 均保持不变。

## Root Cause

根因是构建器对有子项但没有自身页面的 TOC 分组节点输出无目标 `<span>`，导致严格目录编辑器把这些父级项显示为不存在的位置。

## Fix

- 更新 `tools/build_sep_epub.py`：无自身页面但有子页面的 TOC 节点，输出指向首个子页面的 `<a href>`。
- 新增 `tools/patch_epub_nav_targets.py`：用 XML/DOM 结构化方式修复既有成品 `OPS/nav.xhtml`，并守住 OPF、NCX、封面、元数据、manifest、spine 不变量。
- 更新 README、构建说明、发布流程和 AGENTS 规则，把“EPUB3 nav 父级节点必须有目标”写成长期门禁。

## Regression Evidence

- 修复报告：`reports/epub/nav-targets-report.json`
- 修复后成品 SHA256：`f1963040793a24295034d68b0479d92a5cf3dae2d45f13505e60bc26d9a13e80`
- 验证结果：`nav_span_count=0`、`nav_link_count=2648`、`nav_target_errors=[]`、OPF/NCX/封面/元数据保持不变。
- 回归样本：最小 EPUB fixture 中父级目录 `span -> a href` 后，`nav_span_count: 1 -> 0`、`nav_link_count: 1 -> 2`，结构不变量保持。
