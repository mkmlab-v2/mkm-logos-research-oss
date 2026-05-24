#!/usr/bin/env python3
"""List BTC eval_date rows where per-date prediction missed (all-rows basis)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
DEFAULT_OUT = ROOT / "reports/btrack_headline_miss_report_v1_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = json.loads(args.score_json.read_text(encoding="utf-8"))
    rows = [r for r in doc.get("rows", []) if isinstance(r, dict) and r.get("instrument") == "btc"]
    misses: list[dict[str, Any]] = []
    hits = 0
    for r in rows:
        pred = str(r.get("predicted_direction") or "").lower()
        act = str(r.get("actual_direction") or "").lower()
        ok = pred == act
        if ok:
            hits += 1
        else:
            kind = "neutral_abstain_miss" if pred == "neutral" else "wrong_direction"
            misses.append(
                {
                    "eval_date": r.get("eval_date"),
                    "predicted_direction": pred,
                    "actual_direction": act,
                    "miss_kind": kind,
                }
            )
    n = len(rows)
    report = {
        "schema": "btrack_headline_miss_report_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "n_evaluated": n,
        "price_hits": hits,
        "price_directional_hit_rate": round(hits / n, 6) if n else None,
        "n_misses": len(misses),
        "miss_breakdown": {
            "wrong_direction": sum(1 for m in misses if m["miss_kind"] == "wrong_direction"),
            "neutral_abstain_miss": sum(1 for m in misses if m["miss_kind"] == "neutral_abstain_miss"),
        },
        "misses": misses,
        "operator_line": (
            f"- [MKM-HEADLINE-MISS] {hits}/{n} hits; "
            f"wrong_dir={sum(1 for m in misses if m['miss_kind']=='wrong_direction')} "
            f"neutral_miss={sum(1 for m in misses if m['miss_kind']=='neutral_abstain_miss')}"
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(report["operator_line"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
