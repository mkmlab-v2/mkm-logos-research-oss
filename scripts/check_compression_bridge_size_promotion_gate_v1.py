#!/usr/bin/env python3
"""Gate promotion for compression bridge size-only lane."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HOLDOUT = ROOT / "docs" / "final" / "artifacts" / "compression_bridge_size_holdout_eval_latest.json"
DEFAULT_WALKFORWARD = ROOT / "docs" / "final" / "artifacts" / "compression_bridge_size_walkforward_eval_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "compression_bridge_size_promotion_gate_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _f(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def main() -> int:
    ap = argparse.ArgumentParser(description="Promotion gate for size-only bridge.")
    ap.add_argument("--holdout-eval", type=Path, default=DEFAULT_HOLDOUT)
    ap.add_argument("--walkforward-eval", type=Path, default=DEFAULT_WALKFORWARD)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = _load_json(args.holdout_eval)
    rows = doc.get("rows") if isinstance(doc.get("rows"), list) else []
    ok_rows = [r for r in rows if isinstance(r, dict) and r.get("status") == "ok"]
    direction_changed = sum(
        1 for r in ok_rows if r.get("prediction_direction_on") != r.get("prediction_direction_off")
    )
    min_hit_delta = min((_f(r.get("delta_price_directional_hit_rate")) for r in ok_rows), default=0.0)
    mean_size_weighted = (
        sum(_f(r.get("delta_size_weighted_payoff_mean")) for r in ok_rows) / len(ok_rows) if ok_rows else 0.0
    )
    all_size_non_negative = all(_f(r.get("delta_size_weighted_payoff_mean")) >= 0.0 for r in ok_rows)
    holdout_pass = bool(ok_rows) and direction_changed == 0 and min_hit_delta >= 0.0 and all_size_non_negative and mean_size_weighted > 0.0
    walkforward_doc = _load_json(args.walkforward_eval) if args.walkforward_eval.is_file() else {}
    walkforward_summary = walkforward_doc.get("summary") if isinstance(walkforward_doc.get("summary"), dict) else {}
    walkforward_decision = str(walkforward_doc.get("decision") or "")
    walkforward_pass = (
        bool(walkforward_summary)
        and int(walkforward_summary.get("direction_changed_rows") or 0) == 0
        and _f(walkforward_summary.get("min_delta_price_directional_hit_rate")) >= 0.0
        and _f(walkforward_summary.get("min_delta_size_weighted_payoff_mean")) >= 0.0
        and walkforward_decision == "PASS_WALKFORWARD_SIZE_LANE"
    )
    pass_gate = holdout_pass and walkforward_pass

    out = {
        "schema": "compression_bridge_size_promotion_gate_v1",
        "generated_at_utc": _utc_now(),
        "input_holdout_eval": str(args.holdout_eval.resolve()),
        "input_walkforward_eval": str(args.walkforward_eval.resolve()) if args.walkforward_eval.is_file() else None,
        "metrics": {
            "ok_rows": len(ok_rows),
            "direction_changed_rows": direction_changed,
            "min_delta_price_directional_hit_rate": round(min_hit_delta, 8),
            "mean_delta_size_weighted_payoff": round(mean_size_weighted, 8),
            "all_size_weighted_non_negative": all_size_non_negative,
            "holdout_pass": holdout_pass,
            "walkforward_pass": walkforward_pass,
            "walkforward_min_delta_size_weighted_payoff": round(_f(walkforward_summary.get("min_delta_size_weighted_payoff_mean")), 8)
            if walkforward_summary
            else None,
        },
        "decision": "GO_SIZE_LANE_PROMOTION_CONFIRMED" if pass_gate else "HOLD_SIZE_LANE_PROMOTION",
        "fact_safe_note": "Direction must remain isolated and size lane must show positive holdout contribution.",
        "out_of_scope": "No automatic Track A/B promotion or live trigger.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

