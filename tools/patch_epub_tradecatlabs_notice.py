#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import posixpath
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET


TITLE_ENTRY = "OPS/text/title.xhtml"
MARKER = "tradecatlabs/SEP-editing-cn"
NOTICE = """  <p>EPUB 工程整理、资源锁定与发布审计：<a href="https://github.com/tradecatlabs">TradeCatLabs</a></p>
  <p>工程仓库：<a href="https://github.com/tradecatlabs/SEP-editing-cn">tradecatlabs/SEP-editing-cn</a>；X：<a href="https://x.com/123olp">@123olp</a></p>"""
NOTICE_LINE_RE = re.compile(
    r"\n  <p>(?:EPUB 工程整理、资源锁定与发布审计：|工程仓库：|实验室负责人：).*?</p>",
    re.DOTALL,
)
OPF_NS = {
    "opf": "http://www.idpf.org/2007/opf",
    "dc": "http://purl.org/dc/elements/1.1/",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="向既有 SEP EPUB 标题页写入 TradeCatLabs 说明，并保持 OPF、nav、NCX、封面和目录不变。"
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


def inspect_epub(epub_path: Path) -> dict:
    with zipfile.ZipFile(epub_path) as archive:
        bad_crc = archive.testzip()
        names = archive.namelist()
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
        nav_item = next((item.attrib for item in items if item.attrib.get("properties") == "nav"), None)
        ncx_item = next(
            (item.attrib for item in items if item.attrib.get("media-type") == "application/x-dtbncx+xml"),
            None,
        )
        nav_raw = archive.read(local_join(opf_path, nav_item["href"])) if nav_item else b""
        ncx_raw = archive.read(local_join(opf_path, ncx_item["href"])) if ncx_item else b""
        title_raw = archive.read(TITLE_ENTRY)
        cover_items = []
        for item_id, item in manifest.items():
            href = item.get("href", "")
            if "cover" not in item_id.lower() and "cover" not in href.lower() and item.get("properties") != "cover-image":
                continue
            full = local_join(opf_path, href)
            if full not in names and href in names:
                full = href
            cover_items.append(
                {
                    "id": item_id,
                    "href": href,
                    "full": full,
                    "exists": full in names,
                    "sha256": sha_bytes(archive.read(full)) if full in names else None,
                    "size": len(archive.read(full)) if full in names else None,
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
            "nav_link_count": nav_raw.decode("utf-8", "ignore").count("<a "),
            "ncx_navpoint_count": ncx_raw.decode("utf-8", "ignore").count("<navPoint"),
            "opf_sha256": sha_bytes(opf_raw),
            "nav_sha256": sha_bytes(nav_raw),
            "ncx_sha256": sha_bytes(ncx_raw),
            "title_sha256": sha_bytes(title_raw),
            "cover_items": cover_items,
            "tradecatlabs_in_title": MARKER in title_raw.decode("utf-8", "ignore"),
        }


def patch_title(raw: bytes) -> bytes:
    text = raw.decode("utf-8")
    if NOTICE in text:
        return raw
    if "</section>" not in text:
        raise RuntimeError(f"{TITLE_ENTRY} 缺少 </section>，拒绝盲改")
    text = NOTICE_LINE_RE.sub("", text)
    text = text.replace("</section>", NOTICE + "\n</section>", 1)
    ET.fromstring(text.encode("utf-8"))
    return text.encode("utf-8")


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
            if info.filename == TITLE_ENTRY:
                data = patch_title(data)
            compress_type = zipfile.ZIP_STORED if info.filename == "mimetype" else info.compress_type
            output_archive.writestr(clone_info(info, compress_type), data)


def assert_invariants(before: dict, after: dict) -> dict:
    invariant_keys = [
        "metadata",
        "manifest_count",
        "spine_count",
        "xhtml_count",
        "nav_link_count",
        "ncx_navpoint_count",
        "opf_sha256",
        "nav_sha256",
        "ncx_sha256",
        "cover_items",
    ]
    preserved = {key: before[key] == after[key] for key in invariant_keys}
    if not all(preserved.values()):
        broken = {key: [before[key], after[key]] for key, value in preserved.items() if not value}
        raise RuntimeError("修复触碰了不该触碰的结构: " + json.dumps(broken, ensure_ascii=False, indent=2))
    if after["bad_crc"] is not None:
        raise RuntimeError(f"zip CRC 失败: {after['bad_crc']}")
    if not after["tradecatlabs_in_title"]:
        raise RuntimeError("TradeCatLabs 正文提示未写入 title.xhtml")
    return preserved


def default_backup_path(path: Path) -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    return path.with_name(f"{path.stem}.before-tradecatlabs-fix-{stamp}{path.suffix}")


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
    temp_fd, temp_name = tempfile.mkstemp(prefix="sep-tradecatlabs-", suffix=".epub", dir=str(output.parent))
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
            "title_xhtml_changed": before["title_sha256"] != after["title_sha256"],
            "tradecatlabs_in_title": after["tradecatlabs_in_title"],
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
