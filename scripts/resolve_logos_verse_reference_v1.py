#!/usr/bin/env python3
"""Resolve human / English / Korean Bible references to canonical Logos verse_id (e.g. Jhn.19.34).

Track L (Logos Hermeneutics): deterministic lookup rail — not ANN semantic search.
Book IDs align with ingest_logos_gap_original_text_v1.MORPHGNT_SUFFIX_TO_BOOK canon names.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSONL = ROOT / "data/logos/verse_decoded_v2_single_anchor_v1.jsonl"

# Longer keys first when building regex (1john before john).
BOOK_ALIAS_TO_CANON: dict[str, str] = {
    "1 john": "1John",
    "2 john": "2John",
    "3 john": "3John",
    "1john": "1John",
    "2john": "2John",
    "3john": "3John",
    "1jn": "1John",
    "2jn": "2John",
    "3jn": "3John",
    "요한일서": "1John",
    "요한이서": "2John",
    "요한삼서": "3John",
    "요일": "1John",
    "요이": "2John",
    "요삼": "3John",
    "john": "Jhn",
    "jn": "Jhn",
    "jhn": "Jhn",
    "요한복음": "Jhn",
    "복음요한": "Jhn",
    "요한": "Jhn",
    "matthew": "Matt",
    "matt": "Matt",
    "mt": "Matt",
    "마태복음": "Matt",
    "마태": "Matt",
    "mark": "Mark",
    "mk": "Mark",
    "마가복음": "Mark",
    "마가": "Mark",
    "luke": "Luke",
    "lk": "Luke",
    "누가복음": "Luke",
    "누가": "Luke",
    "acts": "Acts",
    "ac": "Acts",
    "사도행전": "Acts",
    "romans": "Rom",
    "rom": "Rom",
    "로마서": "Rom",
}

CANON_DOT_RE = re.compile(
    r"\b(?P<book>[1-3]?[A-Za-z]+)\s*\.\s*(?P<ch>\d{1,3})\s*\.\s*(?P<vs>\d{1,3})\b"
)

# English UI labels that differ from Logos verse_id book prefix.
CANON_DOT_NORMALIZE: dict[str, str] = {
    "John": "Jhn",
    "Jn": "Jhn",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _human_alias_re() -> re.Pattern[str]:
    keys = sorted(BOOK_ALIAS_TO_CANON.keys(), key=len, reverse=True)
    alt = "|".join(re.escape(k) for k in keys)
    return re.compile(
        rf"(?P<alias>{alt})\s*(?P<ch>\d{{1,3}})\s*[:：]\s*(?P<vs>\d{{1,3}})",
        re.IGNORECASE,
    )


_HUMAN_RE = _human_alias_re()


@dataclass(frozen=True)
class ResolvedVerseRef:
    raw_span: str
    verse_id: str
    book_canon: str
    chapter: int
    verse: int
    resolve_via: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_span": self.raw_span,
            "verse_id": self.verse_id,
            "book_canon": self.book_canon,
            "chapter": self.chapter,
            "verse": self.verse,
            "resolve_via": self.resolve_via,
        }


def _make_ref(book: str, ch: int, vs: int, raw: str, via: str) -> ResolvedVerseRef:
    vid = f"{book}.{ch}.{vs}"
    return ResolvedVerseRef(raw_span=raw, verse_id=vid, book_canon=book, chapter=ch, verse=vs, resolve_via=via)


def resolve_verse_references_in_text(text: str) -> list[ResolvedVerseRef]:
    """Return de-duplicated verse refs found in *text* (order preserved)."""
    seen: set[str] = set()
    out: list[ResolvedVerseRef] = []

    def add(ref: ResolvedVerseRef) -> None:
        if ref.verse_id not in seen:
            seen.add(ref.verse_id)
            out.append(ref)

    for m in CANON_DOT_RE.finditer(text):
        book = m.group("book")
        if book[0].isdigit():
            canon = book
        else:
            canon = book[:1].upper() + book[1:] if book else book
        canon = CANON_DOT_NORMALIZE.get(canon, canon)
        add(
            _make_ref(
                canon,
                int(m.group("ch")),
                int(m.group("vs")),
                m.group(0),
                "canon_dot",
            )
        )

    for m in _HUMAN_RE.finditer(text):
        alias = m.group("alias").lower()
        canon = BOOK_ALIAS_TO_CANON.get(alias) or BOOK_ALIAS_TO_CANON.get(m.group("alias"))
        if not canon:
            key = alias.replace(" ", "")
            canon = BOOK_ALIAS_TO_CANON.get(key)
        if not canon:
            continue
        add(
            _make_ref(
                canon,
                int(m.group("ch")),
                int(m.group("vs")),
                m.group(0),
                "alias_colon",
            )
        )

    return out


def load_verse_row(verse_id: str, jsonl_path: Path = DEFAULT_JSONL) -> dict[str, Any] | None:
    """Scan JSONL for a single verse_id (streaming; OK for one-off L0 / pilot)."""
    if not jsonl_path.is_file():
        return None
    needle = f'"verse_id": "{verse_id}"'
    with jsonl_path.open(encoding="utf-8") as f:
        for line in f:
            if needle in line:
                return json.loads(line)
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("text", nargs="?", help="Reference text (e.g. 'John 19:34')")
    ap.add_argument("--text", dest="text_flag", help="Same as positional text")
    ap.add_argument(
        "--fetch-row",
        action="store_true",
        help="Load matching row from verse_decoded JSONL when present",
    )
    ap.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    ap.add_argument("-o", "--out", type=Path, help="Write JSON result")
    args = ap.parse_args()

    raw = (args.text_flag or args.text or "").strip()
    if not raw:
        print("Provide reference text.", file=sys.stderr)
        return 1

    refs = resolve_verse_references_in_text(raw)
    doc: dict[str, Any] = {
        "schema": "logos_verse_reference_resolve_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "track": "L",
        "research_only": True,
        "non_gating_ack": True,
        "input_text": raw,
        "resolved": [r.to_dict() for r in refs],
        "primary_verse_id": refs[0].verse_id if refs else None,
    }
    if args.fetch_row and refs:
        rows = []
        for r in refs:
            row = load_verse_row(r.verse_id, args.jsonl)
            rows.append(
                {
                    "verse_id": r.verse_id,
                    "found": row is not None,
                    "row": row,
                }
            )
        doc["corpus_rows"] = rows

    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
        print(str(args.out.resolve()))
    else:
        print(payload, end="")
    return 0 if refs else 2


if __name__ == "__main__":
    raise SystemExit(main())
