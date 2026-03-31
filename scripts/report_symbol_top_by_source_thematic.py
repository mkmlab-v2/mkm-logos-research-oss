#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.8, K:0.4, M:0.6}
# Balance: 90
# Purpose: Reproducible thematic top symbol extraction by source lane.
# Keywords: symbol, btrack, dss, apocrypha, stopword, report
"""Build reproducible thematic top-K symbols by DSS/Apocrypha source split."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "symbol_candidates_curated_latest.jsonl"
DEFAULT_STOPWORDS = ROOT / "data" / "logos" / "btrack_pilot" / "gates" / "symbol_stopwords_v1.json"
DEFAULT_OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "symbol_top50_by_source_thematic_latest.json"


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                yield obj


def _bucket(row: dict[str, Any]) -> str:
    mix = row.get("source_mix", {})
    if not isinstance(mix, dict):
        mix = {}
    dss = int(mix.get("dss", 0) or 0)
    apo = int(mix.get("apocrypha", 0) or 0)
    if dss > 0 and apo == 0:
        return "dss_only"
    if apo > 0 and dss == 0:
        return "apocrypha_only"
    if dss > 0 and apo > 0:
        return "mixed"
    return "unknown"


def _load_stopwords(path: Path) -> tuple[set[str], set[str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    lang_sets = data.get("language_sets", {})
    if not isinstance(lang_sets, dict):
        return set(), set()
    he = {str(x).strip().lower() for x in lang_sets.get("hebrew", []) if str(x).strip()}
    en = {str(x).strip().lower() for x in lang_sets.get("english", []) if str(x).strip()}
    return he, en


def _is_stopword_symbol(symbol: str, he: set[str], en: set[str]) -> bool:
    s = symbol.strip().lower()
    if not s:
        return True
    parts = s.split()
    if all(p in he for p in parts):
        return True
    if all(p in en for p in parts):
        return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description="Report thematic top symbols by source split")
    ap.add_argument("--input-jsonl", default=str(DEFAULT_INPUT))
    ap.add_argument("--stopwords-json", default=str(DEFAULT_STOPWORDS))
    ap.add_argument("--top-k", type=int, default=50)
    ap.add_argument("--out-json", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    in_path = _abs(args.input_jsonl)
    stop_path = _abs(args.stopwords_json)
    out_path = _abs(args.out_json)
    if not in_path.is_file():
        print(f"ERROR: missing input: {in_path}")
        return 2
    if not stop_path.is_file():
        print(f"ERROR: missing stopwords: {stop_path}")
        return 2

    he_stop, en_stop = _load_stopwords(stop_path)
    rows = list(_iter_jsonl(in_path))
    kept = [
        row
        for row in rows
        if not _is_stopword_symbol(str(row.get("symbol", "")), he_stop, en_stop)
    ]

    lanes: dict[str, list[dict[str, Any]]] = {}
    for lane in ("dss_only", "mixed", "apocrypha_only"):
        picked = [r for r in kept if _bucket(r) == lane]
        picked.sort(
            key=lambda r: (
                float(r.get("score_tfidf_like", 0.0) or 0.0),
                int(r.get("term_freq", 0) or 0),
            ),
            reverse=True,
        )
        lanes[lane] = picked[: args.top_k]

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = {
        "schema": "btrack_symbol_top_by_source_thematic_v1",
        "generated_at_utc": ts,
        "generated_from": str(in_path),
        "stopwords_file": str(stop_path),
        "counts": {
            "raw": len(rows),
            "filtered_in": len(kept),
            "dss_only": len(lanes["dss_only"]),
            "mixed": len(lanes["mixed"]),
            "apocrypha_only": len(lanes["apocrypha_only"]),
        },
        "top_k": args.top_k,
        "top": lanes,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("OK: thematic symbol top report generated")
    print(f"out={out_path}")
    print(f"counts={out['counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
