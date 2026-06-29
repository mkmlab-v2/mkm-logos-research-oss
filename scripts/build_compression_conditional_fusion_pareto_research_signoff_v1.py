#!/usr/bin/env python3
"""[HYPO] Pareto research signoff for conditional fusion v3 (NOT ACTIVE apply).

research_only · send_gate HOLD · apply_active forbidden.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/compression_conditional_fusion_pareto_research_signoff_v1_latest.json"
V2_ABLATION = ROOT / "reports/compression_conditional_fusion_ablation_v2_codec_rerun_v1_latest.json"
V3_ABLATION = ROOT / "reports/compression_conditional_fusion_ablation_v3_ssot_guard_v1_latest.json"
WIRE_SPIKE = ROOT / "reports/compression_hybrid_router_v3_wire_spike_v1_latest.json"
HYBRID_SPEC = ROOT / "docs/final/artifacts/compression_hybrid_router_spec_v1.json"
SCHEMA = "compression_conditional_fusion_pareto_research_signoff_v1"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _arm_point(arm_id: str, label: str, metrics: dict[str, Any], *, recommended: bool = False) -> dict[str, Any]:
    saving = float(metrics.get("global_token_saving_rate") or 0)
    mean_j = float(metrics.get("avg_reconstruction_fidelity_jaccard") or 0)
    min_j = float(metrics.get("min_reconstruction_fidelity_jaccard") or 0)
    return {
        "arm_id": arm_id,
        "label": label,
        "global_token_saving_rate": saving,
        "avg_reconstruction_fidelity_jaccard": mean_j,
        "min_reconstruction_fidelity_jaccard": min_j,
        "recommended_research_headline": recommended,
    }


def _dominates(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """Pareto on (min_j, mean_j, saving) — higher is better on all axes."""
    axes = (
        "min_reconstruction_fidelity_jaccard",
        "avg_reconstruction_fidelity_jaccard",
        "global_token_saving_rate",
    )
    ge_all = all(float(a[k]) >= float(b[k]) for k in axes)
    gt_any = any(float(a[k]) > float(b[k]) for k in axes)
    return ge_all and gt_any


def _pareto_front(arms: list[dict[str, Any]]) -> list[str]:
    front: list[str] = []
    for a in arms:
        dominated = False
        for b in arms:
            if a["arm_id"] == b["arm_id"]:
                continue
            if _dominates(b, a):
                dominated = True
                break
        if not dominated:
            front.append(str(a["arm_id"]))
    return front


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--human-approve-research", action="store_true")
    ap.add_argument("--reviewer", default="commander")
    ap.add_argument("--note", default="")
    args = ap.parse_args()

    missing = [p for p in (V2_ABLATION, V3_ABLATION) if not p.is_file()]
    if missing:
        print(f"missing required ablation artifacts: {missing}", file=sys.stderr)
        return 2

    v2 = _load(V2_ABLATION)
    v3 = _load(V3_ABLATION)
    wire = _load(WIRE_SPIKE) if WIRE_SPIKE.is_file() else {}
    spec = _load(HYBRID_SPEC) if HYBRID_SPEC.is_file() else {}

    v3_arms = v3.get("golden40_codec_arms") or {}
    frozen = v3.get("frozen_baseline") or {}

    arms = [
        _arm_point("active_global", "ACTIVE caps global (frozen competitor)", v3_arms.get("active_global") or {}),
        _arm_point("knee_j_global", "knee_j_first global (research headline arm)", v3_arms.get("knee_j_global") or {}),
        _arm_point(
            "conditional_v2_merged",
            "v2 broad conditional merge",
            (v2.get("golden40_codec_arms") or {}).get("conditional_merged") or {},
        ),
        _arm_point(
            "conditional_v3_ssot_merged",
            "v3 SSOT-only conditional merge (recommended)",
            v3_arms.get("conditional_merged") or {},
            recommended=True,
        ),
    ]

    pareto_front = _pareto_front(arms)
    beat = v3.get("beat_check_conditional_vs_frozen") or {}

    golden40_route = None
    for row in spec.get("corpus_bindings") or spec.get("corpus_routes") or []:
        if row.get("corpus_id") == "golden40_internal":
            golden40_route = row
            break

    g40_wire = next(
        (c for c in wire.get("corpora") or [] if c.get("corpus_id") == "golden40_internal"),
        {},
    )
    g40_raw = (g40_wire.get("result") or {}).get("raw") or {}
    base_spike_path = ROOT / "reports/compression_hybrid_router_spike_v1_latest.json"
    base_spike = _load(base_spike_path) if base_spike_path.is_file() else {}
    old_g40 = next(
        (c for c in base_spike.get("corpora") or [] if c.get("corpus_id") == "golden40_internal"),
        {},
    )
    old_j = float((old_g40.get("result") or {}).get("raw", {}).get("mean_jaccard_proxy") or 0)

    signoff = {
        "schema": SCHEMA,
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_active_write": False,
        "commander_research_approval": bool(args.human_approve_research),
        "reviewer": args.reviewer if args.human_approve_research else None,
        "note": args.note or "Pareto research headline only — ACTIVE apply forbidden",
        "frozen_baseline": {
            "global_token_saving_rate": frozen.get("global_token_saving_rate"),
            "avg_reconstruction_fidelity_jaccard": frozen.get("avg_reconstruction_fidelity_jaccard"),
        },
        "pareto_arms": arms,
        "pareto_front_arm_ids": pareto_front,
        "recommended_research_headline_arm": "conditional_v3_ssot_merged",
        "recommended_routing_policy": "pick_policy_ssot_only",
        "recommended_hybrid_backend": "mkm_conditional_fusion_v3_ssot_guard",
        "beat_frozen": bool(beat.get("beat_frozen")),
        "beat_frozen_reason": beat.get("reason"),
        "apply_active_forbidden": True,
        "active_apply_allowed": False,
        "active_apply_recommended": False,
        "track_a_promotion_allowed": False,
        "research_signoff_ready": bool(args.human_approve_research),
        "knee_j_research_headline_only": True,
        "v3_vs_v2": v3.get("v2_compare"),
        "hybrid_wire": {
            "present": bool(wire),
            "golden40_mean_j_before": old_j if old_j else None,
            "golden40_mean_j_after": g40_raw.get("mean_jaccard_proxy"),
            "spike_pointer": str(WIRE_SPIKE.relative_to(ROOT)).replace("\\", "/") if wire else None,
        },
        "golden40_hybrid_route": golden40_route,
        "evidence_pointers": {
            "v2_ablation": str(V2_ABLATION.relative_to(ROOT)).replace("\\", "/"),
            "v3_ablation": str(V3_ABLATION.relative_to(ROOT)).replace("\\", "/"),
            "hybrid_spec": str(HYBRID_SPEC.relative_to(ROOT)).replace("\\", "/"),
        },
        "verdict_ko": [
            "ACTIVE 47% dual-axis beat 없음 — apply_active 금지 유지",
            "연구 헤드라인: knee_j_first + v3 SSOT-only conditional merge",
            "하이브리드 golden40 → mkm_conditional_fusion_v3_ssot_guard (stub research lane)",
            f"Pareto front: {', '.join(pareto_front)}",
        ],
        "forbidden": [
            "merge conditional with ACTIVE 47% headline without beat_frozen",
            "apply_active from pareto signoff",
            "Track A promotion from repair-only or conditional uplift alone",
        ],
        "reproducible_command": (
            "py scripts/build_compression_conditional_fusion_pareto_research_signoff_v1.py "
            "--human-approve-research --reviewer commander"
        ),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(signoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out), "pareto_front": pareto_front}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
