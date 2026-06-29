#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Logos question router 4D shadow — path coherence from verse vectors [HYPO][NON_GATING]."""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_VERSE_4D = ROOT / "reports/logos_verse_4d_bridge_v2_overlay_v1_latest.jsonl"
DEFAULT_STATE_4D = ROOT / "docs/final/artifacts/logos_4d_state_v1_latest.json"
HUMAN_REVIEW_THRESHOLD = 0.8
_AXES = ("S", "L", "K", "M")
SCHEMA = "logos_question_4d_shadow_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_vid(vid: str) -> str:
    v = vid.strip()
    if v.lower().startswith("john."):
        return "Jhn." + v.split(".", 1)[1]
    if v.startswith("verse:"):
        return _normalize_vid(v.split(":", 1)[1])
    return v


def _coerce_4d(raw: Any) -> dict[str, float] | None:
    if not isinstance(raw, dict):
        return None
    try:
        return {k: float(raw[k]) for k in _AXES}
    except (KeyError, TypeError, ValueError):
        return None


def load_verse_4d_index(verse_jsonl: Path, *, max_rows: int = 0) -> dict[str, dict[str, float]]:
    idx: dict[str, dict[str, float]] = {}
    if not verse_jsonl.is_file():
        return idx
    n = 0
    with verse_jsonl.open(encoding="utf-8") as fh:
        for line in fh:
            if max_rows and n >= max_rows:
                break
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                continue
            schema = row.get("schema")
            if schema and schema not in (
                "logos_verse_4d_v1",
                "logos_verse_4d_bridge_v2_overlay_v1",
            ):
                continue
            vid = str(row.get("verse_id") or "")
            vec = _coerce_4d(row.get("vector_4d")) or _coerce_4d(row.get("unified_4d_vector"))
            if vid and vec is not None:
                idx[_normalize_vid(vid)] = vec
            n += 1
    return idx


def _l2(a: dict[str, float], b: dict[str, float]) -> float:
    return math.sqrt(sum((float(a[k]) - float(b[k])) ** 2 for k in _AXES))


def verse_ids_from_path(path: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for step in path.get("steps") or []:
        if isinstance(step, str) and step.startswith("verse:"):
            out.append(_normalize_vid(step.split(":", 1)[1]))
    return out


def score_path_four_d_coherence(
    path: dict[str, Any],
    verse_index: dict[str, dict[str, float]],
) -> dict[str, Any]:
    cites = verse_ids_from_path(path)
    if len(cites) < 2:
        return {
            "four_d_coherence": 1.0,
            "reason": "fewer_than_two_verses",
            "human_review_hint": False,
            "verse_count": len(cites),
        }

    vecs: list[dict[str, float]] = []
    missing: list[str] = []
    for c in cites:
        v = verse_index.get(c)
        if v is None:
            missing.append(c)
        else:
            vecs.append(v)

    if len(vecs) < 2:
        return {
            "four_d_coherence": None,
            "reason": "insufficient_verse_4d_index",
            "missing_verse_ids": missing,
            "human_review_hint": True,
            "verse_count": len(cites),
        }

    jumps = [_l2(vecs[i], vecs[i + 1]) for i in range(len(vecs) - 1)]
    mean_jump = sum(jumps) / len(jumps)
    coherence = round(max(0.0, 1.0 - mean_jump), 4)
    return {
        "four_d_coherence": coherence,
        "mean_l2_jump": round(mean_jump, 6),
        "jump_count": len(jumps),
        "reason": "verse_4d_path_projection",
        "human_review_hint": coherence < HUMAN_REVIEW_THRESHOLD,
        "verse_count": len(cites),
        "indexed_verse_count": len(vecs),
    }


def _composite_rank_score(path: dict[str, Any], shadow: dict[str, Any]) -> float:
    try:
        match = int(path.get("match_score") or 0)
    except (TypeError, ValueError):
        match = 0
    coh = shadow.get("four_d_coherence")
    if isinstance(coh, (int, float)):
        return match * 1000.0 + float(coh) * 100.0
    return match * 1000.0


def enrich_router_with_4d_shadow(
    router: dict[str, Any],
    *,
    verse_index: dict[str, dict[str, float]],
    state_4d: dict[str, Any] | None = None,
    rerank: bool = True,
) -> dict[str, Any]:
    out = dict(router)
    paths = [dict(p) for p in (router.get("paths") or []) if isinstance(p, dict)]
    unit_shadows: list[dict[str, Any]] = []
    coherence_scores: list[float] = []

    for path in paths:
        shadow = score_path_four_d_coherence(path, verse_index)
        path["four_d_shadow"] = shadow
        path["rank_score"] = round(_composite_rank_score(path, shadow), 4)
        unit_shadows.append(
            {
                "path_id": path.get("path_id"),
                "bridge_artifact": path.get("bridge_artifact"),
                **shadow,
            }
        )
        coh = shadow.get("four_d_coherence")
        if isinstance(coh, (int, float)):
            coherence_scores.append(float(coh))

    if rerank and paths:
        paths.sort(
            key=lambda p: (
                -float(p.get("rank_score") or 0),
                -int(p.get("match_score") or 0),
                str(p.get("path_id") or ""),
            )
        )

    scored = coherence_scores
    mean_coherence = round(sum(scored) / len(scored), 4) if scored else None
    below = sum(1 for u in unit_shadows if u.get("human_review_hint") is True)

    quadrant = None
    regime_tag = None
    if state_4d:
        qinfo = state_4d.get("quadrant_info") if isinstance(state_4d.get("quadrant_info"), dict) else {}
        quadrant = qinfo.get("current_quadrant")
        regime_tag = qinfo.get("regime_tag")

    out["paths"] = paths
    out["four_d_shadow_v1"] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "does_not_affect_gate_pass": True,
        "human_review_threshold": HUMAN_REVIEW_THRESHOLD,
        "interpretation_guard": (
            "4D coherence is structural shadow on verse vectors — not prophecy, "
            "not Track A compression, not live trading trigger."
        ),
        "verse_index_path": None,
        "paths_shadowed": len(unit_shadows),
        "mean_four_d_coherence": mean_coherence,
        "human_review_hint_count": below,
        "rerank_applied": bool(rerank),
        "rank_policy": "match_score*1000 + four_d_coherence*100",
        "macro_4d_state": {
            "quadrant": quadrant,
            "regime_tag": regime_tag,
            "artifact_path_rel": "docs/final/artifacts/logos_4d_state_v1_latest.json",
        }
        if state_4d
        else None,
        "units": unit_shadows,
    }
    return out


def load_state_4d(path: Path = DEFAULT_STATE_4D) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return doc if isinstance(doc, dict) and doc.get("schema") == "logos_4d_state_v1" else None


def enrich_router_file(
    router_path: Path,
    *,
    verse_jsonl: Path = DEFAULT_VERSE_4D,
    state_path: Path = DEFAULT_STATE_4D,
    rerank: bool = True,
    in_place: bool = True,
    out_path: Path | None = None,
) -> dict[str, Any]:
    router = json.loads(router_path.read_text(encoding="utf-8-sig"))
    verse_index = load_verse_4d_index(verse_jsonl)
    state = load_state_4d(state_path)
    enriched = enrich_router_with_4d_shadow(router, verse_index=verse_index, state_4d=state, rerank=rerank)
    shadow = enriched.get("four_d_shadow_v1") or {}
    if shadow:
        shadow["verse_index_path"] = str(verse_jsonl.relative_to(ROOT)).replace("\\", "/")
    target = router_path if in_place else (out_path or router_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(enriched, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return enriched


def coherence_gate_check(router: dict[str, Any], *, min_mean: float = 0.5) -> dict[str, Any]:
    shadow = router.get("four_d_shadow_v1") or {}
    mean = shadow.get("mean_four_d_coherence")
    paths = router.get("paths") or []
    has_shadow = bool(shadow.get("paths_shadowed"))
    ok = has_shadow and isinstance(mean, (int, float)) and float(mean) >= min_mean
    return {
        "schema": "logos_question_4d_coherence_gate_v1",
        "ok": ok,
        "mean_four_d_coherence": mean,
        "min_mean_required": min_mean,
        "paths_shadowed": shadow.get("paths_shadowed") or len(paths),
        "human_review_hint_count": shadow.get("human_review_hint_count"),
        "hypothesis_tier": "B",
        "non_gating": True,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Enrich Logos subgraph router with 4D path shadow.")
    ap.add_argument("--router-json", type=Path, required=True)
    ap.add_argument("--verse-4d-jsonl", type=Path, default=DEFAULT_VERSE_4D)
    ap.add_argument("--state-4d-json", type=Path, default=DEFAULT_STATE_4D)
    ap.add_argument("--no-rerank", action="store_true")
    ap.add_argument("--out-json", type=Path, default=None)
    args = ap.parse_args()

    router_path = args.router_json if args.router_json.is_absolute() else ROOT / args.router_json
    if not router_path.is_file():
        print(json.dumps({"ok": False, "error": "router_missing", "path": str(router_path)}))
        return 2

    enriched = enrich_router_file(
        router_path,
        verse_jsonl=args.verse_4d_jsonl if args.verse_4d_jsonl.is_absolute() else ROOT / args.verse_4d_jsonl,
        state_path=args.state_4d_json if args.state_4d_json.is_absolute() else ROOT / args.state_4d_json,
        rerank=not args.no_rerank,
        in_place=args.out_json is None,
        out_path=args.out_json,
    )
    gate = coherence_gate_check(enriched)
    shadow = enriched.get("four_d_shadow_v1") or {}
    print(
        json.dumps(
            {
                "ok": True,
                "paths_shadowed": shadow.get("paths_shadowed"),
                "mean_four_d_coherence": shadow.get("mean_four_d_coherence"),
                "gate_ok": gate.get("ok"),
                "out": str(args.out_json or router_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
