#!/usr/bin/env python3
"""Canon book coverage heatmap — verses, themes, citations, deep-push depth [HYPO]."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VERSE_JSONL = ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_v1_latest.jsonl"
PRESETS = ROOT / "docs/final/artifacts/LOGOS_TRACK_B_THEME_PRESETS_V1.json"
ART = ROOT / "docs/final/artifacts"
OUT_DEFAULT = ROOT / "reports/logos_canon_book_coverage_heatmap_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def _book_from_vid(vid: str) -> str:
    m = re.match(r"^([A-Za-z0-9]+)\.", (vid or "").strip())
    return m.group(1) if m else ""


def _count_verses_by_book(jsonl: Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    if not jsonl.is_file():
        return counts
    with jsonl.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("schema") != "logos_verse_4d_v1":
                continue
            book = _book_from_vid(str(row.get("verse_id") or ""))
            if book:
                counts[book] += 1
    return counts


def _theme_books(presets: dict[str, Any]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = defaultdict(list)
    for tid, theme in (presets.get("themes") or {}).items():
        prefix = str(theme.get("verse_prefix") or "")
        book = _book_from_vid(prefix)
        if book:
            out[book].append(tid)
    return dict(out)


def _path_gate_by_book(path_gate: Path) -> Counter[str]:
    freq: Counter[str] = Counter()
    gate = _load(path_gate)
    for chk in gate.get("checks") or []:
        for c in (chk.get("citations") or []):
            book = _book_from_vid(str(c))
            if book:
                freq[book] += 1
    return freq


def _deep_push_by_book(theme_ids: list[str]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for tid in theme_ids:
        locked = ART / f"logos_deep_research_distill_{tid}_citation_lock_latest.json"
        distill = _load(locked) if locked.is_file() else _load(ART / f"logos_deep_research_distill_{tid}_latest.json")
        books: Counter[str] = Counter()
        for ref in distill.get("evidence_refs") or []:
            if isinstance(ref, dict):
                book = _book_from_vid(str(ref.get("verse_id") or ""))
                if book:
                    books[book] += 1
        lock = distill.get("citation_lock") or {}
        locked_count = int(lock.get("locked_count") or 0)
        evidence_n = len(distill.get("evidence_refs") or [])
        out[tid] = {
            "evidence_ref_count": evidence_n,
            "citation_locked": locked_count,
            "citation_valid": locked_count >= 3 and locked_count >= max(1, evidence_n),
            "books": dict(books),
        }
    return out


def build(
    *,
    verse_jsonl: Path,
    presets_path: Path,
    path_gate: Path,
    key_v2: Path,
) -> dict[str, Any]:
    presets = _load(presets_path)
    theme_ids = list((presets.get("themes") or {}).keys())
    verse_by_book = _count_verses_by_book(verse_jsonl)
    theme_by_book = _theme_books(presets)
    cite_by_book = _path_gate_by_book(path_gate)
    deep = _deep_push_by_book(theme_ids)

    key_v2_doc = _load(key_v2)
    key_by_book: Counter[str] = Counter()
    for row in key_v2_doc.get("rows") or []:
        book = _book_from_vid(str(row.get("verse_id") or ""))
        if book:
            key_by_book[book] += 1

    deep_cited_books: set[str] = set()
    for row in deep.values():
        deep_cited_books.update((row.get("books") or {}).keys())

    books = sorted(set(verse_by_book) | set(theme_by_book) | set(cite_by_book) | deep_cited_books)
    heatmap: list[dict[str, Any]] = []
    for book in books:
        themes = theme_by_book.get(book) or []
        deep_ok = sum(
            1
            for t in themes
            if (deep.get(t) or {}).get("citation_valid") is True
            or int((deep.get(t) or {}).get("citation_locked") or 0) > 0
        )
        heatmap.append(
            {
                "book": book,
                "verse_count": verse_by_book.get(book, 0),
                "theme_count": len(themes),
                "theme_ids": themes,
                "path_gate_citations": cite_by_book.get(book, 0),
                "key_verse_v2_rows": key_by_book.get(book, 0),
                "deep_push_themes_with_evidence": deep_ok,
                "depth_tier": (
                    "deep_validated"
                    if deep_ok and themes
                    else "themed"
                    if themes
                    else "corpus_only"
                ),
            }
        )

    deep_valid = sum(1 for t in theme_ids if (deep.get(t) or {}).get("citation_valid") is True)
    deep_locked = sum(1 for t in theme_ids if int((deep.get(t) or {}).get("citation_locked") or 0) > 0)

    return {
        "schema": "logos_canon_book_coverage_heatmap_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "track_wall": {"track_a_bridge": False, "ms_headline_merge_forbidden": True},
        "summary": {
            "book_count": len(books),
            "total_verses": sum(verse_by_book.values()),
            "theme_preset_count": len(theme_ids),
            "deep_push_citation_valid_themes": deep_valid,
            "deep_push_locked_themes": deep_locked,
            "books_with_deep_theme": sum(1 for h in heatmap if h["depth_tier"] == "deep_validated"),
            "books_with_theme_only": sum(1 for h in heatmap if h["depth_tier"] == "themed"),
        },
        "deep_push_by_theme": deep,
        "heatmap": heatmap,
        "reproduce": "py scripts/build_logos_canon_book_coverage_heatmap_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verse-jsonl", type=Path, default=VERSE_JSONL)
    ap.add_argument("--presets", type=Path, default=PRESETS)
    ap.add_argument("--path-gate", type=Path, default=ROOT / "reports/logos_path_verification_gate_v1_latest.json")
    ap.add_argument("--key-v2", type=Path, default=ROOT / "reports/verse_metadata_shadow_v2_latest.json")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    doc = build(
        verse_jsonl=args.verse_jsonl,
        presets_path=args.presets,
        path_gate=args.path_gate,
        key_v2=args.key_v2,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sm = doc["summary"]
    print(
        json.dumps(
            {
                "ok": sm["book_count"] > 0,
                "book_count": sm["book_count"],
                "deep_valid": sm["deep_push_citation_valid_themes"],
                "out": str(args.out.relative_to(ROOT)),
            },
            ensure_ascii=False,
        )
    )
    return 0 if sm["book_count"] > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
