#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B-track Logos per-date core — macro gate causal-asof [HYPO][NON_GATING][research_only]."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_LOGOS_PER_DATE_JSONL = ROOT / "reports/btrack_logos_per_date_v1.jsonl"
DEFAULT_LOGOS_LENS = ROOT / "docs/final/artifacts/logos_independent_lens_latest.json"

MACRO_RISK_LOG = ROOT / "reports/macro_risk/forward/macro_risk_forward_log_v1.jsonl"
MACRO_RISK_BACKFILL_LOG = ROOT / "reports/macro_risk/forward/macro_risk_forward_log_research_backfill_v1.jsonl"
FRAGILITY_LOG = ROOT / "reports/fragility_macro_risk_daily_run_log.jsonl"

DIRECTION_TO_SCORE = {"bull": 0.55, "bear": -0.55, "neutral": 0.0}


def _direction_to_score(direction: str) -> float:
    return float(DIRECTION_TO_SCORE.get(str(direction or "neutral").lower(), 0.0))


def _score_to_sign(score: float) -> int:
    if score > 0:
        return 1
    if score < 0:
        return -1
    return 0


def logos_global_block(path: Path) -> dict[str, Any]:
    from scripts.btrack_multilens_per_date_core_v1 import logos_global

    block = logos_global(path)
    block["input_mode"] = "global_snapshot"
    block["non_gating"] = True
    return block


def index_logos_per_date_rows(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        dk = str(row.get("session_date") or row.get("eval_date") or "")[:10]
        if dk:
            out[dk] = row
    return out


def read_logos_per_date_jsonl(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(o, dict):
            rows.append(o)
    return index_logos_per_date_rows(rows)


def logos_block_at_date(
    logos_by_day: dict[str, dict[str, Any]],
    eval_date: str,
    *,
    fallback_global: Path | None = DEFAULT_LOGOS_LENS,
) -> dict[str, Any]:
    """Resolve per-date Logos advisory block; causal as-of <= eval_date."""
    ed = eval_date[:10]
    eligible = [d for d in logos_by_day if d <= ed]
    if eligible:
        row = logos_by_day[max(eligible)]
        direction = str(row.get("direction") or "neutral")
        score = row.get("direction_score")
        if not isinstance(score, (int, float)):
            score = _direction_to_score(direction)
        score_f = float(score)
        return {
            "direction_score": round(score_f, 6),
            "sign": _score_to_sign(score_f),
            "direction": direction,
            "confidence": row.get("confidence"),
            "data_quality": str(row.get("source_provenance") or "per_date_macro_gate"),
            "input_mode": "per_date_macro_gate",
            "matched_session_date": str(row.get("session_date") or max(eligible))[:10],
            "non_gating": True,
            "variant_id": row.get("variant_id"),
        }
    if fallback_global and fallback_global.is_file():
        block = logos_global_block(fallback_global)
        block["matched_session_date"] = None
        block["fallback_used"] = True
        return block
    return {
        "direction_score": 0.0,
        "sign": 0,
        "direction": "neutral",
        "data_quality": "missing",
        "input_mode": "missing",
        "non_gating": True,
    }


def build_logos_per_date_rows(
    *,
    trading_days: list[str],
    closes: dict[str, float],
    date_from: str | None,
    date_to: str | None,
    neutral_bps: float,
    logos_lens: Path = DEFAULT_LOGOS_LENS,
    gate_paths: list[tuple[int, Path]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from scripts.run_three_lens_horizon_empirical_eval_v2 import (  # noqa: WPS433
        _build_gate_by_day_tiered,
        _decision_to_direction,
        _gate_asof,
        _trailing_return_sign,
    )
    from scripts.btrack_multilens_per_date_core_v1 import logos_global, sign_to_dir

    if gate_paths is None:
        gate_paths = [
            (3, MACRO_RISK_LOG),
            (2, FRAGILITY_LOG),
            (1, MACRO_RISK_BACKFILL_LOG),
        ]

    global_block = logos_global(logos_lens)
    global_dir = sign_to_dir(int(global_block.get("sign") or 0))
    gate_by_day = _build_gate_by_day_tiered(gate_paths)

    days = list(trading_days)
    if date_from:
        days = [d for d in days if d >= date_from[:10]]
    if date_to:
        days = [d for d in days if d <= date_to[:10]]

    out: list[dict[str, Any]] = []
    mode_counts: dict[str, int] = {}
    for i, dk in enumerate(trading_days):
        if dk not in days:
            continue
        gate_row = _gate_asof(gate_by_day, dk)
        trailing_dir = _trailing_return_sign(closes, trading_days, i, 21, neutral_bps)
        if gate_row:
            direction = _decision_to_direction(
                str(gate_row.get("decision_state") or ""),
                str(gate_row.get("risk_warning_level") or ""),
            )
            mode = (
                "research_backfill_ohlcv_v1"
                if "research_backfill" in str(gate_row.get("schema") or "")
                else "causal_asof_macro_risk_log"
            )
            gate_source = str(gate_row.get("schema") or "macro_gate_log")
        elif trailing_dir:
            direction = trailing_dir
            mode = "trailing_21d_fallback_no_causal_gate"
            gate_source = None
        else:
            direction = global_dir
            mode = "global_snapshot_fallback"
            gate_source = None

        mode_counts[mode] = mode_counts.get(mode, 0) + 1
        score = _direction_to_score(direction)
        out.append(
            {
                "schema": "btrack_logos_per_date_v1",
                "session_date": dk,
                "eval_date": dk,
                "hypothesis_tier": "B",
                "research_only": True,
                "stub": False,
                "non_gating": True,
                "source_provenance": "macro_gate_causal_asof_v1",
                "variant_id": "logos_macro_risk_causal",
                "direction": direction,
                "direction_score": round(score, 6),
                "sign": _score_to_sign(score),
                "global_snapshot_direction": global_dir,
                "derivation_mode": mode,
                "gate_source": gate_source,
                "matched_gate_session_date": str((gate_row or {}).get("session_date") or "")[:10] or None,
            }
        )

    meta = {
        "n_rows": len(out),
        "date_min": out[0]["session_date"] if out else None,
        "date_max": out[-1]["session_date"] if out else None,
        "derivation_mode_counts": mode_counts,
        "first_causal_gate_day": min(gate_by_day.keys()) if gate_by_day else None,
        "global_snapshot_direction": global_dir,
    }
    return out, meta
