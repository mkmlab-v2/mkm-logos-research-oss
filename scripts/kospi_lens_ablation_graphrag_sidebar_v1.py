#!/usr/bin/env python3
"""GraphRAG sidebar pack for KOSPI lens ablation — audit path only, no scoring wire [HYPO]."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_MYEONGNI_ROUTER = ROOT / "reports/btrack_lens_graphrag_myeongni_corpus_v1_latest.json"
DEFAULT_SASANG_ROUTER = ROOT / "reports/btrack_lens_graphrag_sasang_kospi_tail_v1_latest.json"

SIDEBAR_POLICY_V1: dict[str, Any] = {
    "prophecy_vote": "none",
    "wires_to_scoring_core": False,
    "non_gating": True,
    "research_only": True,
    "send_gate": "HOLD",
    "max_anchor_ids": 3,
    "note_ko": "해설·감사 경로만 — 결정론 코어·regime_map 비주입",
}


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _slice_router(router: dict[str, Any] | None, *, max_paths: int = 3) -> dict[str, Any] | None:
    if not router:
        return None
    paths = router.get("paths")
    if not isinstance(paths, list):
        paths = []
    trimmed = []
    for p in paths[:max_paths]:
        if not isinstance(p, dict):
            continue
        trimmed.append(
            {
                "path_id": p.get("path_id"),
                "steps": (p.get("steps") or [])[:5],
                "note_ko": (str(p.get("note_ko") or ""))[:120],
                "match_score": p.get("match_score"),
            }
        )
    anchor_ids = router.get("anchor_node_ids")
    if isinstance(anchor_ids, list):
        anchor_ids = anchor_ids[: SIDEBAR_POLICY_V1["max_anchor_ids"]]
    else:
        anchor_ids = []
    return {
        "schema": router.get("schema"),
        "lens_id": router.get("lens_id"),
        "query": router.get("query"),
        "path_count": len(paths),
        "paths_trimmed": trimmed,
        "anchor_node_ids": anchor_ids,
        "direction_score_from_lens": router.get("direction_score_from_lens"),
        "policy": router.get("policy"),
    }


def _estimate_token_savings(path_count: int, *, chars_per_path: int = 280) -> dict[str, Any]:
    """Rough PoC budget — Logos wire profile ~74% savings is reference only."""
    full_corpus_chars = max(path_count, 1) * 1200
    sidebar_chars = path_count * chars_per_path
    if full_corpus_chars <= 0:
        ratio = 0.0
    else:
        ratio = round(max(0.0, 1.0 - (sidebar_chars / full_corpus_chars)), 4)
    return {
        "paths_used": path_count,
        "estimated_sidebar_chars": sidebar_chars,
        "estimated_full_corpus_chars_proxy": full_corpus_chars,
        "estimated_char_savings_ratio": ratio,
        "reference_logos_wire_savings_ratio": 0.74,
        "note_ko": "문자수 프록시 — 실측 토큰은 Ollama wire bench 별도",
    }


def build_graphrag_sidebar_pack(
    *,
    myeongni_router: Path = DEFAULT_MYEONGNI_ROUTER,
    sasang_router: Path = DEFAULT_SASANG_ROUTER,
    enabled: bool = True,
) -> dict[str, Any]:
    my_raw = _read_json(myeongni_router)
    sa_raw = _read_json(sasang_router)
    my_slice = _slice_router(my_raw)
    sa_slice = _slice_router(sa_raw)
    path_count = int((my_slice or {}).get("path_count") or 0) + int((sa_slice or {}).get("path_count") or 0)
    missing: list[str] = []
    if my_slice is None:
        missing.append(str(myeongni_router))
    if sa_slice is None:
        missing.append(str(sasang_router))

    return {
        "schema": "kospi_lens_ablation_graphrag_sidebar_v1",
        "enabled": enabled,
        "policy": dict(SIDEBAR_POLICY_V1),
        "routers": {
            "myeongni": {
                "artifact": str(myeongni_router),
                "loaded": my_slice is not None,
                "slice": my_slice,
            },
            "sasang": {
                "artifact": str(sasang_router),
                "loaded": sa_slice is not None,
                "slice": sa_slice,
            },
        },
        "missing_artifacts": missing,
        "token_budget_proxy": _estimate_token_savings(path_count),
        "reproduce": (
            "py scripts/run_kospi_lens_ablation_backtest_v1.py --graphrag-sidebar on"
        ),
    }


def compare_scoring_invariant(
    doc_without_sidebar: dict[str, Any],
    doc_with_sidebar: dict[str, Any],
) -> dict[str, Any]:
    """Verify GraphRAG sidebar did not alter ablation metrics (FAIL-COMP-004 guard)."""
    arms_a = {a["arm_id"]: a for a in doc_without_sidebar.get("arms") or []}
    arms_b = {a["arm_id"]: a for a in doc_with_sidebar.get("arms") or []}
    per_arm: list[dict[str, Any]] = []
    invariant = True
    for arm_id in sorted(set(arms_a) | set(arms_b)):
        ma = (arms_a.get(arm_id) or {}).get("metrics") or {}
        mb = (arms_b.get(arm_id) or {}).get("metrics") or {}
        soft_a = ma.get("soft_hit_rate")
        soft_b = mb.get("soft_hit_rate")
        dir_a = ma.get("directional_hit_rate")
        dir_b = mb.get("directional_hit_rate")
        soft_delta_pp = None
        dir_delta_pp = None
        if soft_a is not None and soft_b is not None:
            soft_delta_pp = round((soft_b - soft_a) * 100.0, 6)
        if dir_a is not None and dir_b is not None:
            dir_delta_pp = round((dir_b - dir_a) * 100.0, 6)
        arm_ok = soft_delta_pp in (None, 0.0) and dir_delta_pp in (None, 0.0)
        if not arm_ok:
            invariant = False
        per_arm.append(
            {
                "arm_id": arm_id,
                "soft_delta_pp": soft_delta_pp,
                "directional_delta_pp": dir_delta_pp,
                "scoring_invariant": arm_ok,
            }
        )
    overlay_a = doc_without_sidebar.get("four_ai_overlay_uplift_pp_vs_lens3_runtime")
    overlay_b = doc_with_sidebar.get("four_ai_overlay_uplift_pp_vs_lens3_runtime")
    overlay_delta = None
    if overlay_a is not None and overlay_b is not None:
        overlay_delta = round(float(overlay_b) - float(overlay_a), 6)
        if overlay_delta != 0.0:
            invariant = False
    return {
        "schema": "kospi_lens_ablation_graphrag_scoring_invariant_v1",
        "scoring_invariant": invariant,
        "per_arm": per_arm,
        "overlay_uplift_delta_pp": overlay_delta,
        "verdict_ko": (
            "GraphRAG 사이드바 ON/OFF — 코어 스코어 동일 (격벽 OK)"
            if invariant
            else "스코어 불일치 — GraphRAG가 코어에 합선됐을 수 있음"
        ),
    }
