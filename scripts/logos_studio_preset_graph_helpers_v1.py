"""Shared helpers for Logos Studio preset expansion (graph verse → node ids)."""

from __future__ import annotations

import re
from typing import Any

from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref


def parse_verse_tokens(raw: str) -> list[str]:
    """Extract canonical refs from free-text BigSet verse_refs strings."""
    out: list[str] = []
    for chunk in re.split(r"[;|,]", raw or ""):
        chunk = chunk.strip()
        if not chunk:
            continue
        m = re.search(
            r"([1-3]?\s?[A-Za-z]+)\s+(\d+)(?::(\d+)(?:-(\d+))?)?",
            chunk,
        )
        if not m:
            continue
        book_raw = re.sub(r"\s+", "", m.group(1)).lower()
        ch = m.group(2)
        v1 = m.group(3)
        v2 = m.group(4)
        book_map = {
            "genesis": "Gen",
            "gen": "Gen",
            "psalm": "Ps",
            "ps": "Ps",
            "deuteronomy": "Deut",
            "deut": "Deut",
            "job": "Job",
            "jude": "Jude",
            "exodus": "Exod",
            "exod": "Exod",
            "daniel": "Dan",
            "dan": "Dan",
        }
        book = book_map.get(book_raw, book_raw[:1].upper() + book_raw[1:3].title())
        if book_raw in book_map:
            book = book_map[book_raw]
        elif book_raw.startswith("1") and "enoch" in book_raw:
            continue
        elif "enoch" in book_raw or "jubilees" in book_raw.lower() or "4q" in book_raw.lower():
            continue
        if v1 and v2:
            for v in range(int(v1), int(v2) + 1):
                canon = canonical_verse_ref(f"{book}.{ch}.{v}")
                if canon:
                    out.append(canon)
        elif v1:
            canon = canonical_verse_ref(f"{book}.{ch}.{v1}")
            if canon:
                out.append(canon)
        else:
            canon = canonical_verse_ref(f"{book}.{ch}.1")
            if canon:
                out.append(canon)
    return list(dict.fromkeys(out))


def verse_node_ids(graph_doc: dict[str, Any], verse_refs: set[str]) -> list[str]:
    canon_refs = {canonical_verse_ref(v) for v in verse_refs if canonical_verse_ref(v)}
    ids: list[str] = []
    for n in graph_doc.get("nodes") or []:
        ref = canonical_verse_ref(str(n.get("ref") or ""))
        label = canonical_verse_ref(str(n.get("label") or "").replace(" ", "."))
        nid = str(n.get("id") or "")
        for vr in canon_refs:
            if not vr:
                continue
            if ref == vr or label == vr or nid == vr or nid.endswith(f"::{vr}"):
                ids.append(nid)
                break
    return list(dict.fromkeys(ids))


def chapter_node_ids(graph_doc: dict[str, Any], book: str, chapter: int) -> list[str]:
    prefix = f"{book}.{chapter}."
    ids: list[str] = []
    for n in graph_doc.get("nodes") or []:
        ref = str(n.get("ref") or "")
        if ref.startswith(prefix):
            ids.append(str(n["id"]))
    return ids
