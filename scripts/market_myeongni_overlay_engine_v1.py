# -*- coding: utf-8 -*-
"""Market Myeongni overlay v1 — finance-domain weights on universal myeongni lens JSON (decoupled from calendar core)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_overlay_policy(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema") != "market_myeongni_overlay_policy_v1":
        raise ValueError("policy schema must be market_myeongni_overlay_policy_v1")
    return doc


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _pick_sign(score: float) -> str:
    if score > 0.08:
        return "bull"
    if score < -0.08:
        return "bear"
    return "neutral"


def apply_market_myeongni_overlay(
    *,
    base_direction: float,
    base_confidence: float,
    state_id: int | None,
    policy: dict[str, Any],
) -> tuple[float, float, dict[str, Any]]:
    ds_scale = _safe_float(policy.get("direction_score_scale"), 1.0)
    cf_scale = _safe_float(policy.get("confidence_scale"), 1.0)
    max_abs = _safe_float(policy.get("max_abs_direction_score"), 1.0)
    if max_abs <= 0.0:
        max_abs = 1.0

    tilt_map = policy.get("state_id_direction_tilt") if isinstance(policy.get("state_id_direction_tilt"), dict) else {}
    tilt = 0.0
    if state_id is not None:
        tilt = _safe_float(tilt_map.get(str(int(state_id))), 0.0)

    raw = base_direction * ds_scale + tilt
    out_d = _clamp(raw, -max_abs, max_abs)
    out_d = _clamp(out_d, -1.0, 1.0)
    out_c = _clamp(base_confidence * cf_scale, 0.0, 1.0)

    applied = {
        "direction_score_scale": ds_scale,
        "confidence_scale": cf_scale,
        "max_abs_direction_score": max_abs,
        "state_id": state_id,
        "state_id_direction_tilt_applied": tilt,
    }
    return out_d, out_c, applied


def build_market_myeongni_lens_payload(
    *,
    myeongni_lens_doc: dict[str, Any],
    policy: dict[str, Any],
    policy_path: str,
    source_input_path: str,
) -> dict[str, Any]:
    scores = myeongni_lens_doc.get("scores") if isinstance(myeongni_lens_doc.get("scores"), dict) else {}
    base_d = _safe_float(scores.get("direction_score"))
    base_c = _safe_float(scores.get("confidence"))

    stream = myeongni_lens_doc.get("myeongri_stream_outputs")
    state_id: int | None = None
    if isinstance(stream, dict) and stream.get("state_id") is not None:
        try:
            state_id = int(stream.get("state_id"))
        except (TypeError, ValueError):
            state_id = None

    out_d, out_c, applied = apply_market_myeongni_overlay(
        base_direction=base_d,
        base_confidence=base_c,
        state_id=state_id,
        policy=policy,
    )

    boundary = policy.get("boundary") if isinstance(policy.get("boundary"), dict) else {}

    return {
        "schema": "market_myeongni_lens_v1",
        "version": "1.0.0",
        "lens_id": "market_myeongni",
        "hypothesis_tier": str(boundary.get("hypothesis_tier") or "B"),
        "boundary_ack": True,
        "scores": {
            "direction_score": round(out_d, 6),
            "confidence": round(out_c, 6),
        },
        "overlay": {
            "policy_path": policy_path,
            "upstream_artifact": source_input_path,
            "upstream_schema": str(myeongni_lens_doc.get("schema") or ""),
            "upstream_lens_id": str(myeongni_lens_doc.get("lens_id") or "myeongni"),
            "base_direction_score": round(base_d, 6),
            "base_confidence": round(base_c, 6),
            "applied": applied,
        },
        "direction_sign": _pick_sign(out_d),
        "note": "Market interpretation overlay on myeongni_independent_lens_latest; universal time engine unchanged.",
    }
