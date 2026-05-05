#!/usr/bin/env python3
"""Promotion gate checker for Logos symbolic event backtest (B-track).

Reads backtest payload and emits a GO/HOLD style decision artifact.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BACKTEST = ROOT / "docs" / "final" / "artifacts" / "logos_symbolic_event_backtest_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "logos_symbolic_event_promotion_gate_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--backtest-json", type=Path, default=DEFAULT_BACKTEST)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--min-samples", type=int, default=30)
    ap.add_argument("--min-hit-rate", type=float, default=0.53)
    ap.add_argument("--min-symbol-coverage", type=int, default=3)
    ap.add_argument("--min-holdout-samples", type=int, default=0)
    ap.add_argument("--min-holdout-hit-rate", type=float, default=0.0)
    ap.add_argument("--min-non-synthetic-samples", type=int, default=0)
    args = ap.parse_args()

    if not args.backtest_json.is_file():
        raise SystemExit(f"Missing --backtest-json: {args.backtest_json}")

    bt = _read_json(args.backtest_json)
    summary = bt.get("summary") if isinstance(bt.get("summary"), dict) else {}
    n = int(summary.get("n_evaluated") or 0)
    hit_rate = summary.get("hit_rate")
    cov = int(summary.get("symbol_coverage_count") or 0)
    hit_rate_num = float(hit_rate) if isinstance(hit_rate, (int, float)) else None
    split_summary = bt.get("split_summary") if isinstance(bt.get("split_summary"), dict) else {}
    locked_eval = split_summary.get("locked_eval") if isinstance(split_summary.get("locked_eval"), dict) else {}
    holdout_n = int(locked_eval.get("n_evaluated") or 0)
    holdout_hit_rate = locked_eval.get("hit_rate")
    holdout_hit_rate_num = float(holdout_hit_rate) if isinstance(holdout_hit_rate, (int, float)) else None
    non_synth_n = int(summary.get("non_synthetic_n_evaluated") or 0)

    checks = {
        "min_samples_pass": n >= args.min_samples,
        "min_hit_rate_pass": bool(hit_rate_num is not None and hit_rate_num >= args.min_hit_rate),
        "min_symbol_coverage_pass": cov >= args.min_symbol_coverage,
        "min_holdout_samples_pass": holdout_n >= args.min_holdout_samples,
        "min_holdout_hit_rate_pass": bool(
            args.min_holdout_samples == 0
            or (holdout_hit_rate_num is not None and holdout_hit_rate_num >= args.min_holdout_hit_rate)
        ),
        "min_non_synthetic_samples_pass": non_synth_n >= args.min_non_synthetic_samples,
    }
    all_pass = all(checks.values())

    decision = "GO_RESEARCH_PROMOTION_CANDIDATE" if all_pass else "HOLD_RESEARCH_ONLY"
    out = {
        "schema": "logos_symbolic_event_promotion_gate_v1",
        "generated_at_utc": _utc_now(),
        "backtest_ref": str(args.backtest_json).replace("\\", "/"),
        "thresholds": {
            "min_samples": args.min_samples,
            "min_hit_rate": args.min_hit_rate,
            "min_symbol_coverage": args.min_symbol_coverage,
            "min_holdout_samples": args.min_holdout_samples,
            "min_holdout_hit_rate": args.min_holdout_hit_rate,
            "min_non_synthetic_samples": args.min_non_synthetic_samples,
        },
        "metrics_snapshot": {
            "n_evaluated": n,
            "hit_rate": hit_rate_num,
            "symbol_coverage_count": cov,
            "holdout_n_evaluated": holdout_n,
            "holdout_hit_rate": holdout_hit_rate_num,
            "non_synthetic_n_evaluated": non_synth_n,
        },
        "checks": checks,
        "all_pass": all_pass,
        "decision": decision,
        "track_wall": {
            "promotion_to_a_track_allowed": False,
            "human_review_gate_required": True,
            "note": "GO here means B-track research promotion candidate only.",
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "decision": decision, "all_pass": all_pass}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

