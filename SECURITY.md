# 安全政策

## 支持范围

本仓库接受以下安全与供应链问题报告：

- 构建脚本中的路径穿越、压缩包处理、下载资源校验或命令执行风险。
- Release 附件、发布清单、SHA256、审计报告之间的不一致。
- EPUB 包结构导致严格阅读器崩溃或错误解析的问题。
- 文档误导导致用户错误信任版权、来源或发布产物的问题。

正文翻译、百科条目内容和上游 Markdown 资料源问题请优先反馈到 `Rivensa/SEP-CN`。

## 报告方式

- 非敏感问题：直接提交 GitHub Issue，并附复现步骤、文件名、Release 版本和校验信息。
- 敏感问题：不要在公开 Issue 中粘贴令牌、私有路径或未公开样本；请先通过 GitHub 账号资料页联系 TradeCatLabs 维护者，再提供最小复现材料。

## 处理原则

- 先确认可复现证据，再修复根因。
- 涉及 Release 产物时，必须重新生成或重新上传附件，并用 `tools/check_release_assets.py --verify-epub` 复核。
- 涉及构建脚本时，必须运行本地 CI 同等验证：`python3 -m py_compile tools/*.py` 与 `python3 tools/check_repo_health.py`。
