#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_ROOT_FILES = [
    "README.md",
    "README-EPUB.md",
    "RELEASE.md",
    "SOURCE.md",
    "SUPPLY_CHAIN.md",
    "TRADECATLABS.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "NOTICE.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    "requirements.txt",
]

REQUIRED_GITHUB_FILES = [
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/dependabot.yml",
    ".github/ISSUE_TEMPLATE/build-problem.yml",
    ".github/ISSUE_TEMPLATE/epub-rendering.yml",
    ".github/ISSUE_TEMPLATE/metadata-resource.yml",
    ".github/workflows/ci.yml",
    ".github/workflows/release-verify.yml",
]

REPORT_FILES = [
    "reports/epub/release-manifest.json",
    "reports/epub/epub-audit.json",
    "reports/epub/completion-report.json",
    "reports/epub/resource-manifest.json",
    "reports/epub/resource-scan.json",
    "reports/epub/nav-targets-report.json",
    "reports/epub/tradecatlabs-notice-report.json",
    "reports/epub/user-style-diff-report.json",
]

EXPECTED_SOURCE_LINK_TARGET = "../.source/SEP-CN"


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_json(relative_path: str) -> dict:
    path = ROOT / relative_path
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as error:
        fail(f"{relative_path} 不是合法 JSON：{error}")


def require_file(relative_path: str) -> None:
    if not (ROOT / relative_path).is_file():
        fail(f"缺少必需文件：{relative_path}")


def run_git(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout.strip()


def check_required_files() -> None:
    for relative_path in REQUIRED_ROOT_FILES + REQUIRED_GITHUB_FILES:
        require_file(relative_path)


def check_reports() -> None:
    for relative_path in REPORT_FILES:
        load_json(relative_path)

    release_manifest = load_json("reports/epub/release-manifest.json")
    epub_audit = load_json("reports/epub/epub-audit.json")
    completion_report = load_json("reports/epub/completion-report.json")

    expected_sha256 = release_manifest.get("sha256")
    expected_size = release_manifest.get("size")
    for report_name, report_data in [
        ("epub-audit.json", epub_audit),
        ("completion-report.json", completion_report),
    ]:
        if report_data.get("sha256") != expected_sha256:
            fail(f"{report_name} 的 sha256 与 release-manifest.json 不一致")
        if report_data.get("size") != expected_size:
            fail(f"{report_name} 的 size 与 release-manifest.json 不一致")

    if not epub_audit.get("passed"):
        fail("epub-audit.json 未通过")
    if not completion_report.get("passed"):
        fail("completion-report.json 未通过")

    local_completion = release_manifest.get("local_completion", {})
    if not local_completion.get("passed"):
        fail("release-manifest.json local_completion 未通过")

    title_page = release_manifest.get("title_page", {})
    if not title_page.get("standard_two_line_notice"):
        fail("标题页不是标准两行 TradeCatLabs 说明")

    release = release_manifest.get("release", {})
    release_tag = release.get("tag")
    epub_asset_name = release.get("epub_asset_name")
    if not release_tag or not epub_asset_name:
        fail("release-manifest.json 缺少 release.tag 或 release.epub_asset_name")

    readme_text = (ROOT / "README.md").read_text(encoding="utf-8")
    release_text = (ROOT / "RELEASE.md").read_text(encoding="utf-8")
    if release_tag not in readme_text:
        fail(f"README.md 未引用当前 release tag：{release_tag}")
    if release_tag not in release_text:
        fail(f"RELEASE.md 未引用当前 release tag：{release_tag}")
    if epub_asset_name not in readme_text:
        fail(f"README.md 未引用当前 EPUB 附件名：{epub_asset_name}")


def check_git_hygiene() -> None:
    tracked_epubs = run_git("ls-files", "*.epub")
    if tracked_epubs:
        fail(f"EPUB 大文件不应进入 Git：{tracked_epubs}")

    tracked_build_files = run_git("ls-files", "build", ".source")
    if tracked_build_files:
        fail(f"本地构建目录不应进入 Git：{tracked_build_files}")


def check_source_pointer() -> None:
    source_link = ROOT / "source" / "SEP-CN"
    if not source_link.is_symlink():
        fail("source/SEP-CN 必须是软链接")
    link_target = os.readlink(source_link)
    if link_target != EXPECTED_SOURCE_LINK_TARGET:
        fail(f"source/SEP-CN 指向 {link_target}，应为 {EXPECTED_SOURCE_LINK_TARGET}")


def main() -> int:
    check_required_files()
    check_reports()
    check_git_hygiene()
    check_source_pointer()
    print("OK: 仓库结构、报告一致性和发布引用通过本地检查")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
