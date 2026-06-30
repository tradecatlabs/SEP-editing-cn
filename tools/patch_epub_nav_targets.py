#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import posixpath
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import unquote
import xml.etree.ElementTree as ET


NAV_ENTRY = "OPS/nav.xhtml"
XHTML_NS = "http://www.w3.org/1999/xhtml"
EPUB_NS = "http://www.idpf.org/2007/ops"
OPF_NS = {
    "opf": "http://www.idpf.org/2007/opf",
    "dc": "http://purl.org/dc/elements/1.1/",
}
LI_TAG = f"{{{XHTML_NS}}}li"
SPAN_TAG = f"{{{XHTML_NS}}}span"
A_TAG = f"{{{XHTML_NS}}}a"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="修复 EPUB nav.xhtml 中没有 href 的父级目录项，并保持 OPF、NCX、封面、元数据和 spine 不变。"
    )
    parser.add_argument("input", type=Path, help="输入 EPUB")
    parser.add_argument("output", type=Path, nargs="?", help="输出 EPUB；使用 --in-place 时可省略")
    parser.add_argument("--in-place", action="store_true", help="原地修复输入 EPUB，并自动写备份")
    parser.add_argument("--backup", type=Path, help="原地修复时的备份路径")
    parser.add_argument("--report", type=Path, help="JSON 修复报告路径")
    return parser.parse_args()


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def local_join(base: str, href: str) -> str:
    return posixpath.normpath(posixpath.join(posixpath.dirname(base), href))


def dc_texts(opf: ET.Element, name: str) -> list[str]:
    return [node.text or "" for node in opf.findall(f".//dc:{name}", OPF_NS)]


def nav_span_labels(nav_text: str) -> list[str]:
    try:
        root = ET.fromstring(nav_text)
    except ET.ParseError:
        return re.findall(r"<span(?:\s[^>]*)?>(.*?)</span>", nav_text)
    return ["".join(node.itertext()).strip() for node in root.iter(SPAN_TAG)]


def nav_link_hrefs(nav_text: str) -> list[str]:
    try:
        root = ET.fromstring(nav_text)
    except ET.ParseError:
        return re.findall(r"<a\s+[^>]*href=\"([^\"]+)\"", nav_text)
    return [node.attrib["href"] for node in root.iter(A_TAG) if node.attrib.get("href")]


def internal_nav_target_errors(nav_text: str, names: set[str]) -> list[list[str]]:
    errors = []
    for href in nav_link_hrefs(nav_text):
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", href) or href.startswith(("mailto:", "#")):
            continue
        clean = href.split("#", 1)[0].split("?", 1)[0]
        if not clean:
            continue
        target = posixpath.normpath(posixpath.join(posixpath.dirname(NAV_ENTRY), unquote(clean)))
        if target not in names:
            errors.append([href, target])
    return errors


def inspect_epub(epub_path: Path) -> dict:
    with zipfile.ZipFile(epub_path) as archive:
        bad_crc = archive.testzip()
        names = archive.namelist()
        name_set = set(names)
        container = ET.fromstring(archive.read("META-INF/container.xml"))
        rootfile = container.find(".//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile")
        if rootfile is None:
            raise RuntimeError("META-INF/container.xml 缺少 rootfile")
        opf_path = rootfile.attrib["full-path"]
        opf_raw = archive.read(opf_path)
        opf = ET.fromstring(opf_raw)
        items = opf.findall(".//opf:manifest/opf:item", OPF_NS)
        manifest = {item.attrib["id"]: item.attrib for item in items}
        spine = [item.attrib.get("idref") for item in opf.findall(".//opf:spine/opf:itemref", OPF_NS)]
        ncx_item = next(
            (item.attrib for item in items if item.attrib.get("media-type") == "application/x-dtbncx+xml"),
            None,
        )
        ncx_raw = archive.read(local_join(opf_path, ncx_item["href"])) if ncx_item else b""
        nav_raw = archive.read(NAV_ENTRY)
        nav_text = nav_raw.decode("utf-8", "ignore")
        cover_items = []
        for item_id, item in manifest.items():
            href = item.get("href", "")
            if "cover" not in item_id.lower() and "cover" not in href.lower() and item.get("properties") != "cover-image":
                continue
            full = local_join(opf_path, href)
            if full not in name_set and href in name_set:
                full = href
            cover_items.append(
                {
                    "id": item_id,
                    "href": href,
                    "full": full,
                    "exists": full in name_set,
                    "sha256": sha_bytes(archive.read(full)) if full in name_set else None,
                    "size": len(archive.read(full)) if full in name_set else None,
                }
            )
        return {
            "sha256": sha_bytes(epub_path.read_bytes()),
            "size": epub_path.stat().st_size,
            "bad_crc": bad_crc,
            "first_entry": names[0] if names else "",
            "mimetype_uncompressed": bool(
                names
                and names[0] == "mimetype"
                and archive.getinfo("mimetype").compress_type == zipfile.ZIP_STORED
            ),
            "metadata": {
                "title": dc_texts(opf, "title"),
                "creator": dc_texts(opf, "creator"),
                "publisher": dc_texts(opf, "publisher"),
                "language": dc_texts(opf, "language"),
                "date": dc_texts(opf, "date"),
                "identifier": dc_texts(opf, "identifier"),
                "rights": dc_texts(opf, "rights"),
                "source": dc_texts(opf, "source"),
            },
            "manifest_count": len(items),
            "spine_count": len(spine),
            "xhtml_count": sum(name.endswith((".xhtml", ".html")) for name in names),
            "opf_sha256": sha_bytes(opf_raw),
            "nav_sha256": sha_bytes(nav_raw),
            "ncx_sha256": sha_bytes(ncx_raw),
            "nav_span_count": len(nav_span_labels(nav_text)),
            "nav_span_labels": nav_span_labels(nav_text),
            "nav_link_count": len(nav_link_hrefs(nav_text)),
            "nav_target_errors": internal_nav_target_errors(nav_text, name_set),
            "ncx_navpoint_count": ncx_raw.decode("utf-8", "ignore").count("<navPoint"),
            "cover_items": cover_items,
        }


def patch_nav(raw: bytes) -> bytes:
    ET.register_namespace("", XHTML_NS)
    ET.register_namespace("epub", EPUB_NS)
    root = ET.fromstring(raw)
    changed = 0
    for li in root.iter(LI_TAG):
        children = list(li)
        if not children or children[0].tag != SPAN_TAG:
            continue
        first_link = next((node for node in li.iter(A_TAG) if node.attrib.get("href")), None)
        if first_link is None:
            continue
        span = children[0]
        link = ET.Element(A_TAG, {"href": first_link.attrib["href"]})
        link.text = span.text
        link.tail = span.tail
        for child in list(span):
            span.remove(child)
            link.append(child)
        li.remove(span)
        li.insert(0, link)
        changed += 1
    patched = ET.tostring(root, encoding="utf-8", xml_declaration=False)
    if changed == 0 and nav_span_labels(raw.decode("utf-8", "ignore")):
        raise RuntimeError("nav.xhtml 仍有 span，但没有可自动指向的第一个子链接")
    ET.fromstring(patched)
    return patched


def clone_info(info: zipfile.ZipInfo, compress_type: int | None = None) -> zipfile.ZipInfo:
    cloned = zipfile.ZipInfo(info.filename, info.date_time)
    cloned.comment = info.comment
    cloned.extra = info.extra
    cloned.internal_attr = info.internal_attr
    cloned.external_attr = info.external_attr
    cloned.create_system = info.create_system
    cloned.compress_type = info.compress_type if compress_type is None else compress_type
    return cloned


def write_patched_epub(source: Path, output: Path) -> None:
    with zipfile.ZipFile(source, "r") as source_archive, zipfile.ZipFile(output, "w") as output_archive:
        infos = source_archive.infolist()
        if not infos or infos[0].filename != "mimetype":
            raise RuntimeError("mimetype 不是第一项，拒绝继续")
        for info in infos:
            data = source_archive.read(info.filename)
            if info.filename == NAV_ENTRY:
                data = patch_nav(data)
            compress_type = zipfile.ZIP_STORED if info.filename == "mimetype" else info.compress_type
            output_archive.writestr(clone_info(info, compress_type), data)


def assert_invariants(before: dict, after: dict) -> dict:
    invariant_keys = [
        "metadata",
        "manifest_count",
        "spine_count",
        "xhtml_count",
        "opf_sha256",
        "ncx_sha256",
        "cover_items",
    ]
    preserved = {key: before[key] == after[key] for key in invariant_keys}
    if not all(preserved.values()):
        broken = {key: [before[key], after[key]] for key, value in preserved.items() if not value}
        raise RuntimeError("目录修复触碰了不该触碰的结构: " + json.dumps(broken, ensure_ascii=False, indent=2))
    if after["bad_crc"] is not None:
        raise RuntimeError(f"zip CRC 失败: {after['bad_crc']}")
    if after["nav_span_count"] != 0:
        raise RuntimeError(f"nav.xhtml 仍有无目标 span: {after['nav_span_labels'][:20]}")
    if after["nav_target_errors"]:
        raise RuntimeError("nav.xhtml 存在坏目标: " + json.dumps(after["nav_target_errors"][:20], ensure_ascii=False))
    return preserved


def default_backup_path(path: Path) -> Path:
    return path.with_name(f"{path.stem}.before-nav-target-fix{path.suffix}")


def main() -> int:
    args = parse_args()
    source = args.input.resolve()
    if not source.exists():
        raise FileNotFoundError(source)
    if args.in_place:
        output = source
        backup = args.backup.resolve() if args.backup else default_backup_path(source)
    else:
        if args.output is None:
            raise SystemExit("非 --in-place 模式必须提供输出 EPUB 路径")
        output = args.output.resolve()
        backup = None

    before = inspect_epub(source)
    if args.in_place:
        shutil.copy2(source, backup)
        patch_source = backup
    else:
        patch_source = source

    output.parent.mkdir(parents=True, exist_ok=True)
    temp_fd, temp_name = tempfile.mkstemp(prefix="sep-nav-targets-", suffix=".epub", dir=str(output.parent))
    os.close(temp_fd)
    temp_path = Path(temp_name)
    try:
        write_patched_epub(patch_source, temp_path)
        after_temp = inspect_epub(temp_path)
        preserved = assert_invariants(before, after_temp)
        os.replace(temp_path, output)
    finally:
        if temp_path.exists():
            temp_path.unlink()

    after = inspect_epub(output)
    report = {
        "input": str(source),
        "output": str(output),
        "backup": str(backup) if backup else None,
        "before": before,
        "after": after,
        "invariants_preserved": preserved,
        "changed_payload": {
            "nav_xhtml_changed": before["nav_sha256"] != after["nav_sha256"],
            "nav_span_count_before": before["nav_span_count"],
            "nav_span_count_after": after["nav_span_count"],
            "nav_link_count_before": before["nav_link_count"],
            "nav_link_count_after": after["nav_link_count"],
            "sha256_before": before["sha256"],
            "sha256_after": after["sha256"],
        },
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
