#!/usr/bin/env python3
"""Shared helpers for Logos Studio 31k bloom secondary fetch (P5/P6, B-track)."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

BOOK_ALIASES: dict[str, str] = {
    "창세기": "Gen",
    "출애굽": "Exod",
    "레위": "Lev",
    "민수": "Num",
    "신명": "Deut",
    "욥기": "Job",
    "욥": "Job",
    "시편": "Ps",
    "이사야": "Isa",
    "예레미야": "Jer",
    "에스겔": "Ezek",
    "다니엘": "Dan",
    "마태": "Matt",
    "마가": "Mark",
    "누가": "Luke",
    "요한": "John",
    "사도행전": "Acts",
    "로마": "Rom",
    "고린도": "1Cor",
    "갈라디아": "Gal",
    "에베소": "Eph",
    "빌립보": "Phil",
    "골로새": "Col",
    "데살로니가": "1Thess",
    "디모데": "1Tim",
    "디도": "Titus",
    "히브리": "Heb",
    "야고": "Jas",
    "베드로": "1Pet",
    "유다": "Jude",
    "요한계시록": "Rev",
    "계 Revelation": "Rev",
}

CHAPTER_RE = re.compile(r"(?:^|\s)(\d+)\s*장")
VERSE_REF_RE = re.compile(r"^([A-Za-z0-9_]+)\.(\d+)\.(\d+)$")


def load_bloom_index(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    return doc if isinstance(doc, dict) else None


def _books_from_query(query: str) -> set[str]:
    q = (query or "").strip()
    books: set[str] = set()
    low = q.lower()
    for alias, book in BOOK_ALIASES.items():
        if alias in q or alias.lower() in low:
            books.add(book)
    for book in (
        "Gen",
        "Exod",
        "Lev",
        "Num",
        "Deut",
        "Josh",
        "Judg",
        "Ruth",
        "1Sam",
        "2Sam",
        "1Kgs",
        "2Kgs",
        "1Chr",
        "2Chr",
        "Ezra",
        "Neh",
        "Esth",
        "Job",
        "Ps",
        "Prov",
        "Eccl",
        "Song",
        "Isa",
        "Jer",
        "Lam",
        "Ezek",
        "Dan",
        "Hos",
        "Joel",
        "Amos",
        "Obad",
        "Jonah",
        "Mic",
        "Nah",
        "Hab",
        "Zeph",
        "Hag",
        "Zech",
        "Mal",
        "Matt",
        "Mark",
        "Luke",
        "John",
        "Acts",
        "Rom",
        "1Cor",
        "2Cor",
        "Gal",
        "Eph",
        "Phil",
        "Col",
        "1Thess",
        "2Thess",
        "1Tim",
        "2Tim",
        "Titus",
        "Phlm",
        "Heb",
        "Jas",
        "1Pet",
        "2Pet",
        "1John",
        "2John",
        "3John",
        "Jude",
        "Rev",
    ):
        if book.lower() in low or f"{book.lower()}." in low:
            books.add(book)
    return books


def _chapters_from_query(query: str) -> set[int]:
    return {int(m.group(1)) for m in CHAPTER_RE.finditer(query or "")}


def expand_verse_refs_via_bloom(
    query: str,
    base_refs: list[str],
    bloom_index: dict[str, Any],
    *,
    max_extra: int = 24,
    min_primary: int = 4,
) -> tuple[list[str], dict[str, Any]]:
    """Secondary fetch: append chapter-shard refs when primary router path is sparse."""
    meta: dict[str, Any] = {"secondary_fetch_applied": False, "shards_loaded": [], "added_count": 0}
    if len(base_refs) >= min_primary or max_extra <= 0:
        return base_refs, meta

    shards: dict[str, dict[str, Any]] = {}
    for row in bloom_index.get("chapter_shards") or []:
        if isinstance(row, dict) and row.get("shard_id"):
            shards[str(row["shard_id"])] = row

    if not shards:
        return base_refs, meta

    books = _books_from_query(query)
    chapters = _chapters_from_query(query)
    seen = set(base_refs)
    out = list(base_refs)
    added = 0

    for shard_id, row in shards.items():
        if added >= max_extra:
            break
        book = str(row.get("book") or "")
        chap = int(row.get("chapter") or 0)
        if books and book not in books:
            continue
        if chapters and chap not in chapters:
            continue
        refs = row.get("verse_refs") or []
        if not refs:
            shard_path = bloom_index.get("shard_dir_relative")
            if shard_path:
                full = ROOT / str(shard_path).replace("/", "\\") / f"{shard_id}.json"
                if full.is_file():
                    shard_doc = json.loads(full.read_text(encoding="utf-8-sig"))
                    refs = shard_doc.get("verse_refs") or []
        if not refs:
            continue
        meta["shards_loaded"].append(shard_id)
        for ref in refs:
            if ref in seen:
                continue
            seen.add(ref)
            out.append(ref)
            added += 1
            if added >= max_extra:
                break

    if added:
        meta["secondary_fetch_applied"] = True
        meta["added_count"] = added
    return out, meta
