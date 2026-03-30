#!/usr/bin/env python3
"""Build promotion-ready symbol lanes from curated B-Track symbols."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
IN_JSONL = ROOT / "reports" / "constitution" / "btrack_pilot" / "symbol_candidates_curated_latest.jsonl"
OUT_DIR = ROOT / "reports" / "constitution" / "btrack_pilot"

DSS_TERMS = {
    "belial", "kittim", "yahad", "edah", "sons of light", "sons of darkness",
    "darkness", "light", "war", "covenant", "jerusalem", "levi", "judah", "benjamin",
}


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


def _bucket(dss: int, apo: int) -> str:
    if dss > 0 and apo > 0:
        return "mixed"
    if dss > 0 and apo <= 0:
        return "dss_only"
    if apo > 0 and dss <= 0:
        return "apocrypha_only"
    return "unknown"


def _has_dss_theme(symbol: str) -> bool:
    s = symbol.lower().strip()
    if s in DSS_TERMS:
        return True
    if " " in s:
        return any(part in DSS_TERMS for part in s.split())
    return False


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build B-Track symbol promotion lanes")
    ap.add_argument("--in-jsonl", default=str(IN_JSONL))
    ap.add_argument("--out-dir", default=str(OUT_DIR))
    ap.add_argument("--dss-min-count", type=int, default=1)
    args = ap.parse_args()

    in_path = _abs(args.in_jsonl)
    out_dir = _abs(args.out_dir)
    if not in_path.is_file():
        print(f"ERROR: missing input: {in_path}")
        return 2
    out_dir.mkdir(parents=True, exist_ok=True)

    dss_priority: list[dict[str, Any]] = []
    mixed_lane: list[dict[str, Any]] = []
    apocrypha_priority: list[dict[str, Any]] = []

    for row in _iter_jsonl(in_path):
        symbol = str(row.get("symbol", "")).strip()
        mix = row.get("source_mix", {})
        if not isinstance(mix, dict):
            mix = {}
        dss = int(mix.get("dss", 0) or 0)
        apo = int(mix.get("apocrypha", 0) or 0)
        bucket = _bucket(dss, apo)
        enriched = dict(row)
        enriched["lane_bucket"] = bucket
        enriched["dss_theme_match"] = _has_dss_theme(symbol)
        if bucket == "mixed":
            mixed_lane.append(enriched)
        if bucket == "apocrypha_only":
            apocrypha_priority.append(enriched)
        if (bucket == "dss_only") or (bucket == "mixed" and dss >= args.dss_min_count):
            dss_priority.append(enriched)

    # Stable ranking by tfidf-like score.
    sort_key = lambda r: float(r.get("score_tfidf_like", 0.0) or 0.0)
    dss_priority.sort(key=sort_key, reverse=True)
    mixed_lane.sort(key=sort_key, reverse=True)
    apocrypha_priority.sort(key=sort_key, reverse=True)

    dss_path = out_dir / "symbol_lane_dss_priority_latest.jsonl"
    mixed_path = out_dir / "symbol_lane_mixed_latest.jsonl"
    apo_path = out_dir / "symbol_lane_apocrypha_priority_latest.jsonl"
    summary_path = out_dir / "symbol_lane_summary_latest.json"

    _write_jsonl(dss_path, dss_priority)
    _write_jsonl(mixed_path, mixed_lane)
    _write_jsonl(apo_path, apocrypha_priority)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    summary = {
        "schema": "btrack_symbol_lanes_v1",
        "generated_at_utc": ts,
        "input_jsonl": str(in_path),
        "lanes": {
            "dss_priority": {"count": len(dss_priority), "path": str(dss_path)},
            "mixed": {"count": len(mixed_lane), "path": str(mixed_path)},
            "apocrypha_priority": {"count": len(apocrypha_priority), "path": str(apo_path)},
        },
        "policy": {
            "dss_priority_rule": "dss_only OR (mixed AND dss_count>=dss_min_count)",
            "dss_min_count": args.dss_min_count,
        },
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("OK: symbol promotion lanes generated")
    print(f"dss_priority={len(dss_priority)}")
    print(f"mixed={len(mixed_lane)}")
    print(f"apocrypha_priority={len(apocrypha_priority)}")
    print(f"summary={summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
