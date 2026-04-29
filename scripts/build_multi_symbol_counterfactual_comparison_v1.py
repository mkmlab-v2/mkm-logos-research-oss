#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def load(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare base multi-symbol survivability vs counterfactual set.")
    ap.add_argument("--survivability-json", default="docs/final/artifacts/multi_symbol_walkforward_survivability_latest.json")
    ap.add_argument("--counterfactual-json", default="docs/final/artifacts/multi_symbol_counterfactual_set_latest.json")
    ap.add_argument("--output-json", default="docs/final/artifacts/multi_symbol_counterfactual_comparison_latest.json")
    ap.add_argument("--min-mean-gap", type=float, default=0.15)
    args = ap.parse_args()

    sp = resolve(args.survivability_json)
    cp = resolve(args.counterfactual_json)
    op = resolve(args.output_json)
    for p in (sp, cp):
        if not p.is_file():
            raise SystemExit(f"missing required input: {p}")

    base = load(sp)
    counter = load(cp)
    base_rows = base.get("metrics") if isinstance(base.get("metrics"), list) else []
    counter_rows = counter.get("counterfactual_rows") if isinstance(counter.get("counterfactual_rows"), list) else []

    mean_base = sum(float(r.get("survivability_score", 0.0)) for r in base_rows if isinstance(r, dict)) / max(len(base_rows), 1)
    mean_cf = (
        sum(float(r.get("counterfactual_survivability_score", 0.0)) for r in counter_rows if isinstance(r, dict))
        / max(len(counter_rows), 1)
    )
    mean_gap = mean_base - mean_cf
    pass_gate = mean_gap >= float(args.min_mean_gap)

    out = {
        "schema": "multi_symbol_counterfactual_comparison_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "metrics": {
            "mean_base_survivability": round(mean_base, 6),
            "mean_counterfactual_survivability": round(mean_cf, 6),
            "mean_gap_base_minus_counterfactual": round(mean_gap, 6),
            "min_mean_gap_threshold": float(args.min_mean_gap),
        },
        "gate_eval": {
            "pass": pass_gate,
            "should_alert": not pass_gate,
            "promotion_hold": not pass_gate,
            "reasons": [] if pass_gate else ["counterfactual_gap_below_threshold"],
        },
        "sources": {"survivability_json": str(sp), "counterfactual_json": str(cp)},
    }
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(op))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

