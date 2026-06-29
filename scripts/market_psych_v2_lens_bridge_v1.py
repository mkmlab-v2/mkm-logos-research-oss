#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bridge market_psych v2 mapping -> sasang_independent_lens-compatible upstream (B-track)."""

from __future__ import annotations

from typing import Any


def sasang_upstream_stub_from_v2_mapping(
    mapping: dict[str, Any],
    *,
    eval_date: str = "",
) -> dict[str, Any]:
    """Build upstream doc for market_sasang_lens_engine_v1.build_market_sasang_lens_payload."""
    mr = dict(mapping.get("machine_readables") or {})
    fusion = float(mapping.get("fusion_direction_score") or 0.0)
    if "direction_score" not in mr:
        mr["direction_score"] = float(mr.get("direction_score") or fusion)
    direction = float(mr.get("direction_score") or fusion)
    axis = mapping.get("axis_normalized") or {}
    spread = 0.0
    if axis:
        spread = max(float(v) for v in axis.values()) - min(float(v) for v in axis.values())
    confidence = max(0.12, min(0.95, 0.45 + 0.35 * spread + 0.2 * abs(direction)))
    bj = mapping.get("byungjeung") or {}
    regime = str(bj.get("byungjeung_state") or "watch")
    return {
        "schema": "sasang_independent_lens_v0",
        "version": "0.2.0",
        "lens_id": "sasang",
        "engine_id": "market_psych_v2_lens_bridge_v1",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "a_track_autobind_forbidden": True,
        "scores": {
            "direction_score": round(direction, 8),
            "confidence": round(confidence, 8),
        },
        "sasang_stream_outputs": {
            "regime_hypothesis": regime,
            "machine_readables": mr,
            "mapping_target": mapping.get("mapping_target"),
            "rationale": (
                "market_psych v2 manifest bridge; heat/cold/vol aligned with "
                "market_psych_to_sasang_axis_manifest_v2 — not sasang dynamics JSONL."
            ),
        },
        "b_track_axis_scores_v1": {
            "schema": "sasang_b_track_axis_scores_v1",
            "version": "0.1.0",
            "heat_proxy": mr.get("heat_proxy"),
            "cold_proxy": mr.get("cold_proxy"),
            "volatility_rarefaction_proxy": mr.get("volatility_rarefaction_proxy"),
            "thermal_imbalance_proxy": round(abs(direction), 8),
            "disclaimer_ko": "v2 bridge proxy; not cohort DNA.",
        },
        "market_psych_v2_axis_normalized": axis,
        "byungjeung_v2": bj,
        "provenance": {
            "source": "market_psych_v2",
            "eval_date": eval_date,
            "bridge": "market_psych_v2_lens_bridge_v1",
        },
        "note": "B-track observation; market_sasang lens input via v2 machine_readables.",
    }


def load_latest_v2_mapping(map_json: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    if "latest" in map_json:
        block = map_json["latest"] or {}
        return str(block.get("date") or ""), dict(block.get("mapping") or {})
    timeline = map_json.get("timeline") or []
    if not timeline:
        raise ValueError("map json has no latest or timeline")
    last = timeline[-1]
    return str(last.get("date") or ""), dict(last.get("mapping") or {})
