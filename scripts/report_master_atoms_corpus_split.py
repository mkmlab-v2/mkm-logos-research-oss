#!/usr/bin/env python3
"""Summarize master atoms by corpus bucket (source JSONL filename rules).

Reads original_language_master_atoms_latest.jsonl and optionally
master_atoms_lexicon_seed_latest.jsonl to attribute unmatched/ambiguous
Strong's seed rows to corpus buckets.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent.parent

DEFAULT_ATOMS = (
    ROOT / "reports" / "constitution" / "btrack_pilot" / "original_language_master_atoms_latest.jsonl"
)
DEFAULT_OUT = (
    ROOT / "reports" / "constitution" / "btrack_pilot" / "master_atoms_corpus_split_summary_latest.json"
)

# Basename of build inputs -> stable bucket id (MASTER / plan naming).
SOURCE_BASENAME_TO_BUCKET: dict[str, str] = {
    "verse_decoded_v2.jsonl": "canon_decode",
    "dss_parsed_enriched.jsonl": "dss",
    "apocrypha_std.jsonl": "apocrypha",
}


def _iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                yield obj


def _atom_exclusive_pattern(source_files: list[str]) -> tuple[frozenset[str], str]:
    buckets: set[str] = set()
    for name in source_files:
        buckets.add(SOURCE_BASENAME_TO_BUCKET.get(name, "other"))
    if len(buckets) > 1:
        return frozenset(buckets), "mixed_multi_bucket"
    if not buckets:
        return frozenset(), "unknown"
    sole = next(iter(buckets))
    if sole == "other":
        return frozenset(buckets), "other_only"
    return frozenset(buckets), f"{sole}_only"


def main() -> int:
    ap = argparse.ArgumentParser(description="Master atoms corpus bucket report")
    ap.add_argument("--atoms-jsonl", default=str(DEFAULT_ATOMS))
    ap.add_argument("--seed-jsonl", default="", help="Optional lexicon seed JSONL (Strong's rail)")
    ap.add_argument("--out-json", default=str(DEFAULT_OUT))
    ap.add_argument(
        "--stamp",
        action="store_true",
        help="Also write master_atoms_corpus_split_summary_<utc>.json next to out-json",
    )
    args = ap.parse_args()

    atoms_path = Path(args.atoms_jsonl)
    if not atoms_path.is_absolute():
        atoms_path = ROOT / atoms_path
    out_path = Path(args.out_json)
    if not out_path.is_absolute():
        out_path = ROOT / out_path

    if not atoms_path.is_file():
        print(f"ERROR: missing atoms file: {atoms_path}", flush=True)
        return 2

    seed_path: Path | None = None
    if args.seed_jsonl:
        seed_path = Path(args.seed_jsonl)
        if not seed_path.is_absolute():
            seed_path = ROOT / seed_path
        if not seed_path.is_file():
            print(f"ERROR: missing seed file: {seed_path}", flush=True)
            return 2

    by_bucket_presence: Counter[str] = Counter()
    by_exclusive_pattern: Counter[str] = Counter()
    by_lang: dict[str, Counter[str]] = defaultdict(Counter)
    unknown_sources: Counter[str] = Counter()

    seed_match_by_atom: dict[str, str] = {}
    if seed_path is not None:
        for row in _iter_jsonl(seed_path):
            aid = row.get("atom_id")
            if isinstance(aid, str) and aid:
                seed_match_by_atom[aid] = str(row.get("match_method") or "")

    lex_unmatched_by_pattern: Counter[str] = Counter()
    lex_ambiguous_by_pattern: Counter[str] = Counter()

    atoms_total = 0
    for row in _iter_jsonl(atoms_path):
        atoms_total += 1
        sfiles = row.get("source_files") or []
        if not isinstance(sfiles, list):
            sfiles = []
        basenames = [str(x) for x in sfiles]
        for fn in basenames:
            if fn not in SOURCE_BASENAME_TO_BUCKET:
                unknown_sources[fn] += 1
        buckets, pattern = _atom_exclusive_pattern(basenames)
        by_exclusive_pattern[pattern] += 1
        lang = str(row.get("lang") or "unknown")
        by_lang[lang][pattern] += 1
        for b in buckets:
            by_bucket_presence[b] += 1

        aid = row.get("atom_id")
        if isinstance(aid, str) and aid in seed_match_by_atom:
            mm = seed_match_by_atom[aid]
            if mm == "unmatched":
                lex_unmatched_by_pattern[pattern] += 1
            elif mm == "strongs_norm_multi":
                lex_ambiguous_by_pattern[pattern] += 1

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload: dict[str, Any] = {
        "schema": "master_atoms_corpus_split_summary_v1",
        "generated_at_utc": ts,
        "inputs": {
            "atoms": str(atoms_path),
            "source_basename_to_bucket": dict(SOURCE_BASENAME_TO_BUCKET),
        },
        "atoms_total": atoms_total,
        "by_bucket_presence": dict(sorted(by_bucket_presence.items())),
        "by_exclusive_pattern": dict(sorted(by_exclusive_pattern.items())),
        "by_lang_exclusive_pattern": {k: dict(v) for k, v in sorted(by_lang.items())},
    }
    if unknown_sources:
        payload["unknown_source_basenames"] = dict(sorted(unknown_sources.items()))

    if seed_path is not None:
        payload["inputs"]["lexicon_seed_jsonl"] = str(seed_path)
        payload["lexicon_seed_strongs"] = {
            "unmatched_by_exclusive_pattern": dict(sorted(lex_unmatched_by_pattern.items())),
            "ambiguous_by_exclusive_pattern": dict(sorted(lex_ambiguous_by_pattern.items())),
        }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    out_path.write_text(text, encoding="utf-8")
    print(f"OK: wrote {out_path}", flush=True)

    if args.stamp:
        stamped = out_path.with_name(
            f"master_atoms_corpus_split_summary_{ts.replace(':', '').replace('-', '')}.json"
        )
        stamped.write_text(text, encoding="utf-8")
        print(f"OK: wrote {stamped}", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
