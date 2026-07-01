#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_ASSETS = [
    "release-manifest.json",
    "epub-audit.json",
    "completion-report.json",
    "user-style-diff-report.json",
    "resource-manifest.json",
    "resource-scan.json",
    "orphan-pages.json",
    "tradecatlabs-notice-report.json",
    "nav-targets-report.json",
]


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def request_json(url: str, token: str | None, timeout: int) -> dict:
    request = Request(url, headers=build_headers(token))
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        fail(f"GitHub API 请求失败 {error.code}: {url}")
    except URLError as error:
        fail(f"网络请求失败：{error}")


def request_bytes(url: str, token: str | None, timeout: int) -> bytes:
    request = Request(url, headers=build_headers(token))
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read()
    except HTTPError as error:
        fail(f"下载失败 {error.code}: {url}")
    except URLError as error:
        fail(f"下载失败：{error}")


def build_headers(token: str | None) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "SEP-editing-cn-release-checker/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def download_sha256(url: str, token: str | None, timeout: int) -> tuple[str, int]:
    request = Request(url, headers=build_headers(token))
    digest = hashlib.sha256()
    total_size = 0
    try:
        with urlopen(request, timeout=timeout) as response:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
                total_size += len(chunk)
    except HTTPError as error:
        fail(f"EPUB 下载失败 {error.code}: {url}")
    except URLError as error:
        fail(f"EPUB 下载失败：{error}")
    return digest.hexdigest(), total_size


def load_expected_manifest(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as error:
        fail(f"无法读取本地发布清单 {path}: {error}")


def asset_map(release_data: dict) -> dict[str, dict]:
    return {asset["name"]: asset for asset in release_data.get("assets", [])}


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 GitHub Release 附件与本地发布清单一致性")
    parser.add_argument("--repo", default="tradecatlabs/SEP-editing-cn", help="owner/repo")
    parser.add_argument("--tag", default=None, help="Release tag；默认读取本地 release-manifest.json")
    parser.add_argument("--expected", default="reports/epub/release-manifest.json", help="本地发布清单路径")
    parser.add_argument("--verify-epub", action="store_true", help="下载 EPUB 并校验 SHA256 与 size")
    parser.add_argument("--timeout", type=int, default=120, help="网络超时秒数")
    arguments = parser.parse_args()

    expected_manifest = load_expected_manifest(Path(arguments.expected))
    expected_release = expected_manifest.get("release", {})
    release_tag = arguments.tag or expected_release.get("tag")
    if not release_tag:
        fail("缺少 release tag")

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    release_url = f"https://api.github.com/repos/{arguments.repo}/releases/tags/{release_tag}"
    release_data = request_json(release_url, token, arguments.timeout)
    assets = asset_map(release_data)

    epub_asset_name = expected_release.get("epub_asset_name")
    required_assets = [epub_asset_name, *DEFAULT_ASSETS]
    missing_assets = [asset_name for asset_name in required_assets if asset_name and asset_name not in assets]
    if missing_assets:
        fail(f"Release 缺少附件：{', '.join(missing_assets)}")

    remote_manifest_asset = assets["release-manifest.json"]
    remote_manifest = json.loads(
        request_bytes(remote_manifest_asset["browser_download_url"], token, arguments.timeout).decode("utf-8")
    )

    for key in ["sha256", "size"]:
        if remote_manifest.get(key) != expected_manifest.get(key):
            fail(f"远端 release-manifest.json 的 {key} 与本地不一致")

    remote_release = remote_manifest.get("release", {})
    if remote_release.get("tag") != release_tag:
        fail("远端 release-manifest.json 的 release.tag 与实际 tag 不一致")
    if remote_release.get("epub_asset_name") != epub_asset_name:
        fail("远端 release-manifest.json 的 EPUB 附件名与本地不一致")

    if arguments.verify_epub:
        epub_asset = assets[epub_asset_name]
        with tempfile.TemporaryDirectory(prefix="sep-release-check-") as temporary_dir:
            marker_path = Path(temporary_dir) / "download-started"
            marker_path.write_text(epub_asset_name, encoding="utf-8")
            remote_sha256, remote_size = download_sha256(
                epub_asset["browser_download_url"],
                token,
                arguments.timeout,
            )
        if remote_sha256 != expected_manifest.get("sha256"):
            fail(f"远端 EPUB SHA256 不一致：{remote_sha256}")
        if remote_size != expected_manifest.get("size"):
            fail(f"远端 EPUB size 不一致：{remote_size}")

    print(f"OK: Release {release_tag} 附件与本地发布清单一致")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
