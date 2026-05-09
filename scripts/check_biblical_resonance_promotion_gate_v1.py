#!/usr/bin/env python3
"""Promotion gate for biblical resonance hypothesis evaluation (B-track only)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVAL = ROOT / "docs" / "final" / "artifacts" / "biblical_resonance_eval_latest.json"
DEFAULT_POLICY = ROOT / "docs" / "final" / "artifacts" / "biblical_resonance_promotion_policy_v1.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "biblical_resonance_promotion_gate_latest.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _to_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _to_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def main() -> int:
    ap = argparse.ArgumentParser(description="Check promotion gate for biblical resonance evaluation.")
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--policy-json", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--strict", action="store_true", help="Exit 1 when promotion outcome is HOLD.")
    args = ap.parse_args()

    if not args.eval_json.exists():
        raise FileNotFoundError(f"Missing eval json: {args.eval_json}")
    if not args.policy_json.exists():
        raise FileNotFoundError(f"Missing policy json: {args.policy_json}")

    ev = _load(args.eval_json)
    pol = _load(args.policy_json)
    th = pol.get("thresholds", {})
    inputs = ev.get("inputs", {})
    rows = ev.get("hypotheses", [])
    if not isinstance(rows, list):
        rows = []

    min_strong_score = _to_float(th.get("min_composite_score_for_strong", 0.6), 0.6)
    strong_count = sum(1 for r in rows if _to_float(r.get("composite_score")) >= min_strong_score)
    weak_count = sum(1 for r in rows if _to_float(r.get("composite_score")) < 0.4)

    failures: list[str] = []
    if _to_int(inputs.get("news_row_count")) < _to_int(th.get("min_news_rows_window", 40)):
        failures.append("insufficient_news_rows_window")
    if _to_int(inputs.get("news_unique_asof_days")) < _to_int(th.get("min_unique_asof_days_window", 7)):
        failures.append("insufficient_unique_asof_days_window")
    if _to_int(inputs.get("chronicle_row_count")) < _to_int(th.get("min_chronicle_rows_window", 7)):
        failures.append("insufficient_chronicle_rows_window")
    if strong_count < _to_int(th.get("min_strong_hypotheses", 2)):
        failures.append("insufficient_strong_hypotheses")
    if weak_count > _to_int(th.get("max_weak_hypotheses", 1)):
        failures.append("too_many_weak_hypotheses")

    is_promote = len(failures) == 0
    outcomes = pol.get("outcomes", {})
    outcome = str(outcomes.get("promote" if is_promote else "hold", "HOLD_NEED_MORE_EVIDENCE"))

    out = {
        "schema": "biblical_resonance_promotion_gate_v1",
        "checked_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_track": "B",
        "observation_mode": "KEEP_OBSERVATION_ONLY",
        "auto_bind_to_atrack_forbidden": True,
        "eval_json": str(args.eval_json),
        "policy_json": str(args.policy_json),
        "strong_hypotheses_count": strong_count,
        "weak_hypotheses_count": weak_count,
        "failures": failures,
        "promotion_outcome": outcome,
        "promote_shadow_ready": is_promote,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False))

    if args.strict and not is_promote:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
