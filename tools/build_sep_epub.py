#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import hashlib
import html
import json
import mimetypes
import os
import posixpath
import re
import shutil
import subprocess
import sys
import time
import uuid
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote, urlparse
from urllib.parse import urljoin
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from lxml import etree
from lxml import html as lxml_html


PROJECT_TITLE = "斯坦福哲学百科全书（中文版）"
PROJECT_DISPLAY_TITLE = "斯坦福哲学百科全书简体中文版"
PROJECT_CREATOR = "The Metaphysics Research Lab, Department of Philosophy, Stanford University"
PROJECT_PUBLISHER = "The Metaphysics Research Lab, Department of Philosophy, Stanford University"
PROJECT_RIGHTS = (
    "The Stanford Encyclopedia of Philosophy is copyright © 2026 by "
    "The Metaphysics Research Lab, Department of Philosophy, Stanford University."
)
PROJECT_ISSN = "1095-5054"
PROJECT_SOURCE = "Library of Congress Catalog Data: ISSN 1095-5054"
PROJECT_DATE = "2026-06-30T16:00:00+00:00"
PROJECT_DESCRIPTION = (
    "《斯坦福哲学百科全书（中文版）》是基于 SEP-CN 项目内容整理的离线 EPUB，"
    "面向哲学学习、研究与检索阅读；本版本保留 Stanford Encyclopedia of Philosophy "
    "的来源、版权与 ISSN 元信息，并由 TradeCatLabs 进行 EPUB 工程整理、资源锁定与发布审计。"
)
PROJECT_SUBJECTS = [
    "哲学",
    "百科全书",
    "Stanford Encyclopedia of Philosophy",
    "SEP-CN",
    "中文",
    "简体中文",
]
ACCESSIBILITY_METADATA = [
    ("schema:accessMode", "textual"),
    ("schema:accessMode", "visual"),
    ("schema:accessModeSufficient", "textual"),
    ("schema:accessibilityFeature", "tableOfContents"),
    ("schema:accessibilityFeature", "readingOrder"),
    ("schema:accessibilityFeature", "structuralNavigation"),
    ("schema:accessibilityFeature", "alternativeText"),
    ("schema:accessibilityFeature", "displayTransformability"),
    ("schema:accessibilityHazard", "none"),
    (
        "schema:accessibilitySummary",
        "本 EPUB 为可重排文本，提供目录、结构化阅读顺序和图片替代文本；"
        "少量原始资料中缺失替代文本的图像已补充通用替代文本，后续可由人工校订为更精确描述；"
        "未进行第三方无障碍认证。",
    ),
]
PROJECT_OUTPUT_NAME = f"{PROJECT_TITLE} - {PROJECT_CREATOR}.epub"
LANGUAGE = "zh-CN"
USER_AGENT = "SEP-CN-EPUB-Builder/1.0"

ROOT_META_MD = {
    "AGENTS.md",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
}

EPUB_MEDIA_TYPES = {
    ".css": "text/css",
    ".gif": "image/gif",
    ".html": "application/xhtml+xml",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".ncx": "application/x-dtbncx+xml",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".xhtml": "application/xhtml+xml",
}

MARKDOWN_LINK_RE = re.compile(
    r"(?P<bang>!?)\[(?P<label>(?:\\.|[^\]\\])*)\]\((?P<href><[^>]+>|[^)\s]+)(?P<title>\s+\"[^\"]*\")?\)"
)
HTML_IMG_RE = re.compile(
    r"(<img\b[^>]*\bsrc=[\"'])(?P<src>[^\"']+)([\"'][^>]*>)",
    re.IGNORECASE,
)
HTML_A_RE = re.compile(
    r"(<a\b[^>]*\bhref=[\"'])(?P<href>[^\"']+)([\"'][^>]*>)",
    re.IGNORECASE,
)
SUMMARY_LINK_RE = re.compile(r"\[(?P<title>[^\]]+)\]\((?P<href>[^)]+)\)")


@dataclass
class TocNode:
    title: str
    level: int
    href: str | None = None
    source_rel: str | None = None
    children: list["TocNode"] = field(default_factory=list)
    page: "Page" | None = None


@dataclass
class Page:
    title: str
    source_path: Path
    source_rel: str
    output_href: str
    orphan: bool = False


@dataclass
class Resource:
    key: str
    original_href: str
    source_rel: str
    line: int
    kind: str
    is_remote: bool
    source_path: Path | None = None
    url: str | None = None
    resolved_url: str | None = None
    cache_path: Path | None = None
    epub_href: str | None = None
    media_type: str | None = None
    sha256: str | None = None
    size: int = 0
    status: str = "pending"
    error: str | None = None
    placeholder_reason: str | None = None
    references: list[dict] = field(default_factory=list)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="构建 SEP-CN 标准 EPUB，含资源锁定与完整性审计。")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="SEP-CN 项目根目录")
    parser.add_argument("--build-dir", type=Path, default=Path("build/epub"), help="构建目录")
    parser.add_argument("--dist-dir", type=Path, default=Path("dist"), help="输出目录")
    parser.add_argument("--output-name", default=PROJECT_OUTPUT_NAME, help="EPUB 文件名")
    parser.add_argument("--limit", type=int, default=0, help="只构建前 N 个正文页面，用于样本验证")
    parser.add_argument("--scan-only", action="store_true", help="只扫描目录与资源，不生成 EPUB")
    parser.add_argument("--jobs", type=int, default=8, help="远程资源下载并发数")
    parser.add_argument("--timeout", type=int, default=45, help="单个远程资源下载超时秒数")
    parser.add_argument("--retries", type=int, default=3, help="单个远程资源下载重试次数")
    parser.add_argument("--keep-work", action="store_true", help="保留已有工作目录，不先清理")
    return parser.parse_args()


def is_external_href(href: str) -> bool:
    return bool(re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", href))


def normalize_href(href: str) -> str:
    href = href.strip()
    if href.startswith("<") and href.endswith(">"):
        href = href[1:-1]
    return href


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def url_key(url: str) -> str:
    return "url:" + hashlib.sha256(url.encode("utf-8")).hexdigest()


def local_key(path: Path) -> str:
    return "file:" + str(path.resolve())


def safe_ext_from_href(href: str, media_type: str | None = None) -> str:
    suffix = Path(unquote(urlparse(href).path if is_external_href(href) else href).split("?", 1)[0]).suffix.lower()
    if suffix == ".jpeg":
        return ".jpg"
    if suffix in {".jpg", ".png", ".gif", ".svg", ".webp"}:
        return suffix
    if media_type:
        guessed = mimetypes.guess_extension(media_type.split(";", 1)[0].strip())
        if guessed:
            return ".jpg" if guessed == ".jpe" else guessed
    return suffix or ".bin"


def media_type_for(path_or_href: str, fallback: str | None = None) -> str:
    ext = Path(path_or_href).suffix.lower()
    if ext == ".jpeg":
        ext = ".jpg"
    if ext in EPUB_MEDIA_TYPES:
        return EPUB_MEDIA_TYPES[ext]
    guessed = mimetypes.guess_type(path_or_href)[0]
    return guessed or fallback or "application/octet-stream"


def strip_frontmatter(text: str) -> str:
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            after = end + len("\n---")
            if after < len(text) and text[after:after + 1] in {"\n", "\r"}:
                return text[after:].lstrip("\r\n")
    return text


def parse_summary(root: Path) -> tuple[list[TocNode], list[tuple[str, str, int]]]:
    summary_path = root / "SUMMARY.md"
    nodes: list[TocNode] = []
    stack: list[TocNode] = []
    links: list[tuple[str, str, int]] = []

    for line_no, line in enumerate(summary_path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if heading:
            level = len(heading.group(1))
            node = TocNode(title=heading.group(2).strip(), level=level)
            while stack and stack[-1].level >= level:
                stack.pop()
            if stack:
                stack[-1].children.append(node)
            else:
                nodes.append(node)
            stack.append(node)
            continue

        bullet = re.match(r"^(?P<indent>\s*)[-*]\s+(?P<body>.+?)\s*$", line)
        if not bullet:
            continue
        match = SUMMARY_LINK_RE.search(bullet.group("body"))
        if not match:
            continue
        href = normalize_href(match.group("href")).split("#", 1)[0]
        if not href or is_external_href(href):
            continue
        title = match.group("title").replace("\\[", "[").replace("\\]", "]").strip()
        level = 7 + len(bullet.group("indent").replace("\t", "    ")) // 2
        node = TocNode(title=title, level=level, href=href, source_rel=href)
        while stack and stack[-1].level >= level:
            stack.pop()
        if stack:
            stack[-1].children.append(node)
        else:
            nodes.append(node)
        stack.append(node)
        links.append((title, href, line_no))

    return nodes, links


def iter_toc_nodes(nodes: Iterable[TocNode]) -> Iterable[TocNode]:
    for node in nodes:
        yield node
        yield from iter_toc_nodes(node.children)


def all_markdown_files(root: Path) -> list[str]:
    excluded = {".git", "build", "dist"}
    result: list[str] = []
    for path in root.rglob("*.md"):
        rel_parts = path.relative_to(root).parts
        if any(part in excluded for part in rel_parts):
            continue
        result.append(path.relative_to(root).as_posix())
    return sorted(result)


def collect_pages(root: Path, limit: int = 0) -> tuple[list[TocNode], list[Page], list[str]]:
    toc_roots, summary_links = parse_summary(root)
    seen: set[str] = set()
    pages: list[Page] = []

    for node in iter_toc_nodes(toc_roots):
        if not node.href:
            continue
        rel = node.href
        source = (root / rel).resolve()
        if not source.exists():
            raise FileNotFoundError(f"SUMMARY 链接不存在: {rel}")
        if rel in seen:
            continue
        seen.add(rel)
        page = Page(
            title=node.title,
            source_path=source,
            source_rel=rel,
            output_href=f"text/p{len(pages) + 1:05d}.xhtml",
        )
        node.page = page
        pages.append(page)

    orphan_rels = [rel for rel in all_markdown_files(root) if rel not in seen and rel not in ROOT_META_MD]
    orphan_pages: list[Page] = []
    for rel in orphan_rels:
        source = (root / rel).resolve()
        title = first_heading(source) or rel
        orphan_pages.append(
            Page(
                title=title,
                source_path=source,
                source_rel=rel,
                output_href=f"text/p{len(pages) + len(orphan_pages) + 1:05d}.xhtml",
                orphan=True,
            )
        )

    if orphan_pages:
        orphan_root = TocNode(title="补遗与未列入主目录文档", level=2)
        toc_roots.append(orphan_root)
        for page in orphan_pages:
            node = TocNode(title=page.title, level=7, href=page.source_rel, source_rel=page.source_rel, page=page)
            orphan_root.children.append(node)
        pages.extend(orphan_pages)

    if limit > 0:
        allowed = {p.source_rel for p in pages[:limit]}
        pages = pages[:limit]
        prune_toc(toc_roots, allowed)

    return toc_roots, pages, orphan_rels


def prune_toc(nodes: list[TocNode], allowed: set[str]) -> bool:
    kept: list[TocNode] = []
    for node in nodes:
        child_has = prune_toc(node.children, allowed)
        self_has = bool(node.page and node.page.source_rel in allowed)
        if node.page and not self_has:
            node.page = None
            node.href = None
            node.source_rel = None
        if child_has or self_has or not node.href:
            kept.append(node)
    nodes[:] = kept
    return bool(kept)


def first_heading(path: Path) -> str | None:
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.match(r"^#\s+(.+?)\s*#*\s*$", line)
        if match:
            return match.group(1).strip()
    return None


def resolve_local(root: Path, source_path: Path, href: str) -> Path:
    clean = href.split("#", 1)[0].split("?", 1)[0]
    return (source_path.parent / unquote(clean)).resolve()


def scan_resources(root: Path, pages: list[Page]) -> dict[str, Resource]:
    resources: dict[str, Resource] = {}

    def add_resource(page: Page, line_no: int, href: str, kind: str) -> None:
        href = normalize_href(href)
        if not href or href.startswith(("data:", "mailto:", "#")):
            return
        if is_external_href(href):
            parsed = urlparse(href)
            if parsed.scheme not in {"http", "https"}:
                return
            key = url_key(href)
            resource = resources.get(key)
            if not resource:
                resource = Resource(
                    key=key,
                    original_href=href,
                    source_rel=page.source_rel,
                    line=line_no,
                    kind=kind,
                    is_remote=True,
                    url=href,
                )
                resources[key] = resource
        else:
            target = resolve_local(root, page.source_path, href)
            try:
                target.relative_to(root.resolve())
            except ValueError as exc:
                raise ValueError(f"资源越界: {page.source_rel}:{line_no} -> {href}") from exc
            key = local_key(target)
            resource = resources.get(key)
            if not resource:
                resource = Resource(
                    key=key,
                    original_href=href,
                    source_rel=page.source_rel,
                    line=line_no,
                    kind=kind,
                    is_remote=False,
                    source_path=target,
                )
                resources[key] = resource
        resource.references.append({"source": page.source_rel, "line": line_no, "href": href, "kind": kind})

    for page in pages:
        text = page.source_path.read_text(encoding="utf-8", errors="replace")
        for line_no, line in enumerate(text.splitlines(), 1):
            for match in MARKDOWN_LINK_RE.finditer(line):
                if match.group("bang"):
                    add_resource(page, line_no, match.group("href"), "markdown-image")
            for match in HTML_IMG_RE.finditer(line):
                add_resource(page, line_no, match.group("src"), "html-image")

    return resources


def read_remote(url: str, timeout: int, retries: int) -> tuple[bytes, str | None]:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            request = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(request, timeout=timeout) as response:
                return response.read(), response.headers.get("Content-Type")
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(min(2 * attempt, 8))
    raise RuntimeError(f"{url}: {last_error}")


def normalize_stem(value: str) -> str:
    stem = Path(urlparse(value).path).stem.lower()
    stem = re.sub(r"[^a-z0-9]+", "", stem)
    return stem


def stem_variants(stem: str) -> set[str]:
    variants = {stem}
    if stem.startswith("figure"):
        variants.add("fig" + stem[len("figure"):])
    if stem.startswith("fig"):
        variants.add("figure" + stem[len("fig"):])
    if stem.startswith("example"):
        variants.add("ex" + stem[len("example"):])
    if stem.startswith("ex"):
        variants.add("example" + stem[len("ex"):])
    variants.add(re.sub(r"^(fig|figure|example|ex)[0-9]*[a-z]*", "", stem))
    return {v for v in variants if v}


def candidate_score(original_url: str, candidate_url: str) -> int:
    original = normalize_stem(original_url)
    candidate = normalize_stem(candidate_url)
    original_variants = stem_variants(original)
    candidate_variants = stem_variants(candidate)
    if original_variants & candidate_variants:
        return 100 + max(len(v) for v in original_variants & candidate_variants)
    if candidate in original_variants or original in candidate_variants:
        return 90 + min(len(original), len(candidate))
    if candidate and candidate in original:
        return 70 + len(candidate)
    if original and original in candidate:
        return 70 + len(original)
    original_number = re.search(r"(\d+)", original)
    candidate_number = re.search(r"(\d+)", candidate)
    if original_number and candidate_number and original_number.group(1) == candidate_number.group(1):
        original_prefix = re.match(r"([a-z]+)", original)
        candidate_prefix = re.match(r"([a-z]+)", candidate)
        if original_prefix and candidate_prefix and {original_prefix.group(1), candidate_prefix.group(1)} <= {"fig", "figure", "example", "ex"}:
            return 50
    return 0


def discover_fallback_url(original_url: str, timeout: int) -> str | None:
    parsed = urlparse(original_url)
    page_url = f"{parsed.scheme}://{parsed.netloc}{posixpath.dirname(parsed.path)}/"
    try:
        data, _content_type = read_remote(page_url, timeout=timeout, retries=1)
    except Exception:
        return None
    try:
        doc = lxml_html.fromstring(data)
    except Exception:
        return None
    candidates: list[str] = []
    for element in doc.xpath("//img[@src] | //object[@data]"):
        ref = element.get("src") or element.get("data")
        if not ref:
            continue
        resolved = urljoin(page_url, ref)
        ext = Path(urlparse(resolved).path).suffix.lower()
        if ext in {".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp"}:
            candidates.append(resolved)
    scored = sorted(((candidate_score(original_url, item), item) for item in candidates), reverse=True)
    if scored and scored[0][0] >= 70:
        if len(scored) == 1 or scored[0][0] > scored[1][0]:
            return scored[0][1]
    return None


def placeholder_svg(resource: Resource, reason: str) -> bytes:
    title = "原始图片无法下载"
    detail = resource.url or resource.original_href
    source = f"{resource.source_rel}:{resource.line}"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="420" viewBox="0 0 1200 420">
  <rect width="1200" height="420" fill="#f7f7f7"/>
  <rect x="24" y="24" width="1152" height="372" fill="none" stroke="#999" stroke-width="3" stroke-dasharray="12 8"/>
  <text x="60" y="115" font-family="sans-serif" font-size="42" fill="#333">{html.escape(title)}</text>
  <text x="60" y="190" font-family="monospace" font-size="24" fill="#555">{html.escape(source)}</text>
  <text x="60" y="245" font-family="monospace" font-size="22" fill="#555">{html.escape(detail[:110])}</text>
  <text x="60" y="310" font-family="sans-serif" font-size="24" fill="#777">{html.escape(reason[:120])}</text>
</svg>
""".encode("utf-8")


def materialize_resources(
    root: Path,
    resources: dict[str, Resource],
    work_dir: Path,
    jobs: int,
    timeout: int,
    retries: int,
) -> None:
    cache_dir = work_dir / "resource-cache"
    asset_dir = work_dir / "OPS" / "assets" / "images"
    remote_url_dir = cache_dir / "remote-by-url"
    local_cache_dir = cache_dir / "local"
    for directory in [asset_dir, remote_url_dir, local_cache_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    def materialize_one(resource: Resource) -> Resource:
        try:
            if resource.is_remote:
                assert resource.url
                url_ext = safe_ext_from_href(resource.url)
                url_cache = remote_url_dir / f"{hashlib.sha256(resource.url.encode('utf-8')).hexdigest()}{url_ext}"
                if url_cache.exists() and url_cache.stat().st_size > 0:
                    data = url_cache.read_bytes()
                    content_type = media_type_for(resource.url)
                else:
                    try:
                        data, content_type = read_remote(resource.url, timeout=timeout, retries=retries)
                        resource.resolved_url = resource.url
                    except Exception as first_error:
                        fallback_url = discover_fallback_url(resource.url, timeout=timeout)
                        if fallback_url:
                            data, content_type = read_remote(fallback_url, timeout=timeout, retries=retries)
                            resource.resolved_url = fallback_url
                            url_ext = safe_ext_from_href(fallback_url, content_type)
                            url_cache = remote_url_dir / f"{hashlib.sha256(fallback_url.encode('utf-8')).hexdigest()}{url_ext}"
                        else:
                            data = placeholder_svg(resource, str(first_error))
                            content_type = "image/svg+xml"
                            resource.status = "placeholder"
                            resource.placeholder_reason = str(first_error)
                            url_ext = ".svg"
                            url_cache = remote_url_dir / f"{hashlib.sha256(resource.url.encode('utf-8')).hexdigest()}.placeholder.svg"
                    tmp = url_cache.with_suffix(url_cache.suffix + ".tmp")
                    tmp.write_bytes(data)
                    os.replace(tmp, url_cache)
                media_type = media_type_for(resource.resolved_url or resource.url, content_type)
                ext = safe_ext_from_href(resource.resolved_url or resource.url, media_type)
                resource.cache_path = url_cache
            else:
                assert resource.source_path
                if not resource.source_path.exists():
                    raise FileNotFoundError(str(resource.source_path))
                data = resource.source_path.read_bytes()
                media_type = media_type_for(resource.source_path.name)
                ext = safe_ext_from_href(resource.source_path.name, media_type)
                content_hash = hash_bytes(data)
                local_cache = local_cache_dir / f"{content_hash}{ext}"
                if not local_cache.exists():
                    tmp = local_cache.with_suffix(local_cache.suffix + ".tmp")
                    tmp.write_bytes(data)
                    os.replace(tmp, local_cache)
                resource.cache_path = local_cache

            content_hash = hash_bytes(data)
            resource.sha256 = content_hash
            resource.size = len(data)
            resource.media_type = media_type
            ext = ".jpg" if ext == ".jpeg" else ext
            resource.epub_href = f"assets/images/{content_hash[:24]}{ext}"
            out_path = asset_dir / Path(resource.epub_href).name
            if not out_path.exists():
                tmp = out_path.with_suffix(out_path.suffix + ".tmp")
                tmp.write_bytes(data)
                os.replace(tmp, out_path)
            if resource.status != "placeholder":
                resource.status = "ok"
        except Exception as exc:  # noqa: BLE001
            resource.status = "error"
            resource.error = str(exc)
        return resource

    remote = [r for r in resources.values() if r.is_remote]
    local = [r for r in resources.values() if not r.is_remote]
    for resource in local:
        materialize_one(resource)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, jobs)) as executor:
        list(executor.map(materialize_one, remote))


def page_href_map(pages: list[Page]) -> dict[str, Page]:
    return {page.source_rel: page for page in pages}


def resource_lookup(root: Path, page: Page, href: str, resources: dict[str, Resource]) -> Resource | None:
    href = normalize_href(href)
    if is_external_href(href):
        return resources.get(url_key(href))
    if href.startswith(("data:", "mailto:", "#")):
        return None
    target = resolve_local(root, page.source_path, href)
    return resources.get(local_key(target))


def relative_from_page(page: Page, target_href: str) -> str:
    return posixpath.relpath(target_href, posixpath.dirname(page.output_href))


def rewrite_links(root: Path, page: Page, pages_by_rel: dict[str, Page], resources: dict[str, Resource]) -> str:
    text = strip_frontmatter(page.source_path.read_text(encoding="utf-8", errors="replace"))

    def rewrite_markdown(match: re.Match) -> str:
        bang = match.group("bang")
        label = match.group("label")
        raw_href = normalize_href(match.group("href"))
        title = match.group("title") or ""
        anchor = ""
        href_no_anchor = raw_href
        if "#" in raw_href and not is_external_href(raw_href):
            href_no_anchor, anchor = raw_href.split("#", 1)
            anchor = "#" + anchor
        if bang:
            resource = resource_lookup(root, page, raw_href, resources)
            if resource and resource.status == "ok" and resource.epub_href:
                return f"![{label}]({relative_from_page(page, resource.epub_href)}{title})"
            return match.group(0)
        if href_no_anchor and not is_external_href(raw_href) and not raw_href.startswith(("mailto:", "#")):
            target = resolve_local(root, page.source_path, href_no_anchor)
            try:
                rel = target.relative_to(root.resolve()).as_posix()
            except ValueError:
                return match.group(0)
            target_page = pages_by_rel.get(rel)
            if target_page:
                return f"[{label}]({relative_from_page(page, target_page.output_href)}{anchor}{title})"
        return match.group(0)

    text = MARKDOWN_LINK_RE.sub(rewrite_markdown, text)

    def rewrite_html_img(match: re.Match) -> str:
        src = match.group("src")
        resource = resource_lookup(root, page, src, resources)
        if resource and resource.status == "ok" and resource.epub_href:
            return f"{match.group(1)}{relative_from_page(page, resource.epub_href)}{match.group(3)}"
        return match.group(0)

    return HTML_IMG_RE.sub(rewrite_html_img, text)


def pandoc_fragment(markdown_text: str, root: Path) -> str:
    command = [
        "pandoc",
        "--from",
        "gfm+footnotes+pipe_tables+tex_math_dollars",
        "--to",
        "html5",
        "--mathml",
        "--wrap=none",
    ]
    proc = subprocess.run(
        command,
        input=markdown_text,
        text=True,
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "pandoc failed")
    return proc.stdout


def wrap_tables(parent: etree._Element) -> None:
    for table in list(parent.xpath(".//table")):
        table_parent = table.getparent()
        if table_parent is None or table_parent.get("class") == "table-wrap":
            continue
        wrapper = etree.Element("div")
        wrapper.set("class", "table-wrap")
        index = table_parent.index(table)
        table_parent.remove(table)
        wrapper.append(table)
        table_parent.insert(index, wrapper)


def normalize_fragment(fragment: str) -> str:
    parent = lxml_html.fragment_fromstring(fragment or "<p></p>", create_parent="div")
    etree.strip_elements(parent, "script", "style", with_tail=False)
    wrap_tables(parent)
    for image in parent.xpath(".//img"):
        if not (image.get("alt") or "").strip():
            image.set("alt", "插图")
    body = "".join(etree.tostring(child, encoding="unicode", method="xml") for child in parent)
    return body


def postprocess_html_refs(
    root: Path,
    page: Page,
    pages_by_rel: dict[str, Page],
    resources: dict[str, Resource],
    fragment: str,
) -> str:
    def rewrite_img(match: re.Match) -> str:
        src = match.group("src")
        if src.startswith(("../assets/", "assets/")):
            return match.group(0)
        resource = resource_lookup(root, page, src, resources)
        if resource and resource.status in {"ok", "placeholder"} and resource.epub_href:
            return f"{match.group(1)}{relative_from_page(page, resource.epub_href)}{match.group(3)}"
        return match.group(0)

    def rewrite_a(match: re.Match) -> str:
        href = match.group("href")
        if href.startswith(("#", "mailto:", "text/")) or is_external_href(href):
            return match.group(0)
        href_no_anchor, sep, anchor = href.partition("#")
        if href_no_anchor.endswith((".xhtml", ".html")):
            return match.group(0)
        target = resolve_local(root, page.source_path, href_no_anchor)
        try:
            rel = target.relative_to(root.resolve()).as_posix()
        except ValueError:
            return match.group(0)
        target_page = pages_by_rel.get(rel)
        if not target_page:
            return match.group(0)
        final_href = relative_from_page(page, target_page.output_href)
        if sep:
            final_href += f"#{anchor}"
        return f"{match.group(1)}{final_href}{match.group(3)}"

    fragment = HTML_IMG_RE.sub(rewrite_img, fragment)
    fragment = HTML_A_RE.sub(rewrite_a, fragment)
    return fragment


def write_xhtml(path: Path, title: str, body: str, css_href: str = "../styles/sep.css") -> None:
    content = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="{LANGUAGE}" lang="{LANGUAGE}">
<head>
  <meta charset="utf-8"/>
  <title>{html.escape(title)}</title>
  <link rel="stylesheet" type="text/css" href="{html.escape(css_href)}"/>
</head>
<body>
{body}
</body>
</html>
"""
    ET.fromstring(content.encode("utf-8"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_pages(root: Path, pages: list[Page], resources: dict[str, Resource], work_dir: Path) -> None:
    pages_by_rel = page_href_map(pages)
    ops_dir = work_dir / "OPS"
    text_dir = ops_dir / "text"
    text_dir.mkdir(parents=True, exist_ok=True)
    for page in pages:
        markdown_text = rewrite_links(root, page, pages_by_rel, resources)
        fragment = pandoc_fragment(markdown_text, root)
        fragment = postprocess_html_refs(root, page, pages_by_rel, resources, fragment)
        body = normalize_fragment(fragment)
        write_xhtml(ops_dir / page.output_href, page.title, body)


def write_static_files(work_dir: Path) -> None:
    ops_dir = work_dir / "OPS"
    (ops_dir / "styles").mkdir(parents=True, exist_ok=True)
    (ops_dir / "styles" / "sep.css").write_text(
        """body {
  font-family: -apple-system, BlinkMacSystemFont, "Noto Serif CJK SC", "Source Han Serif SC", serif;
  line-height: 1.72;
  margin: 0 5%;
  color: #222;
}
h1, h2, h3, h4, h5, h6 {
  line-height: 1.32;
  margin: 1.4em 0 0.7em;
}
p {
  margin: 0.75em 0;
}
a {
  color: #2457a6;
  text-decoration: none;
}
blockquote {
  border-left: 0.25em solid #ddd;
  margin: 1em 0;
  padding: 0.2em 0 0.2em 1em;
  color: #555;
}
img, svg {
  max-width: 100%;
  height: auto;
}
pre {
  white-space: pre-wrap;
  word-break: break-word;
  background: #f6f6f6;
  padding: 0.8em;
  border-radius: 0.25em;
}
code {
  font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
}
.table-wrap {
  overflow-x: auto;
  margin: 1em 0;
}
table {
  border-collapse: collapse;
  width: 100%;
}
th, td {
  border: 1px solid #ddd;
  padding: 0.35em 0.5em;
  vertical-align: top;
}
.title-page {
  text-align: center;
  margin-top: 18%;
}
.title-page h1 {
  font-size: 1.8em;
}
""",
        encoding="utf-8",
    )
    title_body = f"""<section class="title-page" epub:type="titlepage">
  <h1>{html.escape(PROJECT_DISPLAY_TITLE)}</h1>
  <p>基于 SEP-CN 项目内容生成的离线 EPUB。</p>
  <p>构建时间：{dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
  <p>EPUB 工程整理、资源锁定与发布审计：<a href="https://github.com/tradecatlabs">TradeCatLabs</a></p>
  <p>工程仓库：<a href="https://github.com/tradecatlabs/SEP-editing-cn">tradecatlabs/SEP-editing-cn</a>；X：<a href="https://x.com/123olp">@123olp</a></p>
</section>"""
    write_xhtml(ops_dir / "text" / "title.xhtml", PROJECT_DISPLAY_TITLE, title_body)


def toc_node_to_nav(node: TocNode, current_page_dir: str = "") -> str:
    label = html.escape(node.title)
    if node.page:
        href = posixpath.relpath(node.page.output_href, posixpath.dirname("nav.xhtml"))
        content = f'<a href="{html.escape(href)}">{label}</a>'
    elif href := first_descendant_href(node):
        href = posixpath.relpath(href, posixpath.dirname("nav.xhtml"))
        content = f'<a href="{html.escape(href)}">{label}</a>'
    else:
        content = f"<span>{label}</span>"
    children = "".join(toc_node_to_nav(child) for child in node.children)
    if children:
        return f"<li>{content}<ol>{children}</ol></li>"
    return f"<li>{content}</li>"


def write_nav(toc_roots: list[TocNode], pages: list[Page], work_dir: Path) -> None:
    first_body_href = pages[0].output_href if pages else "text/title.xhtml"
    first_body_href = posixpath.relpath(first_body_href, posixpath.dirname("nav.xhtml"))
    body = f"""<nav epub:type="toc" id="toc">
  <h1>目录</h1>
  <ol>
    <li><a href="text/title.xhtml">{html.escape(PROJECT_TITLE)}</a></li>
    {''.join(toc_node_to_nav(node) for node in toc_roots)}
  </ol>
</nav>
<nav epub:type="landmarks" id="landmarks">
  <h1>阅读入口</h1>
  <ol>
    <li><a epub:type="titlepage" href="text/title.xhtml">标题页</a></li>
    <li><a epub:type="toc" href="nav.xhtml">目录</a></li>
    <li><a epub:type="bodymatter" href="{html.escape(first_body_href)}">正文</a></li>
  </ol>
</nav>"""
    write_xhtml(work_dir / "OPS" / "nav.xhtml", "目录", body, css_href="styles/sep.css")


def first_descendant_href(node: TocNode) -> str | None:
    if node.page:
        return node.page.output_href
    for child in node.children:
        href = first_descendant_href(child)
        if href:
            return href
    return None


def write_ncx(toc_roots: list[TocNode], work_dir: Path, book_id: str) -> None:
    play_order = 1

    def navpoint(title: str, href: str, children: str = "") -> str:
        nonlocal play_order
        current = play_order
        play_order += 1
        return (
            f'<navPoint id="navPoint-{current}" playOrder="{current}">'
            f"<navLabel><text>{html.escape(title)}</text></navLabel>"
            f'<content src="{html.escape(href)}"/>'
            f"{children}</navPoint>"
        )

    def walk(node: TocNode) -> str:
        href = first_descendant_href(node)
        if not href:
            return ""
        children = "".join(walk(child) for child in node.children)
        return navpoint(node.title, href, children)

    points = navpoint(PROJECT_TITLE, "text/title.xhtml") + "".join(walk(node) for node in toc_roots)
    ncx = f"""<?xml version="1.0" encoding="utf-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="{html.escape(book_id)}"/>
    <meta name="dtb:depth" content="6"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle><text>{html.escape(PROJECT_TITLE)}</text></docTitle>
  <navMap>{points}</navMap>
</ncx>
"""
    ET.fromstring(ncx.encode("utf-8"))
    (work_dir / "OPS" / "toc.ncx").write_text(ncx, encoding="utf-8")


def manifest_id(index: int, prefix: str = "item") -> str:
    return f"{prefix}{index:05d}"


def write_opf(pages: list[Page], resources: dict[str, Resource], work_dir: Path, book_id: str) -> None:
    ops_dir = work_dir / "OPS"
    modified = dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    subject_xml = "\n".join(f"    <dc:subject>{html.escape(subject)}</dc:subject>" for subject in PROJECT_SUBJECTS)
    accessibility_xml = "\n".join(
        f'    <meta property="{html.escape(prop)}">{html.escape(value)}</meta>'
        for prop, value in ACCESSIBILITY_METADATA
    )
    manifest_items: list[tuple[str, str, str, str]] = [
        ("nav", "nav.xhtml", "application/xhtml+xml", ' properties="nav"'),
        ("ncx", "toc.ncx", "application/x-dtbncx+xml", ""),
        ("css", "styles/sep.css", "text/css", ""),
        ("title", "text/title.xhtml", "application/xhtml+xml", ""),
    ]
    for idx, page in enumerate(pages, 1):
        manifest_items.append((manifest_id(idx, "page"), page.output_href, "application/xhtml+xml", ""))

    asset_hrefs: dict[str, str] = {}
    for resource in resources.values():
        if resource.status != "ok" or not resource.epub_href:
            continue
        asset_hrefs[resource.epub_href] = resource.media_type or media_type_for(resource.epub_href)
    for idx, href in enumerate(sorted(asset_hrefs), 1):
        manifest_items.append((manifest_id(idx, "asset"), href, asset_hrefs[href], ""))

    manifest_xml = "\n".join(
        f'    <item id="{item_id}" href="{html.escape(href)}" media-type="{media}"{extra}/>'
        for item_id, href, media, extra in manifest_items
    )
    spine_items = ['    <itemref idref="title"/>']
    for idx, _page in enumerate(pages, 1):
        spine_items.append(f'    <itemref idref="{manifest_id(idx, "page")}"/>')

    opf = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid" prefix="schema: https://schema.org/">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title id="id">{html.escape(PROJECT_TITLE)}</dc:title>
    <dc:creator id="id-1">{html.escape(PROJECT_CREATOR)}</dc:creator>
    <dc:identifier>issn:{PROJECT_ISSN}</dc:identifier>
    <dc:identifier id="bookid">{html.escape(book_id)}</dc:identifier>
    <dc:rights>{html.escape(PROJECT_RIGHTS)}</dc:rights>
    <dc:source>{html.escape(PROJECT_SOURCE)}</dc:source>
    <dc:language>{LANGUAGE}</dc:language>
    <dc:date>{PROJECT_DATE}</dc:date>
    <dc:description>{html.escape(PROJECT_DESCRIPTION)}</dc:description>
    <dc:publisher>{html.escape(PROJECT_PUBLISHER)}</dc:publisher>
{subject_xml}
    <meta refines="#id" property="title-type">main</meta>
    <meta refines="#id" property="file-as">{html.escape(PROJECT_TITLE)}</meta>
{accessibility_xml}
    <meta property="dcterms:modified">{modified}</meta>
    <meta refines="#id-1" property="role" scheme="marc:relators">aut</meta>
    <meta refines="#id-1" property="file-as">{html.escape(PROJECT_CREATOR)}</meta>
  </metadata>
  <manifest>
{manifest_xml}
  </manifest>
  <spine toc="ncx">
{chr(10).join(spine_items)}
  </spine>
</package>
"""
    ET.fromstring(opf.encode("utf-8"))
    (ops_dir / "content.opf").write_text(opf, encoding="utf-8")


def write_container(work_dir: Path) -> None:
    meta_inf = work_dir / "META-INF"
    meta_inf.mkdir(parents=True, exist_ok=True)
    container = """<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""
    ET.fromstring(container.encode("utf-8"))
    (meta_inf / "container.xml").write_text(container, encoding="utf-8")


def write_resource_manifest(
    resources: dict[str, Resource],
    work_dir: Path,
    orphan_rels: list[str],
    pages: list[Page],
    filename: str = "resource-manifest.json",
) -> None:
    report_dir = work_dir / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": dt.datetime.now().isoformat(),
        "page_count": len(pages),
        "orphan_markdown_count": len(orphan_rels),
        "orphan_markdown": orphan_rels,
        "resources": [
            {
                "key": r.key,
                "original_href": r.original_href,
                "source_rel": r.source_rel,
                "line": r.line,
                "kind": r.kind,
                "is_remote": r.is_remote,
                "url": r.url,
                "resolved_url": r.resolved_url,
                "source_path": str(r.source_path) if r.source_path else None,
                "cache_path": str(r.cache_path) if r.cache_path else None,
                "epub_href": r.epub_href,
                "media_type": r.media_type,
                "sha256": r.sha256,
                "size": r.size,
                "status": r.status,
                "error": r.error,
                "placeholder_reason": r.placeholder_reason,
                "references": r.references,
            }
            for r in sorted(resources.values(), key=lambda item: item.key)
        ],
    }
    (report_dir / filename).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (report_dir / "orphan-pages.json").write_text(
        json.dumps({"orphan_markdown": orphan_rels}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def package_epub(work_dir: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    if tmp_path.exists():
        tmp_path.unlink()
    with zipfile.ZipFile(tmp_path, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        for base in [work_dir / "META-INF", work_dir / "OPS"]:
            for path in sorted(base.rglob("*")):
                if path.is_file():
                    arcname = path.relative_to(work_dir).as_posix()
                    zf.write(path, arcname, compress_type=zipfile.ZIP_DEFLATED)
    os.replace(tmp_path, output_path)


def audit_epub(epub_path: Path, resources: dict[str, Resource], work_dir: Path) -> dict:
    report: dict = {
        "epub_path": str(epub_path),
        "resource_error_count": sum(1 for r in resources.values() if r.status == "error"),
        "resource_placeholder_count": sum(1 for r in resources.values() if r.status == "placeholder"),
        "resource_fallback_count": sum(1 for r in resources.values() if r.resolved_url and r.url and r.resolved_url != r.url),
        "resource_count": len(resources),
    }
    with zipfile.ZipFile(epub_path) as zf:
        names = zf.namelist()
        first = names[0] if names else ""
        info = zf.getinfo("mimetype")
        report["zip"] = {
            "entry_count": len(names),
            "first_entry": first,
            "bad_crc": zf.testzip(),
            "mimetype_ok": first == "mimetype"
            and info.compress_type == zipfile.ZIP_STORED
            and zf.read("mimetype") == b"application/epub+zip",
        }
        container = ET.fromstring(zf.read("META-INF/container.xml"))
        opf_path = container.find(".//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile").attrib["full-path"]
        opf = ET.fromstring(zf.read(opf_path))
        opf_dir = posixpath.dirname(opf_path)
        ns = {"opf": "http://www.idpf.org/2007/opf", "dc": "http://purl.org/dc/elements/1.1/"}
        metadata = opf.find("opf:metadata", ns)
        meta_nodes = metadata.findall("opf:meta", ns) if metadata is not None else []
        report["metadata"] = {
            "title": [node.text or "" for node in opf.findall(".//dc:title", ns)],
            "creator": [node.text or "" for node in opf.findall(".//dc:creator", ns)],
            "publisher": [node.text or "" for node in opf.findall(".//dc:publisher", ns)],
            "rights": [node.text or "" for node in opf.findall(".//dc:rights", ns)],
            "source": [node.text or "" for node in opf.findall(".//dc:source", ns)],
            "identifier": [node.text or "" for node in opf.findall(".//dc:identifier", ns)],
            "language": [node.text or "" for node in opf.findall(".//dc:language", ns)],
            "description_count": len(opf.findall(".//dc:description", ns)),
            "subject_count": len(opf.findall(".//dc:subject", ns)),
            "accessibility_meta_count": sum(
                1 for node in meta_nodes if (node.attrib.get("property") or "").startswith("schema:access")
            ),
        }
        items = opf.findall(".//opf:manifest/opf:item", ns)
        ids = {item.attrib["id"] for item in items}
        missing_manifest = []
        for item in items:
            href = item.attrib["href"]
            full = posixpath.normpath(posixpath.join(opf_dir, href))
            if full not in names:
                missing_manifest.append(full)
        spine_missing = [
            item.attrib.get("idref")
            for item in opf.findall(".//opf:spine/opf:itemref", ns)
            if item.attrib.get("idref") not in ids
        ]
        xhtml_files = [n for n in names if n.endswith((".xhtml", ".html"))]
        xml_errors = []
        image_refs = []
        missing_alt = []
        href_refs = []
        anchors: dict[str, set[str]] = {}
        for name in xhtml_files:
            raw = zf.read(name)
            try:
                ET.fromstring(raw)
            except Exception as exc:  # noqa: BLE001
                xml_errors.append([name, str(exc)])
            text = raw.decode("utf-8", errors="replace")
            image_refs.extend((name, match.group(1)) for match in re.finditer(r'<img[^>]+src="([^"]+)"', text))
            missing_alt.extend(
                (name, match.group("src"))
                for match in re.finditer(r'<img\b(?P<tag>[^>]*)\bsrc="(?P<src>[^"]+)"[^>]*>', text)
                if not re.search(r'\balt="[^"]+"', match.group(0))
            )
            href_refs.extend((name, match.group(1)) for match in re.finditer(r'<a[^>]+href="([^"]+)"', text))
            anchors[name] = set(re.findall(r'\sid="([^"]+)"', text)) | set(re.findall(r'\sname="([^"]+)"', text))

        missing_images = []
        for source, src in image_refs:
            clean = src.split("#", 1)[0].split("?", 1)[0]
            if not clean or is_external_href(clean) or clean.startswith(("data:", "mailto:")):
                continue
            target = posixpath.normpath(posixpath.join(posixpath.dirname(source), unquote(clean)))
            if target not in names:
                missing_images.append([source, src, target])

        broken_internal = []
        external_links = 0
        for source, href in href_refs:
            if is_external_href(href) or href.startswith("mailto:"):
                external_links += 1
                continue
            clean, _, anchor = href.partition("#")
            target = posixpath.normpath(posixpath.join(posixpath.dirname(source), unquote(clean))) if clean else source
            if target not in names:
                broken_internal.append([source, href, "missing_file", target])
            elif anchor and anchor not in anchors.get(target, set()):
                broken_internal.append([source, href, "missing_anchor", f"{target}#{anchor}"])

        nav_target_errors = []
        nav_span_labels = []
        nav_link_count = 0
        nav_types = []
        nav_item = next((item for item in items if "nav" in item.attrib.get("properties", "").split()), None)
        if nav_item is not None:
            nav_path = posixpath.normpath(posixpath.join(opf_dir, nav_item.attrib["href"]))
            nav_text = zf.read(nav_path).decode("utf-8", errors="replace")
            nav_span_labels = [
                re.sub(r"<[^>]+>", "", match.group(1)).strip()
                for match in re.finditer(r"<span(?:\s[^>]*)?>(.*?)</span>", nav_text, re.DOTALL)
            ]
            nav_types = re.findall(r"<nav\b[^>]*(?:epub:)?type=\"([^\"]+)\"", nav_text)
            nav_link_count = len(re.findall(r"<a\b[^>]*\bhref=\"[^\"]+\"", nav_text))
            for href in re.findall(r"<a\b[^>]*\bhref=\"([^\"]+)\"", nav_text):
                if is_external_href(href) or href.startswith("mailto:"):
                    continue
                clean, _, anchor = href.partition("#")
                target = posixpath.normpath(posixpath.join(posixpath.dirname(nav_path), unquote(clean))) if clean else nav_path
                if target not in names:
                    nav_target_errors.append([href, "missing_file", target])
                elif anchor and anchor not in anchors.get(target, set()):
                    nav_target_errors.append([href, "missing_anchor", f"{target}#{anchor}"])

        report["epub"] = {
            "opf_path": opf_path,
            "manifest_count": len(items),
            "missing_manifest_count": len(missing_manifest),
            "missing_manifest": missing_manifest[:50],
            "spine_missing_count": len(spine_missing),
            "spine_missing": spine_missing[:50],
            "xhtml_count": len(xhtml_files),
            "xml_error_count": len(xml_errors),
            "xml_errors": xml_errors[:50],
            "image_ref_count": len(image_refs),
            "missing_alt_count": len(missing_alt),
            "missing_alt": missing_alt[:50],
            "missing_image_count": len(missing_images),
            "missing_images": missing_images[:50],
            "href_ref_count": len(href_refs),
            "external_link_count": external_links,
            "broken_internal_count": len(broken_internal),
            "broken_internal": broken_internal[:50],
            "nav_span_count": len(nav_span_labels),
            "nav_span_labels": nav_span_labels[:50],
            "nav_link_count": nav_link_count,
            "nav_types": nav_types,
            "nav_has_landmarks": "landmarks" in nav_types,
            "nav_target_error_count": len(nav_target_errors),
            "nav_target_errors": nav_target_errors[:50],
        }
    report["passed"] = (
        report["resource_error_count"] == 0
        and report["zip"]["mimetype_ok"]
        and report["zip"]["bad_crc"] is None
        and report["epub"]["missing_manifest_count"] == 0
        and report["epub"]["spine_missing_count"] == 0
        and report["epub"]["xml_error_count"] == 0
        and report["epub"]["missing_alt_count"] == 0
        and report["epub"]["missing_image_count"] == 0
        and report["epub"]["broken_internal_count"] == 0
        and report["epub"]["nav_span_count"] == 0
        and report["epub"]["nav_target_error_count"] == 0
        and report["epub"]["nav_has_landmarks"]
        and report["metadata"]["description_count"] > 0
        and report["metadata"]["subject_count"] > 0
        and report["metadata"]["accessibility_meta_count"] > 0
    )
    report_dir = work_dir / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "epub-audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def clean_work_dir(work_dir: Path, keep_work: bool) -> None:
    if work_dir.exists() and not keep_work:
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    build_dir = (root / args.build_dir).resolve() if not args.build_dir.is_absolute() else args.build_dir.resolve()
    dist_dir = (root / args.dist_dir).resolve() if not args.dist_dir.is_absolute() else args.dist_dir.resolve()
    work_dir = build_dir

    if args.scan_only:
        work_dir.mkdir(parents=True, exist_ok=True)
    else:
        clean_work_dir(work_dir, keep_work=args.keep_work)
    toc_roots, pages, orphan_rels = collect_pages(root, limit=args.limit)
    resources = scan_resources(root, pages)

    if args.scan_only:
        write_resource_manifest(resources, work_dir, orphan_rels, pages, filename="resource-scan.json")
        print(json.dumps({"pages": len(pages), "resources": len(resources), "orphans": len(orphan_rels)}, ensure_ascii=False))
        return 0

    write_static_files(work_dir)
    materialize_resources(root, resources, work_dir, jobs=args.jobs, timeout=args.timeout, retries=args.retries)
    write_resource_manifest(resources, work_dir, orphan_rels, pages)

    failed = [r for r in resources.values() if r.status == "error"]
    if failed:
        print(f"资源锁定失败: {len(failed)}", file=sys.stderr)
        for item in failed[:20]:
            print(f"- {item.original_href}: {item.error}", file=sys.stderr)
        return 2

    build_pages(root, pages, resources, work_dir)
    book_id = f"urn:uuid:{uuid.uuid4()}"
    write_nav(toc_roots, pages, work_dir)
    write_ncx(toc_roots, work_dir, book_id)
    write_opf(pages, resources, work_dir, book_id)
    write_container(work_dir)

    output_path = dist_dir / args.output_name
    package_epub(work_dir, output_path)
    audit = audit_epub(output_path, resources, work_dir)
    print(json.dumps({
        "output": str(output_path),
        "pages": len(pages),
        "resources": len(resources),
        "passed": audit["passed"],
        "audit": str(work_dir / "reports" / "epub-audit.json"),
    }, ensure_ascii=False, indent=2))
    return 0 if audit["passed"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
