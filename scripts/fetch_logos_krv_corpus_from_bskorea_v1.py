#!/usr/bin/env python3
"""Fetch KRV (개역개정 / GAE) verse corpus from bskorea.or.kr → krv_verses_v1.jsonl.

Research-only ingest for Logos citation shard (P1 bible_full). Resumable progress file.

  py scripts/fetch_logos_krv_corpus_from_bskorea_v1.py --dry-run --max-chapters 2
  py scripts/fetch_logos_krv_corpus_from_bskorea_v1.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref, is_canonical_verse_ref

DEFAULT_OUT = ROOT / "data/logos/krv_verses_v1.jsonl"
DEFAULT_PROGRESS = ROOT / "reports/logos_krv_bskorea_fetch_progress_v1.json"
CORPUS_MANIFEST = ROOT / "docs/final/artifacts/logos_corpus_manifest_v1_latest.json"
BASE_URL = "https://www.bskorea.or.kr/bible/korbibReadpage.php"

# bskorea book code → Logos book id (must match verse_4pipeline)
BSK_BOOK_TO_LOGOS: dict[str, str] = {
    "gen": "Gen",
    "exo": "Exod",
    "lev": "Lev",
    "num": "Num",
    "deu": "Deut",
    "jos": "Josh",
    "jdg": "Judg",
    "rut": "Ruth",
    "1sa": "1Sam",
    "2sa": "2Sam",
    "1ki": "1Kgs",
    "2ki": "2Kgs",
    "1ch": "1Chr",
    "2ch": "2Chr",
    "ezr": "Ezra",
    "neh": "Neh",
    "est": "Esth",
    "job": "Job",
    "psa": "Ps",
    "pro": "Prov",
    "ecc": "Eccl",
    "sng": "Song",
    "isa": "Isa",
    "jer": "Jer",
    "lam": "Lam",
    "ezk": "Ezek",
    "dan": "Dan",
    "hos": "Hos",
    "joe": "Joel",
    "jol": "Joel",
    "amo": "Amos",
    "oba": "Obad",
    "jon": "Jonah",
    "jnh": "Jonah",
    "mic": "Mic",
    "nah": "Nah",
    "nam": "Nah",
    "hab": "Hab",
    "zep": "Zeph",
    "hag": "Hag",
    "zec": "Zech",
    "mal": "Mal",
    "mat": "Matt",
    "mrk": "Mark",
    "luk": "Luke",
    "jhn": "Jhn",
    "act": "Acts",
    "rom": "Rom",
    "1co": "1Cor",
    "2co": "2Cor",
    "gal": "Gal",
    "eph": "Eph",
    "php": "Phil",
    "col": "Col",
    "1th": "1Thess",
    "2th": "2Thess",
    "1ti": "1Tim",
    "2ti": "2Tim",
    "tit": "Titus",
    "phm": "Phlm",
    "heb": "Heb",
    "jas": "Jas",
    "1pe": "1Pet",
    "2pe": "2Pet",
    "1jn": "1John",
    "2jn": "2John",
    "3jn": "3John",
    "jud": "Jude",
    "rev": "Rev",
}

LOGOS_TO_BSK: dict[str, str] = {v: k for k, v in BSK_BOOK_TO_LOGOS.items()}
# Prefer working bskorea book codes (jol/jnh/nam over legacy joe/jon/nah shells)
LOGOS_TO_BSK["Joel"] = "jol"
LOGOS_TO_BSK["Jonah"] = "jnh"
LOGOS_TO_BSK["Nah"] = "nam"
LOGOS_TO_BSK.setdefault("John", "jhn")
LOGOS_TO_BSK.setdefault("Jhn", "jhn")

VERSE_CHUNK_RE = re.compile(
    r'<span(?: style="color:#376BCB;")?><span class="number">(\d+)&nbsp;&nbsp;&nbsp;</span>(.*?)</span><br',
    re.DOTALL,
)
TAG_RE = re.compile(r"<[^>]+>")


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_canon_chapters() -> list[tuple[str, int, list[int]]]:
    """Return [(bsk_book, chapter, [verse_nums...]), ...] from verse_4pipeline manifest."""
    manifest = json.loads(CORPUS_MANIFEST.read_text(encoding="utf-8-sig"))
    rel = manifest.get("input_path", "data/logos/verse_4pipeline_full_31102.json")
    corpus_path = ROOT / str(rel).replace("/", "\\")
    data = json.loads(corpus_path.read_text(encoding="utf-8-sig"))
    by_ch: dict[tuple[str, int], set[int]] = defaultdict(set)
    for row in data:
        vid = str(row.get("verse_id") or "").strip()
        if not vid:
            continue
        vid = canonical_verse_ref(vid)
        m = re.match(r"^([A-Za-z0-9_]+)\.(\d+)\.(\d+)$", vid)
        if not m:
            continue
        book = m.group(1)
        bsk = LOGOS_TO_BSK.get(book)
        if not bsk:
            continue
        by_ch[(bsk, int(m.group(2)))].add(int(m.group(3)))
    out: list[tuple[str, int, list[int]]] = []
    for (bsk, chap), verses in sorted(by_ch.items(), key=lambda x: (list(BSK_BOOK_TO_LOGOS).index(x[0][0]), x[0][1])):
        out.append((bsk, chap, sorted(verses)))
    return out


def _clean_verse_html(raw: str) -> str:
    s = unescape(TAG_RE.sub("", raw))
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _fetch_chapter(bsk_book: str, chapter: int, *, timeout: int = 45) -> dict[int, str]:
    qs = f"version=GAE&book={bsk_book}&chap={chapter}"
    url = f"{BASE_URL}?{qs}"
    req = urllib.request.Request(url, headers={"User-Agent": "MKM-Logos-Research/1.0 (btrack; citation-shard)"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        html = resp.read().decode("utf-8", "replace")
    verses: dict[int, str] = {}
    for num_s, body in VERSE_CHUNK_RE.findall(html):
        text = _clean_verse_html(body)
        if text:
            verses[int(num_s)] = text
    return verses


def _fetch_verse(bsk_book: str, chapter: int, verse: int, *, timeout: int = 30) -> str:
    qs = f"version=GAE&book={bsk_book}&chap={chapter}&sec={verse}"
    url = f"{BASE_URL}?{qs}"
    req = urllib.request.Request(url, headers={"User-Agent": "MKM-Logos-Research/1.0 (btrack; citation-shard)"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        html = resp.read().decode("utf-8", "replace")
    got = _fetch_chapter(bsk_book, chapter, timeout=timeout) if verse in (0,) else {}
    if verse in got:
        return got[verse]
    for num_s, body in VERSE_CHUNK_RE.findall(html):
        if int(num_s) == verse:
            return _clean_verse_html(body)
    m = re.search(
        rf'<span class="number">{verse}&nbsp;&nbsp;&nbsp;</span>(.*?)</span>',
        html,
        re.DOTALL,
    )
    if m:
        return _clean_verse_html(m.group(1))
    return ""


def _load_existing(out_path: Path) -> dict[str, str]:
    if not out_path.is_file():
        return {}
    refs: dict[str, str] = {}
    for line in out_path.read_text(encoding="utf-8-sig").splitlines():
        s = line.strip()
        if not s:
            continue
        row = json.loads(s)
        ref = row.get("ref") or row.get("verse_id")
        text = row.get("text_ko") or row.get("text")
        if isinstance(ref, str) and isinstance(text, str):
            refs[canonical_verse_ref(ref)] = text.strip()
    return refs


def _write_progress(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--progress", type=Path, default=DEFAULT_PROGRESS)
    ap.add_argument("--sleep-ms", type=int, default=350, help="Delay between chapter requests")
    ap.add_argument("--max-chapters", type=int, default=0, help="0 = all")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--timeout", type=int, default=45)
    ap.add_argument(
        "--refetch-logos-books",
        type=str,
        default="",
        help="Comma-separated Logos books to refetch even if chapter marked done (e.g. John,Ezek,Mark)",
    )
    args = ap.parse_args()

    refetch_logos: set[str] = set()
    if args.refetch_logos_books.strip():
        refetch_logos = {b.strip() for b in args.refetch_logos_books.split(",") if b.strip()}
    refetch_bsk = {LOGOS_TO_BSK[b] for b in refetch_logos if b in LOGOS_TO_BSK}

    chapters = _load_canon_chapters()
    if args.max_chapters > 0:
        chapters = chapters[: args.max_chapters]

    existing = _load_existing(args.out)
    done_keys: set[str] = set()
    if args.progress.is_file():
        try:
            prog = json.loads(args.progress.read_text(encoding="utf-8-sig"))
            done_keys = set(prog.get("completed_chapters") or [])
        except json.JSONDecodeError:
            done_keys = set()

    fetched = 0
    errors: list[str] = []
    for bsk_book, chap, expected_verses in chapters:
        key = f"{bsk_book}:{chap}"
        logos_book = BSK_BOOK_TO_LOGOS.get(bsk_book, "")
        if key in done_keys and bsk_book not in refetch_bsk:
            continue
        logos_book = BSK_BOOK_TO_LOGOS[bsk_book]
        if args.dry_run:
            print(f"[dry-run] would fetch {key} ({logos_book}.{chap}, {len(expected_verses)} verses)")
            continue
        try:
            got = _fetch_chapter(bsk_book, chap, timeout=args.timeout)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            errors.append(f"{key}:{exc}")
            _write_progress(
                args.progress,
                {
                    "schema": "logos_krv_bskorea_fetch_progress_v1",
                    "updated_at_utc": _utc(),
                    "ok": False,
                    "verse_count": len(existing),
                    "completed_chapters": sorted(done_keys),
                    "last_error": str(exc),
                    "errors": errors[-20:],
                },
            )
            print(json.dumps({"ok": False, "error": str(exc), "at": key}, ensure_ascii=False))
            return 1

        for vnum in expected_verses:
            text = got.get(vnum)
            if not text:
                try:
                    text = _fetch_verse(bsk_book, chap, vnum, timeout=args.timeout)
                    if args.sleep_ms > 0:
                        time.sleep(max(80, args.sleep_ms // 2) / 1000.0)
                except (urllib.error.URLError, TimeoutError, OSError):
                    text = ""
            if not text:
                errors.append(f"{key}:missing_v{vnum}")
                continue
            ref = canonical_verse_ref(f"{logos_book}.{chap}.{vnum}")
            existing[ref] = text
            fetched += 1

        done_keys.add(key)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", encoding="utf-8") as fh:
            for ref in sorted(existing.keys(), key=lambda r: (r.split(".")[0], int(r.split(".")[1]), int(r.split(".")[2]))):
                fh.write(json.dumps({"ref": ref, "text_ko": existing[ref]}, ensure_ascii=False) + "\n")

        _write_progress(
            args.progress,
            {
                "schema": "logos_krv_bskorea_fetch_progress_v1",
                "updated_at_utc": _utc(),
                "ok": True,
                "verse_count": len(existing),
                "completed_chapters": sorted(done_keys),
                "total_chapters": len(_load_canon_chapters()),
                "errors": errors[-20:],
            },
        )
        if args.sleep_ms > 0:
            time.sleep(args.sleep_ms / 1000.0)

    print(
        json.dumps(
            {
                "ok": len(errors) == 0 or len(existing) >= 1000,
                "verse_count": len(existing),
                "fetched_this_run": fetched,
                "chapters_done": len(done_keys),
                "out": str(args.out),
                "errors_sample": errors[:5],
            },
            ensure_ascii=False,
        )
    )
    return 0 if len(existing) >= 1000 else 2


if __name__ == "__main__":
    raise SystemExit(main())
