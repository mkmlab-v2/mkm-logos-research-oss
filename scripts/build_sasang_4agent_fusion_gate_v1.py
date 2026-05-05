#!/usr/bin/env python3
"""Build fusion gate for 보명지주/성정불변/병증약리/금화교역."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    art = root / "docs" / "final" / "artifacts"
    protocol_path = art / "sasang_4agent_collision_btrack_protocol_latest.json"
    out_json = art / "sasang_4agent_fusion_gate_latest.json"
    out_md = art / "sasang_4agent_fusion_gate_latest.md"

    protocol = _safe_json(protocol_path)
    if not protocol:
        raise SystemExit(f"missing protocol artifact: {protocol_path}")
    bias = protocol.get("bias_injection") if isinstance(protocol.get("bias_injection"), dict) else {}
    res = protocol.get("results") if isinstance(protocol.get("results"), dict) else {}
    exp = protocol.get("experiment") if isinstance(protocol.get("experiment"), dict) else {}

    mdd_reduction = float(res.get("mdd_reduction_abs") or 0.0)
    hold_ratio = float(res.get("hold_ratio") or 0.0)
    topo_p95 = float(res.get("topological_variance_p95") or 0.0)
    sig_pass = bool(res.get("statistical_significance_pass_p_lt_0_05"))
    ticks = int(exp.get("ticks") or 0)

    # 성정불변: agent priors remain fixed and in safe policy range.
    seongjeong_fixed = bool(
        0.0 <= float(bias.get("macro_window", -1.0)) <= 1.0
        and 0.0 < float(bias.get("mom_weight", 0.0)) <= 2.0
        and 0.5 <= float(bias.get("similarity_threshold", 0.0)) <= 0.999
        and 0.0 < float(bias.get("defense_lambda", 0.0)) <= 10.0
        and -1.0 <= float(bias.get("soeum_veto_threshold", -2.0)) <= -0.1
    )

    # 보명지주: survival-first objective score (capital preservation proxy).
    bo_myeong_score = _clamp01((mdd_reduction / 0.2) * 0.7 + min(1.0, hold_ratio / 0.85) * 0.3)

    # 금화교역: expansion->contraction transition proxy from conflict energy and defense intensity.
    conflict_energy = _clamp01((topo_p95 - 0.7) / 0.3)
    defense_intensity = _clamp01((hold_ratio - 0.5) / 0.4)
    geumhwa_transition_score = _clamp01(0.65 * conflict_energy + 0.35 * defense_intensity)
    geumhwa_state = bool(geumhwa_transition_score >= 0.72)

    # 병증약리: diagnose risk pattern and map to ladder action.
    if geumhwa_state and hold_ratio >= 0.8:
        byeongjeung_stage = "말기"
        yakri_action = "FORCE_HOLD"
    elif geumhwa_state:
        byeongjeung_stage = "중기"
        yakri_action = "HEDGE_AND_REDUCE"
    elif topo_p95 >= 0.85:
        byeongjeung_stage = "초기"
        yakri_action = "REDUCE_EXPOSURE"
    else:
        byeongjeung_stage = "안정"
        yakri_action = "KEEP_CONTROLLED_BRIDGE"

    checks = {
        "seongjeong_bulbyeon_fixed": seongjeong_fixed,
        "bo_myeong_jiju_score_gte_0_45": bo_myeong_score >= 0.45,
        "byeongjeung_yakri_mapping_valid": yakri_action in {"KEEP_CONTROLLED_BRIDGE", "REDUCE_EXPOSURE", "HEDGE_AND_REDUCE", "FORCE_HOLD"},
        "geumhwa_transition_detectable": geumhwa_transition_score >= 0.55,
        "protocol_significance_pass": sig_pass,
        "sample_size_gte_300": ticks >= 300,
    }

    decision = "FUSION_GATE_PASS" if all(checks.values()) else "FUSION_GATE_HOLD"
    payload = {
        "schema": "sasang_4agent_fusion_gate_v1",
        "generated_at_utc": _now_utc(),
        "mode": "research_only",
        "policy_label": "NON_GATING",
        "source_ref": str(protocol_path).replace("\\", "/"),
        "fusion": {
            "bo_myeong_jiju": {"score": bo_myeong_score, "objective": "capital_preservation_first"},
            "seongjeong_bulbyeon": {"fixed": seongjeong_fixed, "priors": bias},
            "byeongjeung_yakri": {"stage": byeongjeung_stage, "action": yakri_action},
            "geumhwa_transition": {
                "score": geumhwa_transition_score,
                "state": geumhwa_state,
                "conflict_energy": conflict_energy,
                "defense_intensity": defense_intensity,
            },
        },
        "checks": checks,
        "decision": decision,
    }

    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [
        "# Sasang 4-Agent Fusion Gate",
        "",
        f"- generated_at_utc: `{payload['generated_at_utc']}`",
        f"- decision: `{decision}`",
        "",
        "## Fusion",
        f"- bo_myeong_jiju.score: `{bo_myeong_score}`",
        f"- seongjeong_bulbyeon.fixed: `{seongjeong_fixed}`",
        f"- byeongjeung_yakri.stage: `{byeongjeung_stage}`",
        f"- byeongjeung_yakri.action: `{yakri_action}`",
        f"- geumhwa_transition.score: `{geumhwa_transition_score}`",
        f"- geumhwa_transition.state: `{geumhwa_state}`",
        "",
        "## Checks",
    ]
    for k, v in checks.items():
        md.append(f"- {k}: `{v}`")
    md.append("")
    out_md.write_text("\n".join(md), encoding="utf-8")
    print(str(out_json))
    print(str(out_md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

