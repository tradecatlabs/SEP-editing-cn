# EPUB 工程经验沉淀

- 来源：`v2026.07.02 -> v2026.07.03` 目录目标修复、元数据/封面回归修复、用户反馈与发布验证。
- 状态：已验证。
- 刷新触发器：EPUB 构建器、补丁工具、目录、元数据、封面、Release 流程发生变化时。
- 验证方式：运行脚本编译、最小 fixture、EPUB 审计、Calibre 元数据检查、远端 Release SHA 下载复验。

## 核心教训

### 1. EPUB 补丁必须守住结构不变量

正文补充、实验室说明、目录修复这类“局部变更”，不得默认重建整本 EPUB。重建会改变 OPF、manifest、spine、nav、NCX、封面和内部标识，严格阅读器会把它当成另一套结构。

正确做法：

- 先定义唯一允许变化的 ZIP entry。
- 修改前后记录 OPF、NCX、封面、元数据、manifest 数量、spine 数量、XHTML 数量。
- 任一不变量变化，直接失败，不输出“修复成功”。

### 2. 目录父节点必须有可落地目标

Calibre 目录编辑器把 EPUB3 `nav.xhtml` 中无 `href` 的父级 `<span>` 显示成 `None / 位置不存在`。即使子项存在，父级项也会被标红。

正确做法：

- 有自身页面的 TOC 节点指向自身页面。
- 无自身页面但有子页面的分组节点指向首个子页面。
- 最终发布成品里 `nav_span_count` 必须为 `0`，`nav_target_errors` 必须为 `0`。

### 3. 禁止用裸字符串替换 HTML 结构

`blockquote -> p`、`span -> a` 这类结构变更不能靠简单字符串替换。带属性、命名空间、嵌套节点、空白和序列化差异都会让正则变成隐性破坏器。

正确做法：

- 用 XML/DOM 解析节点。
- 只操作目标节点和必要属性。
- 写回后重新 parse。
- 对修改前后结构不变量做机器校验。

### 4. “能打包成 EPUB”不等于“阅读器能打开”

ZIP 可打开只是最低条件。iOS Books、Calibre、Kindle 对 OPF、nav、NCX、mimetype、manifest、spine、内部锚点和缓存标识更严格。

发布前必须检查：

- `mimetype` 是 ZIP 第一项且无压缩。
- 所有 XHTML/XML 可解析。
- manifest 文件存在。
- spine idref 都在 manifest。
- XHTML 内部链接、图片、锚点都存在。
- nav 链接目标都存在。
- 封面条目存在且 SHA 未意外变化。
- 元数据与内部 identifier 没被误改。

### 5. 元数据和封面是阅读器体验的一部分

封面、作者、出版者、日期、identifier、title sort 会影响阅读器展示和缓存命中。只为了加说明文字而改 OPF，是高风险变更。

正确做法：

- 能不改 OPF 就不改 OPF。
- 必须改 OPF 时，明确写出变更字段、原因和缓存影响。
- iOS Books 异常时，优先排查内部 identifier 和旧缓存，而不是只看文件名。

### 6. 标题页展示必须极简且固定口径

公开标题页不是项目 README，过多实验室说明会干扰阅读器首页体验。TradeCatLabs 信息只保留两行：工程职责一行，工程仓库与负责人 X 一行。

正确做法：

- OPF `dc:title` 保持“斯坦福哲学百科全书（中文版）”。
- 标题页 `h1` 使用“斯坦福哲学百科全书简体中文版”。
- 标题页只显示 `TradeCatLabs`、`tradecatlabs/SEP-editing-cn` 与 `@123olp`。
- 不再单独增加“实验室负责人”段落，不再展示 `@tradecatlabs`。

### 7. Release 必须复验远端资产

本地审计通过后仍不够。GitHub Release 上传后必须下载远端资产重新算 SHA，证明用户下载到的就是审计过的文件。

当前门禁：

- `release-manifest.json` 写入本地成品 SHA。
- Release 上传后 `gh release download` 下载 EPUB。
- 远端下载 SHA 必须等于 `release-manifest.json`。

### 8. 资料缺口不能污染当前供应链

用户提供的待补充资料清单可以沉淀，但未确认来源、版权、授权和项目归属前，不能加入 SEP EPUB 的公开 Release。

正确做法：

- 缺口表放入 `docs/SOURCE_GAPS.md` 作为备忘。
- 不复制来源不明的正文实体。
- 不把其他项目资料混入 SEP 供应链。

## 固定执行清单

每次处理 EPUB 成品前：

- [ ] 明确本次允许变化的 ZIP entry。
- [ ] 备份或保留输入 SHA。
- [ ] 确认是否需要重建；能补丁就不重建。
- [ ] 对 HTML/XHTML 结构修改使用 DOM/XML 操作。
- [ ] 修改后检查 `mimetype`、OPF、manifest、spine、nav、NCX、封面、元数据。
- [ ] 检查 `nav_span_count=0`、`nav_target_errors=0`。
- [ ] 用 Calibre 工具检查元数据。
- [ ] Release 上传后下载远端资产复验 SHA。

## 当前已落地资产

- `tools/patch_epub_tradecatlabs_notice.py`：只改标题页，不改 OPF/nav/NCX/封面。
- `tools/patch_epub_nav_targets.py`：只改 `OPS/nav.xhtml`，修复父级目录无目标项。
- `reports/epub/DEBUG.md`：两次事故的根因、实验和回归证据。
- `reports/epub/nav-targets-report.json`：目录目标修复的机器可读证据。
- `reports/epub/epub-audit.json`：最终 EPUB 审计门禁。
- `reports/epub/release-manifest.json`：Release 资产 SHA 与元信息。
