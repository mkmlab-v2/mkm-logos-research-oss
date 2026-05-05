# -*- coding: utf-8 -*-
"""rule_school_mkm_4d_v1 정책 로드 — 표면 vs 지장간 4D 블렌드 가중."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "data" / "myeongni" / "rule_school_mkm_4d_v1.json"


def blend_vector_4d_rule_school(
    vector_surface: dict[str, float],
    vector_jijangan: dict[str, float],
    w_surface: float,
    w_jijangan: float,
) -> dict[str, float]:
    """S,L,K,M 에 대해 가중 합 후 재정규화(합 1)."""
    keys = ("S", "L", "K", "M")
    out = {
        k: w_surface * float(vector_surface.get(k, 0.0))
        + w_jijangan * float(vector_jijangan.get(k, 0.0))
        for k in keys
    }
    ssum = sum(out.values())
    if ssum <= 0.0:
        return {k: 0.25 for k in keys}
    return {k: out[k] / ssum for k in keys}


def load_rule_school_mkm_4d_v1(path: Path | None = None) -> dict[str, Any]:
    p = path or DEFAULT_POLICY
    doc = json.loads(p.read_text(encoding="utf-8"))
    if doc.get("schema") != "rule_school_mkm_4d_v1":
        raise ValueError("policy schema must be rule_school_mkm_4d_v1")
    vb = doc.get("vector_4d_blend") or {}
    ws = float(vb.get("w_surface", 0.0))
    wj = float(vb.get("w_jijangan", 0.0))
    if ws < 0 or wj < 0:
        raise ValueError("blend weights must be non-negative")
    if abs(ws + wj - 1.0) > 1e-6:
        raise ValueError(f"w_surface + w_jijangan must sum to 1; got {ws + wj}")
    return doc
