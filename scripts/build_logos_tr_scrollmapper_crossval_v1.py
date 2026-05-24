#!/usr/bin/env python3
"""Cross-validate honza TR ingest vs scrollmapper/bible_databases TR.json (B-track)."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.logos_greek_text_normalize_v1 import normalize_greek_lexical  # noqa: E402
from scripts.logos_tr_scrollmapper_to_mt_verse_v1 import scrollmapper_verse_to_id  # noqa: E402

SCROLLMAPPER_TR_URL = (
    "https://raw.githubusercontent.com/scrollmapper/bible_databases/master/formats/json/TR.json"
)
DEFAULT_CACHE = ROOT / "data/logos/manuscripts/cache/scrollmapper_TR.json"
DEFAULT_HONZA_NT = ROOT / "data/logos/manuscripts/tr_greek_by_verse_v1.full_nt.jsonl"
DEFAULT_POLICY = ROOT / "data/logos/logos_gap_mt_only_policy_v1.jsonl"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_tr_scrollmapper_crossval_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    resolved = path.resolve()
    root = ROOT.resolve()
    if resolved == root or root in resolved.parents:
        return str(resolved.relative_to(root)).replace("\\", "/")
    return str(resolved.as_posix())


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "MKM-Logos-TR-Crossval/1.0"})
    with urllib.request.urlopen(req, timeout=600) as resp:  # noqa: S310
        dest.write_bytes(resp.read())


def _load_honza_index(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        vid = str(row.get("verse_id") or "").strip()
        greek = str(row.get("greek_text") or "").strip()
        if vid and greek:
            out[vid] = greek
    return out


def _load_policy_ids(path: Path) -> set[str]:
    ids: set[str] = set()
    if not path.is_file():
        return ids
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            ids.add(str(json.loads(line)["verse_id"]))
    return ids


def _iter_scrollmapper_nt(cache_path: Path) -> dict[str, str]:
    raw = json.loads(cache_path.read_text(encoding="utf-8"))
    books = raw.get("books") if isinstance(raw, dict) else None
    if not isinstance(books, list):
        raise ValueError("unexpected scrollmapper TR.json shape")
    index: dict[str, str] = {}
    unmapped_books: set[str] = set()
    for book in books:
        name = str(book.get("name") or "")
        if name not in {
            "Matthew",
            "Mark",
            "Luke",
            "John",
            "Acts",
            "Romans",
            "I Corinthians",
            "II Corinthians",
            "Galatians",
            "Ephesians",
            "Philippians",
            "Colossians",
            "I Thessalonians",
            "II Thessalonians",
            "I Timothy",
            "II Timothy",
            "Titus",
            "Philemon",
            "Hebrews",
            "James",
            "I Peter",
            "II Peter",
            "I John",
            "II John",
            "III John",
            "Jude",
            "Revelation of John",
        }:
            continue
        for ch in book.get("chapters") or []:
            try:
                ch_n = int(ch["chapter"])
            except (KeyError, TypeError, ValueError):
                continue
            for v in ch.get("verses") or []:
                try:
                    vs_n = int(v["verse"])
                except (KeyError, TypeError, ValueError):
                    continue
                text = str(v.get("text") or "").strip()
                if not text:
                    continue
                vid = scrollmapper_verse_to_id(name, ch_n, vs_n)
                if not vid:
                    unmapped_books.add(name)
                    continue
                index[vid] = text
    if unmapped_books:
        raise ValueError(f"unmapped scrollmapper NT books: {sorted(unmapped_books)}")
    return index


def _compare_pair(vid: str, honza: str, scroll: str) -> dict[str, Any]:
    hn = normalize_greek_lexical(honza)
    sn = normalize_greek_lexical(scroll)
    return {
        "verse_id": vid,
        "match_normalized": hn == sn,
        "honza_preview": honza[:80] + ("…" if len(honza) > 80 else ""),
        "scrollmapper_preview": scroll[:80] + ("…" if len(scroll) > 80 else ""),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--honza-jsonl", type=Path, default=DEFAULT_HONZA_NT)
    ap.add_argument("--cache-path", type=Path, default=DEFAULT_CACHE)
    ap.add_argument("--url", default=SCROLLMAPPER_TR_URL)
    ap.add_argument("--skip-download", action="store_true")
    ap.add_argument("--policy-jsonl", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--scope",
        choices=("gap_only", "full_nt_overlap"),
        default="full_nt_overlap",
        help="gap_only = 15 MT-only policy verses; full_nt_overlap = all shared verse_ids",
    )
    args = ap.parse_args()

    if not args.honza_jsonl.is_file():
        print(f"missing honza ingest: {args.honza_jsonl}", file=sys.stderr)
        return 2

    if not args.skip_download and not args.cache_path.is_file():
        try:
            _download(args.url, args.cache_path)
        except urllib.error.URLError as exc:
            print(f"download failed: {exc}", file=sys.stderr)
            return 2

    if not args.cache_path.is_file():
        print(f"missing scrollmapper cache: {args.cache_path}", file=sys.stderr)
        return 2

    honza = _load_honza_index(args.honza_jsonl)
    scroll = _iter_scrollmapper_nt(args.cache_path)
    policy_ids = _load_policy_ids(args.policy_jsonl)

    if args.scope == "gap_only":
        target_ids = sorted(policy_ids & set(honza) & set(scroll))
    else:
        target_ids = sorted(set(honza) & set(scroll))

    compared: list[dict[str, Any]] = []
    matches = 0
    mismatches: list[dict[str, Any]] = []
    for vid in target_ids:
        row = _compare_pair(vid, honza[vid], scroll[vid])
        compared.append(row)
        if row["match_normalized"]:
            matches += 1
        else:
            mismatches.append(row)

    gap_rows = [_compare_pair(vid, honza[vid], scroll[vid]) for vid in sorted(policy_ids) if vid in honza and vid in scroll]
    gap_matches = sum(1 for r in gap_rows if r["match_normalized"])

    doc = {
        "schema": "logos_tr_scrollmapper_crossval_v1",
        "version": "1.0.0",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "source_track": "B_ext",
        "sources": {
            "primary": "honza/textus-receptus gnt.flat.json",
            "secondary": "scrollmapper/bible_databases formats/json/TR.json",
            "honza_jsonl": _rel(args.honza_jsonl),
            "scrollmapper_cache": _rel(args.cache_path),
        },
        "normalization": "strip_accents_lower_whitespace_punct",
        "scope": args.scope,
        "counts": {
            "honza_rows": len(honza),
            "scrollmapper_nt_rows": len(scroll),
            "overlap_compared": len(compared),
            "normalized_exact_match": matches,
            "normalized_mismatch": len(mismatches),
            "gap_policy_verses": len(policy_ids),
            "gap_overlap_compared": len(gap_rows),
            "gap_normalized_exact_match": gap_matches,
        },
        "gate": {
            "gap_15_of_15_normalized_match": gap_matches == len(gap_rows) and len(gap_rows) == len(policy_ids),
            "full_nt_match_rate": round(matches / len(compared), 6) if compared else None,
        },
        "mismatch_samples": mismatches[:25],
        "gap_results": gap_rows,
        "track_wall": {
            "a_track_auto_promotion": False,
            "ready_for_external_send": False,
            "note": "Second-source agreement only; does not alter complete JSONL or MT-only stubs.",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote {args.output} overlap={len(compared)} match={matches} "
        f"gap={gap_matches}/{len(gap_rows)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
