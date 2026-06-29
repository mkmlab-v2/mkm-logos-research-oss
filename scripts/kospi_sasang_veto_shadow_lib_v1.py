#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sasang veto helpers for KOSPI blend shadow replay [HYPO][research_only]."""

from __future__ import annotations

from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

from scripts.btrack_phase3_lens_asof_v1 import row_asof_calendar_day  # noqa: E402
from scripts.build_sasang_lens_veto_tier2_v1 import _derive_veto  # noqa: E402
from scripts.market_sasang_lens_engine_v1 import build_market_sasang_lens_payload, load_policy  # noqa: E402
from scripts.run_lens_sasang import _build_payload  # noqa: E402

DEFAULT_POLICY = ROOT / "data/market_sasang/market_sasang_lens_policy_v1.json"


def sasang_row_to_upstream_lens(row: dict[str, Any]) -> dict[str, Any]:
    return _build_payload(row, source="sasang_jsonl_per_date", input_path="inline")


def veto_for_sasang_row(row: dict[str, Any] | None, *, policy_path: Path | None = None) -> dict[str, Any]:
    if not row:
        return {"force_hold": False, "reason_codes": ["missing_row"], "source": "none"}
    upstream = sasang_row_to_upstream_lens(row)
    tier2 = _derive_veto(upstream)
    policy = load_policy(policy_path or DEFAULT_POLICY)
    market = build_market_sasang_lens_payload(
        sasang_lens_doc=upstream,
        policy=policy,
        policy_path=str((policy_path or DEFAULT_POLICY).resolve()),
        source_input_path="inline",
    )
    market_veto = (market.get("veto") or {}) if isinstance(market.get("veto"), dict) else {}
    force_hold = bool(tier2.get("force_hold")) or bool(market_veto.get("force_hold"))
    codes = list(dict.fromkeys(list(tier2.get("veto_reason_codes") or []) + list(market_veto.get("reason_codes") or [])))
    return {
        "force_hold": force_hold,
        "reason_codes": codes,
        "tier2_force_hold": bool(tier2.get("force_hold")),
        "market_force_hold": bool(market_veto.get("force_hold")),
        "entropy_norm": (market.get("uncertainty") or {}).get("entropy_norm_4way"),
        "composite_uncertainty": (market.get("uncertainty") or {}).get("composite_uncertainty"),
        "source": "tier2+market_sasang_lens_v1",
    }


def apply_sasang_veto_to_lenses(lenses: dict[str, Any], *, force_hold: bool) -> dict[str, Any]:
    if not force_hold:
        return lenses
    out = dict(lenses)
    sas = dict(out.get("sasang") or {})
    if sas:
        sas = {**sas, "direction": "neutral", "score": 0.0, "veto_applied": True}
        out["sasang"] = sas
    return out


def veto_for_eval_date(
    eval_date: str,
    sasang_by_day: dict[str, dict[str, Any]],
    *,
    policy_path: Path | None = None,
) -> dict[str, Any]:
    _, row = row_asof_calendar_day(sasang_by_day, eval_date[:10])
    doc = veto_for_sasang_row(row, policy_path=policy_path)
    doc["session_date"] = eval_date[:10]
    doc["matched_calendar_day"] = str((row or {}).get("eval_date") or (row or {}).get("ts_utc") or "")[:10] or None
    return doc
