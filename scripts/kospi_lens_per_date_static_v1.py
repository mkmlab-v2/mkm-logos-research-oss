#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Per-eval_date static lens dict for KOSPI multilens blend [HYPO][research_only]."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from scripts.btrack_phase3_lens_asof_v1 import (
    jsonl_last_row_by_calendar_day,
    row_asof_calendar_day,
)
from scripts.kospi_june2026_multilens_blend_v1 import load_static_lenses
from scripts.run_three_lens_horizon_empirical_eval_v2 import (  # noqa: E402
    _build_gate_by_day_tiered,
    _decision_to_direction,
    _gate_asof,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MYEONGNI_JSONL = ROOT / "data/myeongni/myeongni_16_state_experiment_v1.manseryeok_session_30y_v1.jsonl"
DEFAULT_SASANG_JSONL = ROOT / "data/sasang/sasang_dynamics_regime_mapping_v1.manseryeok_session_30y_v1.jsonl"
DEFAULT_MACRO_BACKFILL_JSONL = (
    ROOT / "reports/macro_risk/forward/macro_risk_forward_log_research_backfill_v1.jsonl"
)


def per_date_shadow_calendar_path(year_month: str) -> Path:
    tag = str(year_month).strip().replace("-", "")
    return ROOT / f"reports/kospi_{tag}_per_date_lens_shadow_calendar_v1.json"


def _mapping_target_to_direction(mt: str) -> str:
    m = (mt or "").strip().lower()
    if m == "sideways":
        return "neutral"
    if m in ("bull", "bear"):
        return m
    return "neutral"


def load_macro_gate_by_day(
    macro_jsonl: Path,
    *,
    operational_jsonl: Path | None = None,
) -> dict[str, dict[str, Any]]:
    sources: list[tuple[int, Path]] = [(1, macro_jsonl)]
    if operational_jsonl and operational_jsonl.is_file():
        sources.append((2, operational_jsonl))
    return _build_gate_by_day_tiered(sources)


def static_lenses_for_eval_date(
    eval_date: str,
    *,
    sasang_by_day: dict[str, dict[str, Any]],
    myeongni_by_day: dict[str, dict[str, Any]],
    baseline: dict[str, Any] | None = None,
    macro_gate_by_day: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Merge per-date sasang/myeongni JSONL as-of with global macro/field/logos baseline."""
    out = deepcopy(baseline or load_static_lenses())
    ed = eval_date[:10]

    if macro_gate_by_day:
        gate_row = _gate_asof(macro_gate_by_day, ed)
        if gate_row:
            macro_dir = _decision_to_direction(
                str(gate_row.get("decision_state") or ""),
                str(gate_row.get("risk_warning_level") or ""),
            )
            out["macro"] = {
                "direction": macro_dir,
                "loaded": True,
                "per_date": True,
                "matched_session_date": str(gate_row.get("session_date") or "")[:10],
                "source": gate_row.get("source_label") or gate_row.get("schema"),
                "decision_state": gate_row.get("decision_state"),
            }

    _, sa_row = row_asof_calendar_day(sasang_by_day, ed)
    if sa_row:
        mt = str(sa_row.get("mapping_target") or "neutral")
        out["sasang"] = {
            "direction": _mapping_target_to_direction(mt),
            "score": float((sa_row.get("machine_readables") or {}).get("session_direction_score") or 0.0),
            "loaded": True,
            "per_date": True,
            "matched_calendar_day": str(sa_row.get("eval_date") or sa_row.get("ts_utc", ""))[:10],
            "source": sa_row.get("source"),
            "stub": sa_row.get("stub"),
        }

    _, my_row = row_asof_calendar_day(myeongni_by_day, ed)
    if my_row:
        mt = str(my_row.get("mapping_target") or "neutral")
        out["myeongni_independent"] = {
            "direction": _mapping_target_to_direction(mt),
            "score": float(my_row.get("session_direction_score") or 0.0),
            "loaded": True,
            "per_date": True,
            "matched_calendar_day": str(my_row.get("eval_date") or my_row.get("ts_utc", ""))[:10],
            "source": my_row.get("source"),
            "stub": my_row.get("stub"),
        }

    return out


def load_lens_jsonl_by_day(
    myeongni_jsonl: Path,
    sasang_jsonl: Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any]]:
    my_by = jsonl_last_row_by_calendar_day(myeongni_jsonl)
    sa_by = jsonl_last_row_by_calendar_day(sasang_jsonl)
    meta = {
        "myeongni_jsonl": str(myeongni_jsonl),
        "sasang_jsonl": str(sasang_jsonl),
        "myeongni_days": len(my_by),
        "sasang_days": len(sa_by),
        "myeongni_min": min(my_by) if my_by else None,
        "myeongni_max": max(my_by) if my_by else None,
        "sasang_min": min(sa_by) if sa_by else None,
        "sasang_max": max(sa_by) if sa_by else None,
    }
    return my_by, sa_by, meta


def load_per_date_lens_bundle(
    myeongni_jsonl: Path,
    sasang_jsonl: Path,
    *,
    macro_backfill_jsonl: Path | None = None,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]] | None, dict[str, Any]]:
    """myeongni/sasang JSONL + optional per-date macro gate map."""
    my_by, sa_by, meta = load_lens_jsonl_by_day(myeongni_jsonl, sasang_jsonl)
    macro_path = macro_backfill_jsonl or DEFAULT_MACRO_BACKFILL_JSONL
    macro_by: dict[str, dict[str, Any]] | None = None
    if macro_path.is_file():
        macro_by = load_macro_gate_by_day(macro_path)
        meta["macro_backfill_jsonl"] = str(macro_path)
        meta["macro_days"] = len(macro_by)
    else:
        meta["macro_backfill_jsonl"] = None
    return my_by, sa_by, macro_by, meta


def per_date_lenses_for_session(
    eval_date: str,
    *,
    myeongni_by_day: dict[str, dict[str, Any]],
    sasang_by_day: dict[str, dict[str, Any]],
    macro_gate_by_day: dict[str, dict[str, Any]] | None = None,
    baseline: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return static_lenses_for_eval_date(
        eval_date,
        sasang_by_day=sasang_by_day,
        myeongni_by_day=myeongni_by_day,
        baseline=baseline,
        macro_gate_by_day=macro_gate_by_day,
    )
