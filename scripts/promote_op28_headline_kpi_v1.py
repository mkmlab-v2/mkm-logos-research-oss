#!/usr/bin/env python3
"""Promote O-P28 min-confidence active KPI to headline eval SSOT (human-approved).

Writes docs/final/artifacts/prophecy_hit_rate_eval_latest.json with:
- price_directional_hit_rate = ACTIVE rate (headline KPI after O-P28)
- price_directional_hit_rate_all = all-row rate (reference)
Does not enable live trading.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
for p in (str(ROOT), str(SCRIPTS)):
    if p not in sys.path:
        sys.path.insert(0, p)

from scripts.sweep_prophecy_headline_deadzone_hold_v1 import (
    _load_json,
    _metrics_active,
    _metrics_all,
    _per_date_index,
)

DEFAULT_SCORE = ROOT / "reports" / "btrack_prophecy_score_op28_shadow_v1_latest.json"
DEFAULT_PER_DATE = ROOT / "reports" / "btrack_ensemble_per_date_directions_180d_op28_gated_v1_latest.json"
from scripts.prophecy_hit_rate_ssot_v1 import HEADLINE_KPI  # noqa: E402

DEFAULT_OUT = HEADLINE_KPI
SCHEMA = "prophecy_hit_rate_eval_report_v2"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--per-date-json", type=Path, default=DEFAULT_PER_DATE)
    ap.add_argument("--min-confidence", type=float, default=0.18)
    ap.add_argument("--score-abs-deadzone", type=float, default=0.0)
    ap.add_argument("--prior-headline-rate", type=float, default=0.494444)
    ap.add_argument("--promotion-lane", type=str, default="op28_min_confidence_active")
    ap.add_argument("--used-field", type=str, default="op28_active_gate_on_per_date_confidence")
    ap.add_argument(
        "--zeroing-note",
        type=str,
        default=(
            "Headline promotion: price_directional_hit_rate is ACTIVE (low-confidence rows skipped). "
            "price_directional_hit_rate_all is all scored rows including neutral/low-conf predictions."
        ),
    )
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--skip-evolution-allowlist",
        action="store_true",
        help="Skip evolution allowlist gate (tests only; do not use in scheduled automation).",
    )
    args = ap.parse_args()

    if not args.skip_evolution_allowlist:
        from evolution_auto_apply_allowlist_v1 import assert_headline_kpi_promotion_allowed

        try:
            assert_headline_kpi_promotion_allowed(
                min_confidence=float(args.min_confidence),
                score_abs_deadzone=float(args.score_abs_deadzone),
                output=args.output,
            )
        except ValueError as exc:
            raise SystemExit(f"evolution allowlist: {exc}") from exc

    score_doc = _load_json(args.score_json)
    if not score_doc or not isinstance(score_doc.get("rows"), list):
        raise SystemExit(f"invalid score json: {args.score_json}")
    rows = [r for r in score_doc["rows"] if isinstance(r, dict)]
    pdx = _per_date_index(args.per_date_json)
    active = _metrics_active(
        rows,
        min_confidence=float(args.min_confidence),
        score_abs_deadzone=float(args.score_abs_deadzone),
        per_date_index=pdx,
    )
    all_m = _metrics_all(rows)

    rate_active = active.get("price_directional_hit_rate_active")
    rate_all = all_m.get("price_directional_hit_rate_all")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "run_mode": "price",
        "status": "ok",
        "zeroing_note": str(args.zeroing_note),
        "inputs": {
            "run_mode": "price",
            "score_json": str(args.score_json),
            "per_date_json": str(args.per_date_json),
            "headline_instrument": "auto",
            "min_confidence_active_gate": float(args.min_confidence),
            "score_abs_deadzone": float(args.score_abs_deadzone),
        },
        "metrics": {
            "price_directional_hit_rate": rate_active,
            "n_evaluated": active.get("n_active"),
            "price_hits": active.get("price_hits_active"),
            "price_directional_hit_rate_all": rate_all,
            "n_evaluated_all": all_m.get("n_evaluated_all"),
            "price_hits_all": all_m.get("price_hits_all"),
            "coverage_active": active.get("coverage_active"),
        },
        "headline_promotion_v1": {
            "lane": str(args.promotion_lane),
            "human_approved": True,
            "prior_price_directional_hit_rate": float(args.prior_headline_rate),
            "delta_vs_prior": round(float(rate_active or 0) - float(args.prior_headline_rate), 6),
            "research_only_boundary": False,
            "track_a_live_auto_merge": False,
            "evolution_allowlist_v1": {
                "checked": not args.skip_evolution_allowlist,
                "writer_script": "promote_op28_headline_kpi_v1",
                "min_confidence_active_gate": float(args.min_confidence),
                "score_abs_deadzone": float(args.score_abs_deadzone),
            },
        },
        "sources": {
            "oracle_path": None,
            "registry_path": None,
            "used_field": str(args.used_field),
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    args.output.write_text(text, encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(
        f"HEADLINE_ACTIVE={rate_active} ALL={rate_all} "
        f"n_active={active.get('n_active')} cov={active.get('coverage_active')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
