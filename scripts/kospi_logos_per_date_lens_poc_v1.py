#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Per-date Logos lens PoC helpers [HYPO][research_only][NON_GATING].

Replaces global `logos_independent_lens_latest.json` snapshot with a per-session
macro-gate-derived direction for blend replay only. Does NOT enable Track A or
daily equal-weight Logos elevation.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from scripts.kospi_june2026_multilens_blend_v1 import load_static_lenses
from scripts.run_three_lens_horizon_empirical_eval_v2 import (  # noqa: E402
    _decision_to_direction,
    _gate_asof,
)

DEFAULT_MACRO_BACKFILL_JSONL = (
    Path(__file__).resolve().parents[1]
    / "reports/macro_risk/forward/macro_risk_forward_log_research_backfill_v1.jsonl"
)


def logos_direction_from_macro_gate_row(gate_row: dict[str, Any] | None) -> tuple[str, dict[str, Any]]:
    if not gate_row:
        return "neutral", {"mode": "no_gate_row", "signal_source": "none"}
    direction = _decision_to_direction(
        str(gate_row.get("decision_state") or ""),
        str(gate_row.get("risk_warning_level") or ""),
    )
    meta = {
        "mode": "causal_asof_macro_risk_log",
        "signal_source": gate_row.get("source_label") or gate_row.get("schema"),
        "matched_session_date": str(gate_row.get("session_date") or "")[:10],
        "decision_state": gate_row.get("decision_state"),
        "risk_warning_level": gate_row.get("risk_warning_level"),
    }
    return direction, meta


def logos_lens_for_eval_date(
    eval_date: str,
    *,
    baseline: dict[str, Any] | None = None,
    macro_gate_by_day: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Merge per-date logos (macro-gate proxy) into static lens dict."""
    out = deepcopy(baseline or load_static_lenses())
    ed = eval_date[:10]
    global_logos = out.get("logos") if isinstance(out.get("logos"), dict) else {}

    if macro_gate_by_day:
        gate_row = _gate_asof(macro_gate_by_day, ed)
        direction, meta = logos_direction_from_macro_gate_row(gate_row)
        out["logos"] = {
            "direction": direction,
            "score": float(global_logos.get("score") or 0.0),
            "loaded": True,
            "per_date": True,
            "non_gating": True,
            "global_snapshot_direction": str(global_logos.get("direction") or "neutral"),
            "derivation": "macro_gate_causal_asof_v1",
            **meta,
        }
    return out
