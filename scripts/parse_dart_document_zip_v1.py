#!/usr/bin/env python3
"""Parse Open DART document.zip bytes → plain text for MD&A ingest (PoC v2).

Reproduce:
  py scripts/parse_dart_document_zip_v1.py --zip-file tests/fixtures/dart_mda_document_v1.zip
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.kospi_dart_mda_poc_lib_v1 import extract_mda_section  # noqa: E402

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")
BLOCK_TAGS = frozenset({"p", "section", "div", "li", "tr", "h1", "h2", "h3", "title"})
CONTAINER_TAGS = frozenset({"document", "body", "html", "root", "xbrl"})


def _local_tag(node: ET.Element) -> str:
    tag = node.tag
    if "}" in tag:
        tag = tag.rsplit("}", 1)[-1]
    return tag.lower()


def _node_inline_text(node: ET.Element) -> str:
    parts: list[str] = []
    if node.text and node.text.strip():
        parts.append(node.text.strip())
    for child in list(node):
        parts.append(_node_inline_text(child))
        if child.tail and child.tail.strip():
            parts.append(child.tail.strip())
    return WS_RE.sub(" ", " ".join(parts)).strip()


def _xml_text_blocks(node: ET.Element) -> list[str]:
    tag = _local_tag(node)
    if tag in CONTAINER_TAGS:
        blocks: list[str] = []
        for child in list(node):
            blocks.extend(_xml_text_blocks(child))
        return blocks
    if tag in BLOCK_TAGS:
        block = _node_inline_text(node)
        return [block] if block else []
    blocks = []
    for child in list(node):
        blocks.extend(_xml_text_blocks(child))
    if not list(node):
        inline = _node_inline_text(node)
        if inline:
            blocks.append(inline)
    return blocks


def _is_zip_payload(data: bytes) -> bool:
    return len(data) >= 4 and data[:2] == b"PK"


def _strip_xml_text(raw: str) -> str:
    text = TAG_RE.sub(" ", raw)
    text = text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    return WS_RE.sub(" ", text).strip()


def _sanitize_xml_ampersands(raw: bytes) -> bytes:
    text = raw.decode("utf-8", errors="replace")
    text = re.sub(r"&(?!(amp|lt|gt|quot|apos|#\d+|#x[\da-fA-F]+);)", "&amp;", text)
    return text.encode("utf-8")


def extract_text_from_xml_bytes(data: bytes) -> str:
    sanitized = _sanitize_xml_ampersands(data)
    try:
        root = ET.fromstring(sanitized)
    except ET.ParseError:
        return _split_markup_blocks(data.decode("utf-8", errors="replace"))
    blocks = _xml_text_blocks(root)
    if not blocks:
        return _split_markup_blocks(data.decode("utf-8", errors="replace"))
    return "\n\n".join(blocks).strip()


def _split_markup_blocks(raw: str) -> str:
    pieces = re.split(r"</(?:p|section|div|tr|li|h[1-3])\s*>", raw, flags=re.IGNORECASE)
    blocks: list[str] = []
    for piece in pieces:
        block = _strip_xml_text(piece)
        if block and len(block) >= 8:
            blocks.append(block)
    return "\n\n".join(blocks).strip()


def _member_mda_score(name: str, member_text: str) -> tuple[int, str]:
    mda = extract_mda_section(member_text)
    score = len(mda)
    head = member_text[:400]
    if "감사보고서" in head or "감 사 보 고 서" in head:
        score -= 200_000
    base = name.rsplit("/", 1)[-1]
    if base.endswith(".xml") and "_" not in base.replace(".xml", ""):
        score += 10_000
    return score, mda


def extract_text_from_zip_bytes(zip_bytes: bytes) -> dict[str, Any]:
    if not _is_zip_payload(zip_bytes):
        snippet = zip_bytes[:500].decode("utf-8", errors="replace")
        raise ValueError(f"not_zip_payload: {snippet[:120]}")

    texts: list[str] = []
    members: list[str] = []
    best_score = -1
    best_mda = ""
    best_member = ""

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for name in zf.namelist():
            if name.endswith("/"):
                continue
            lower = name.lower()
            if not (lower.endswith(".xml") or lower.endswith(".html") or lower.endswith(".htm")):
                continue
            members.append(name)
            raw = zf.read(name)
            member_text = extract_text_from_xml_bytes(raw)
            texts.append(member_text)
            score, mda = _member_mda_score(name, member_text)
            if score > best_score:
                best_score = score
                best_mda = mda
                best_member = name

    combined = "\n\n".join(t for t in texts if t).strip()
    if not combined:
        raise ValueError("zip_contains_no_extractable_text")

    mda = best_mda or extract_mda_section(combined)
    return {
        "ok": True,
        "schema": "dart_document_zip_parse_v1",
        "zip_members_parsed": members,
        "mda_source_member": best_member,
        "combined_char_count": len(combined),
        "mda_char_count": len(mda),
        "combined_text": combined,
        "mda_text": mda,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--zip-file", type=Path, required=True)
    ap.add_argument("--mda-only", action="store_true")
    args = ap.parse_args()
    data = args.zip_file.read_bytes()
    out = extract_text_from_zip_bytes(data)
    if args.mda_only:
        print(out["mda_text"])
    else:
        print(json.dumps({k: v for k, v in out.items() if k not in ("combined_text", "mda_text")}, ensure_ascii=False))
        print(json.dumps({"mda_preview": out["mda_text"][:400]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
