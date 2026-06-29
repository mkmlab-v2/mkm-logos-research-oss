#!/usr/bin/env python3
"""Small-sample guardrails for KOSPI Field band L4 / OOS [HYPO]."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

HOLDOUT_N_DISCUSSION_MIN = 30
TOTAL_SCORED_HEADLINE_MIN = 40
CONSECUTIVE_OOS_PASS_REQUIRED = 2
MIN_DELTA_PP = 0.03

DEFAULT_OOS_LOG = Path(__file__).resolve().parents[1] / "reports/kospi_field_band_prophecy_only_oos_log_v1.jsonl"


def consecutive_oos_passes(log_path: Path = DEFAULT_OOS_LOG) -> int:
    if not log_path.is_file():
        return 0
    streak = 0
    for line in reversed(log_path.read_text(encoding="utf-8-sig").splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            break
        if not isinstance(obj, dict):
            break
        if obj.get("prophecy_only_oos_ready") is True and float(obj.get("delta_stack_minus_base_holdout") or 0) >= MIN_DELTA_PP:
            streak += 1
        else:
            break
    return streak


def build_small_sample_guardrails(
    prophecy_oos: dict[str, Any] | None,
    *,
    log_path: Path = DEFAULT_OOS_LOG,
) -> dict[str, Any]:
    po_ready = (prophecy_oos or {}).get("prophecy_only_oos_ready") is True
    po_hold = ((prophecy_oos or {}).get("holdout_pooled") or {}).get("stack_union") or {}
    holdout_n = int(po_hold.get("n_scored") or 0)
    total_n = int((prophecy_oos or {}).get("n_scored_total") or 0)
    delta = float((prophecy_oos or {}).get("delta_stack_minus_base_holdout") or 0.0)
    consecutive = consecutive_oos_passes(log_path)

    holdout_ok = holdout_n >= HOLDOUT_N_DISCUSSION_MIN
    total_ok = total_n >= TOTAL_SCORED_HEADLINE_MIN
    consecutive_ok = consecutive >= CONSECUTIVE_OOS_PASS_REQUIRED
    delta_ok = delta >= MIN_DELTA_PP

    discussion_eligible = po_ready and holdout_ok and total_ok and consecutive_ok and delta_ok

    blockers: list[str] = []
    if not po_ready:
        blockers.append("prophecy_only_oos_gates_not_pass")
    if not holdout_ok:
        blockers.append(f"holdout_n_lt_{HOLDOUT_N_DISCUSSION_MIN}")
    if not total_ok:
        blockers.append(f"total_scored_n_lt_{TOTAL_SCORED_HEADLINE_MIN}")
    if not consecutive_ok:
        blockers.append(f"consecutive_oos_pass_lt_{CONSECUTIVE_OOS_PASS_REQUIRED}")
    if not delta_ok:
        blockers.append("delta_lt_3pp")

    return {
        "holdout_n": holdout_n,
        "total_scored_n": total_n,
        "holdout_n_discussion_min": HOLDOUT_N_DISCUSSION_MIN,
        "total_scored_headline_min": TOTAL_SCORED_HEADLINE_MIN,
        "consecutive_oos_pass_required": CONSECUTIVE_OOS_PASS_REQUIRED,
        "consecutive_oos_pass_count": consecutive,
        "delta_stack_minus_base_holdout": delta,
        "track_a_discussion_eligible": discussion_eligible,
        "promotion_candidate_research": po_ready and delta_ok,
        "promotion_candidate_for_discussion": discussion_eligible,
        "mixed_panel_headline_kpi_forbidden": po_ready,
        "blockers": blockers,
        "next_auto_schedule": "MKM_KospiFieldBand_MonthlyProphecyRevalidate monthly day 2 09:30",
        "panel_expansion_note": (
            None
            if total_n >= TOTAL_SCORED_HEADLINE_MIN
            else "Include new prophecy month eval when n_scored>0; July 202607 currently empty"
        ),
    }
