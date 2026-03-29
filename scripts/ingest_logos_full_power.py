#!/usr/bin/env python3
"""
Ingest apocrypha from Sefaria HTTP API into Strict-JSONL pipeline inputs.

Writes:
  - data/logos/manuscripts/apocrypha_std.jsonl  (source, verse_id, text per line)

DSS (dss_parsed.jsonl):
  Sefaria does not expose reliable machine-parseable DSS scrolls under the same
  slugs as printed Bibles; ETCBC/HF pipelines are separate. This script creates
  an empty dss_parsed.jsonl if missing so downstream paths exist without fabricating DSS.

Post-run (repo root):
  py scripts/backfill_logos_manuscript_hashes.py
  py scripts/verify_logos_manuscripts_integrity.py --strict
  py scripts/build_logos_dss_manifest.py
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


# Sefaria index slugs (verified). Wisdom uses "Wisdom", not "Wisdom_of_Solomon".
APOCRYPHA_SLUGS: tuple[str, ...] = (
    "Sirach",
    "Wisdom",
    "Tobit",
    "Judith",
    "First_Maccabees",
    "The_Book_of_Maccabees_II",
)

USER_AGENT = "MKM-LogosIngest/1.0 (+https://example.invalid/contact)"


def http_get_json(url: str, timeout: int = 45) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def fetch_with_retries(
    url: str,
    *,
    max_retries: int,
    backoff_base: float,
    timeout: int,
) -> dict[str, Any]:
    last_err: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return http_get_json(url, timeout=timeout)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as e:
            last_err = e
            code = getattr(e, "code", None)
            if isinstance(e, urllib.error.HTTPError) and code == 404:
                raise
            if attempt >= max_retries:
                break
            sleep_s = backoff_base * (2**attempt) + random.random() * 0.15
            time.sleep(sleep_s)
    assert last_err is not None
    raise last_err


def chapter_count_from_index(data: dict[str, Any]) -> int:
    lengths = data.get("lengths")
    if isinstance(lengths, list) and lengths:
        return int(lengths[0])
    schema = data.get("schema")
    if isinstance(schema, dict):
        sl = schema.get("lengths")
        if isinstance(sl, list) and sl:
            return int(sl[0])
    raise ValueError("index: could not determine chapter count (no lengths)")


def normalize_verse_text(v: Any) -> str:
    """Turn a Sefaria verse cell into a single display string (English or Hebrew)."""
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, list):
        parts: list[str] = []
        for item in v:
            s = normalize_verse_text(item)
            if s:
                parts.append(s)
        return " ".join(parts).strip()
    if isinstance(v, dict):
        return json.dumps(v, ensure_ascii=False).strip()
    return str(v).strip()


def _verse_list_field(data: dict[str, Any], key: str) -> list[Any]:
    raw = data.get(key)
    return raw if isinstance(raw, list) else []


def fetch_chapter_verses(
    book_slug: str,
    chapter: int,
    *,
    max_retries: int,
    backoff_base: float,
    timeout: int,
) -> list[str]:
    ref = f"{book_slug}.{chapter}"
    q = urllib.parse.urlencode({"context": "0"})
    url = f"https://www.sefaria.org/api/texts/{urllib.parse.quote(ref)}?{q}"
    data = fetch_with_retries(url, max_retries=max_retries, backoff_base=backoff_base, timeout=timeout)
    cells_en = _verse_list_field(data, "text")
    cells_he = _verse_list_field(data, "he")
    lg = data.get("length")
    n_hint = int(lg) if isinstance(lg, int) and lg > 0 else 0
    n = max(len(cells_en), len(cells_he), n_hint)
    if n == 0:
        return []
    out: list[str] = []
    for i in range(n):
        t_en = normalize_verse_text(cells_en[i] if i < len(cells_en) else None)
        t_he = normalize_verse_text(cells_he[i] if i < len(cells_he) else None)
        out.append(t_en if t_en else t_he)
    return out


def ingest_apocrypha(
    out_path: Path,
    *,
    book_slugs: tuple[str, ...],
    delay_s: float,
    max_retries: int,
    backoff_base: float,
    timeout: int,
    max_books: int | None,
    max_chapters_total: int | None,
    dry_run: bool,
) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []
    chapters_done = 0

    books_iter = list(book_slugs)
    if max_books is not None:
        books_iter = books_iter[: max_books]

    for slug in books_iter:
        idx_url = f"https://www.sefaria.org/api/v2/index/{urllib.parse.quote(slug)}"
        idx = fetch_with_retries(idx_url, max_retries=max_retries, backoff_base=backoff_base, timeout=timeout)
        n_ch = chapter_count_from_index(idx)
        print(f"[index] {slug}: {n_ch} chapter(s)", flush=True)

        for ch in range(1, n_ch + 1):
            if max_chapters_total is not None and chapters_done >= max_chapters_total:
                break
            if dry_run and chapters_done >= 1:
                break
            time.sleep(delay_s)
            verses = fetch_chapter_verses(
                slug, ch, max_retries=max_retries, backoff_base=backoff_base, timeout=timeout
            )
            for vi, t in enumerate(verses, start=1):
                if not t.strip():
                    continue
                vid = f"apo:{slug}:{ch}:{vi}"
                rows.append({"source": "Sefaria", "verse_id": vid, "text": t})
            chapters_done += 1
            print(f"  {slug}.{ch}: {len(verses)} cell(s)", flush=True)

        if max_chapters_total is not None and chapters_done >= max_chapters_total:
            break

    with out_path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Wrote {out_path} ({len(rows)} row(s))", flush=True)
    return len(rows)


def ensure_empty_dss(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file() and path.stat().st_size > 0:
        return
    path.write_text("", encoding="utf-8")
    print(f"Ensured empty DSS placeholder: {path}", flush=True)


def main() -> int:
    root = repo_root()
    ap = argparse.ArgumentParser(description="Sefaria apocrypha -> manuscript JSONL (pre-hash)")
    ap.add_argument(
        "--out-apo",
        type=Path,
        default=root / "data/logos/manuscripts/apocrypha_std.jsonl",
        help="Output JSONL for apocrypha",
    )
    ap.add_argument(
        "--out-dss",
        type=Path,
        default=root / "data/logos/manuscripts/dss_parsed.jsonl",
        help="DSS placeholder path (empty file if missing/empty)",
    )
    ap.add_argument("--delay", type=float, default=0.35, help="Seconds between chapter GETs")
    ap.add_argument("--max-retries", type=int, default=4)
    ap.add_argument("--backoff-base", type=float, default=0.5)
    ap.add_argument("--timeout", type=int, default=45)
    ap.add_argument("--max-books", type=int, default=None)
    ap.add_argument("--max-chapters", type=int, default=None, help="Stop after N chapters fetched (all books)")
    ap.add_argument("--dry-run", action="store_true", help="Fetch only first chapter of first book")
    ap.add_argument(
        "--books",
        type=str,
        default="",
        help="Comma-separated Sefaria slugs (default: built-in apocrypha list)",
    )
    args = ap.parse_args()

    if args.books.strip():
        slugs = tuple(s.strip() for s in args.books.split(",") if s.strip())
    else:
        slugs = APOCRYPHA_SLUGS

    mc = 1 if args.dry_run else args.max_chapters

    try:
        n = ingest_apocrypha(
            args.out_apo,
            book_slugs=slugs,
            delay_s=args.delay,
            max_retries=args.max_retries,
            backoff_base=args.backoff_base,
            timeout=args.timeout,
            max_books=args.max_books,
            max_chapters_total=mc,
            dry_run=args.dry_run,
        )
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    ensure_empty_dss(args.out_dss)
    print(f"OK: apocrypha rows written: {n}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
