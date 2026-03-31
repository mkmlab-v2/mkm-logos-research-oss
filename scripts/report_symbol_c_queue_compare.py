#!/usr/bin/env python3
"""Compare stable vs exploratory C validation queues."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"

IN_STABLE = PILOT / "symbol_c_validation_queue_stable_latest.jsonl"
IN_EXPL = PILOT / "symbol_c_validation_queue_exploratory_latest.jsonl"
OUT = PILOT / "symbol_c_validation_queue_compare_latest.json"


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


def _stats(rows: list[dict[str, Any]], overlap_k: int) -> dict[str, Any]:
    if not rows:
        return {"count": 0, "avg_score": 0.0, "top_symbols": [], "top_k_used": overlap_k}
    scores = [float(r.get("score_tfidf_like", 0.0) or 0.0) for r in rows]
    top_symbols = [str(r.get("symbol", "")).strip() for r in rows[:overlap_k]]
    return {
        "count": len(rows),
        "avg_score": round(sum(scores) / len(scores), 6),
        "top_symbols": top_symbols,
        "top_k_used": overlap_k,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare C validation queues")
    ap.add_argument("--stable-jsonl", default=str(IN_STABLE))
    ap.add_argument("--exploratory-jsonl", default=str(IN_EXPL))
    ap.add_argument("--out-json", default=str(OUT))
    ap.add_argument("--overlap-k", type=int, default=20)
    args = ap.parse_args()

    stable_path = _abs(args.stable_jsonl)
    expl_path = _abs(args.exploratory_jsonl)
    out_path = _abs(args.out_json)
    for p in (stable_path, expl_path):
        if not p.is_file():
            print(f"ERROR: missing file: {p}")
            return 2

    stable_rows = list(_iter_jsonl(stable_path))
    expl_rows = list(_iter_jsonl(expl_path))
    stable = _stats(stable_rows, args.overlap_k)
    expl = _stats(expl_rows, args.overlap_k)

    stable_top = set(stable["top_symbols"])
    expl_top = set(expl["top_symbols"])
    overlap_count = len(stable_top & expl_top)
    denom = max(1, min(len(stable_top), len(expl_top)))
    overlap_rate = round(overlap_count / denom, 6)

    report = {
        "schema": "btrack_symbol_c_validation_queue_compare_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "stable_jsonl": str(stable_path),
            "exploratory_jsonl": str(expl_path),
        },
        "stable": {
            "count": stable["count"],
            "avg_score": stable["avg_score"],
        },
        "exploratory": {
            "count": expl["count"],
            "avg_score": expl["avg_score"],
        },
        "delta": {
            "count": int(expl["count"]) - int(stable["count"]),
            "avg_score": round(float(expl["avg_score"]) - float(stable["avg_score"]), 6),
        },
        "top_overlap": {
            "k": args.overlap_k,
            "count": overlap_count,
            "rate": overlap_rate,
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("OK: symbol C queue compare generated")
    print(f"out={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
