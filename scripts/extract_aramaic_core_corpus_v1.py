#!/usr/bin/env python3
"""Extract Biblical Aramaic verses from logos verse_decoded JSONL (B-track core corpus).

Maps standard Hebrew Bible Aramaic portions:
  - Daniel 2:4 through 7:28 (Daniel 2 verse 4 begins Aramaic section)
  - Ezra 4:8–6:18 and Ezra 7:12–26
  - Jeremiah 10:11

verse_id format: ``Book.chapter.verse`` (e.g. ``Dan.2.4``, ``Ezra.5.1``).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterator


def parse_verse_id(verse_id: str) -> tuple[str, int, int] | None:
    """Split ``Book.ch.vs`` into book slug and integers; supports ``1Kin.1.1`` style."""
    verse_id = verse_id.strip()
    parts = verse_id.split(".")
    if len(parts) < 3:
        return None
    try:
        verse = int(parts[-1])
        chapter = int(parts[-2])
    except ValueError:
        return None
    book = ".".join(parts[:-2])
    if not book:
        return None
    return book, chapter, verse


def is_biblical_aramaic_core(book: str, chapter: int, verse: int) -> bool:
    """Return True if (book, chapter, verse) lies in canonical BH Aramaic sections."""
    b = book.casefold()
    if b in ("dan", "daniel"):
        if chapter < 2 or chapter > 7:
            return False
        if chapter == 2:
            return verse >= 4
        return True
    if b in ("jer", "jeremiah"):
        return chapter == 10 and verse == 11
    if b == "ezra":
        if 4 <= chapter <= 6:
            if chapter == 4:
                return verse >= 8
            if chapter == 6:
                return verse <= 18
            return True
        if chapter == 7:
            return 12 <= verse <= 26
        return False
    return False


def row_is_aramaic_core(row: dict[str, Any]) -> bool:
    vid = row.get("verse_id")
    if not isinstance(vid, str) or not vid.strip():
        return False
    parsed = parse_verse_id(vid)
    if parsed is None:
        return False
    book, chapter, verse = parsed
    return is_biblical_aramaic_core(book, chapter, verse)


def iter_aramaic_core_rows(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(obj, dict):
                continue
            if row_is_aramaic_core(obj):
                yield obj


def parse_args() -> argparse.Namespace:
    repo = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser(description="Extract Biblical Aramaic verses from verse JSONL.")
    ap.add_argument("--input-jsonl", type=Path, required=True, help="Source verse_decoded-style JSONL")
    ap.add_argument(
        "--output-jsonl",
        type=Path,
        required=True,
        help="Filtered JSONL (same row shape as input)",
    )
    ap.add_argument(
        "--annotate",
        action="store_true",
        help='Add fields "aramaic_core_v1" and "source_track": "B" on each row (default off).',
    )
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    inp = args.input_jsonl
    out = args.output_jsonl
    if not inp.is_file():
        print(f"FAIL: input not found: {inp}", file=sys.stderr)
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with out.open("w", encoding="utf-8") as wf:
        for row in iter_aramaic_core_rows(inp):
            if args.annotate:
                row = dict(row)
                row["aramaic_core_v1"] = True
                row["source_track"] = "B"
            wf.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    print(f"extract_aramaic_core_corpus_v1: wrote {count} rows -> {out}")
    if count == 0:
        print("WARN: zero Aramaic rows matched; check verse_id format or input corpus.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
