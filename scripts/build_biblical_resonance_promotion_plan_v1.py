#!/usr/bin/env python3
"""Build minimal execution plan to satisfy biblical resonance promotion gate."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVAL = ROOT / "docs" / "final" / "artifacts" / "biblical_resonance_eval_latest.json"
DEFAULT_POLICY = ROOT / "docs" / "final" / "artifacts" / "biblical_resonance_promotion_policy_v1.json"
DEFAULT_GATE = ROOT / "docs" / "final" / "artifacts" / "biblical_resonance_promotion_gate_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "biblical_resonance_promotion_plan_latest.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _to_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def main() -> int:
    ap = argparse.ArgumentParser(description="Build minimal promotion execution plan.")
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--policy-json", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--gate-json", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    ev = _load(args.eval_json)
    pol = _load(args.policy_json)
    gate = _load(args.gate_json) if args.gate_json.exists() else {}

    th = pol.get("thresholds", {})
    inputs = ev.get("inputs", {})
    summary = ev.get("summary", {})

    need_news_rows = max(0, _to_int(th.get("min_news_rows_window", 40)) - _to_int(inputs.get("news_row_count")))
    need_unique_days = max(0, _to_int(th.get("min_unique_asof_days_window", 7)) - _to_int(inputs.get("news_unique_asof_days")))
    need_chronicle_rows = max(0, _to_int(th.get("min_chronicle_rows_window", 7)) - _to_int(inputs.get("chronicle_row_count")))
    need_strong = max(0, _to_int(th.get("min_strong_hypotheses", 2)) - _to_int(summary.get("strong_count")))

    plan_steps: list[dict[str, Any]] = []
    if need_unique_days > 0:
        plan_steps.append(
            {
                "step": "collect_distinct_asof_days",
                "target": f"+{need_unique_days} unique as_of days",
                "how": "run daily observation ingestion on new calendar days; avoid same-day duplicates as primary source",
            }
        )
    if need_news_rows > 0:
        per_day = max(1, (need_news_rows + max(1, need_unique_days) - 1) // max(1, need_unique_days))
        plan_steps.append(
            {
                "step": "increase_news_rows_window",
                "target": f"+{need_news_rows} rows in 30-day window",
                "how": f"ingest at least {per_day} high-signal rows per day over next {max(1, need_unique_days)} days",
            }
        )
    if need_chronicle_rows > 0:
        plan_steps.append(
            {
                "step": "accumulate_chronicle_rows",
                "target": f"+{need_chronicle_rows} chronicle rows",
                "how": "run chronicle daily build/eval cycle each day to append history rows",
            }
        )
    if need_strong > 0:
        plan_steps.append(
            {
                "step": "raise_hypothesis_strength",
                "target": f"+{need_strong} strong hypotheses (score >= {th.get('min_composite_score_for_strong', 0.6)})",
                "how": "expand keyword groups with validated historical markers and re-run eval after data growth",
            }
        )

    min_days_estimate = max(1, need_unique_days)
    out = {
        "schema": "biblical_resonance_promotion_plan_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_track": "B",
        "observation_mode": "KEEP_OBSERVATION_ONLY",
        "auto_bind_to_atrack_forbidden": True,
        "current_gate_outcome": gate.get("promotion_outcome", "unknown"),
        "deficits": {
            "news_rows_missing": need_news_rows,
            "unique_asof_days_missing": need_unique_days,
            "chronicle_rows_missing": need_chronicle_rows,
            "strong_hypotheses_missing": need_strong,
        },
        "minimum_days_estimate": min_days_estimate,
        "execution_steps": plan_steps,
        "daily_routine": [
            "run_global_atom_claim_lock_daily.ps1",
            "check biblical_resonance_eval_latest.json",
            "check biblical_resonance_promotion_gate_latest.json"
        ],
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"schema": out["schema"], "output_json": str(args.output_json), "minimum_days_estimate": min_days_estimate}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
