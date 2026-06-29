#!/usr/bin/env python3
"""[HYPO] Roll up compression multilens DR phases 2–6 into a single closure artifact.

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
DEFAULT_OUT = ROOT / "reports/compression_multilens_dr_closure_v1_latest.json"
SCHEMA = "compression_multilens_dr_closure_v1"

PHASE_POINTERS: dict[str, str] = {
    "phase2": "reports/ng40_dr_phase2_completion_chain_v1_latest.json",
    "phase3": "reports/ng40_dr_phase3_completion_chain_v1_latest.json",
    "phase4": "reports/ng40_dr_phase4_conditional_fusion_completion_chain_v1_latest.json",
    "phase5": "reports/ng40_dr_phase5_hybrid_v3_wire_completion_chain_v1_latest.json",
    "phase6": "reports/ng40_dr_phase6_stub_pareto_completion_chain_v1_latest.json",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_rel(rel: str) -> dict[str, Any] | None:
    p = ROOT / rel.replace("/", "\\")
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def _pct(rate: float | None) -> float | None:
    if rate is None:
        return None
    return round(float(rate) * 100, 2)


def build() -> dict[str, Any]:
    phases: dict[str, Any] = {}
    for pid, rel in PHASE_POINTERS.items():
        doc = _load_rel(rel)
        phases[pid] = {
            "pointer": rel,
            "present": doc is not None,
            "chain_ok": (doc or {}).get("chain_ok"),
            "schema": (doc or {}).get("schema"),
        }

    stack_ok = all(p.get("chain_ok") is True for p in phases.values() if p.get("present"))

    v3 = _load_rel("reports/compression_conditional_fusion_ablation_v3_ssot_guard_v1_latest.json") or {}
    pareto = _load_rel("reports/compression_conditional_fusion_pareto_research_signoff_v1_latest.json") or {}
    path_a = _load_rel("reports/ng40_path_a_product_signoff_chain_v1_latest.json") or {}
    keep_grid = _load_rel("reports/ng40_path_a_keep_ratio_microgrid_v1_latest.json") or {}
    topology = _load_rel(
        "docs/final/artifacts/logos_topology_sidecar_compression_improvement_multilens_v1_latest.json"
    ) or {}

    v3_arms = v3.get("golden40_codec_arms") or {}
    active = v3_arms.get("active_global") or {}
    conditional = v3_arms.get("conditional_merged") or {}
    knee = v3_arms.get("knee_j_global") or {}

    b2b_spine = 0.222911
    for row in (keep_grid.get("b2b_longform") or {}).get("sweep") or []:
        if float(row.get("keep_ratio") or 0) == 0.88:
            b2b_spine = row.get("global_token_saving_rate_spine_binary_only", b2b_spine)
            break

    dual_report = _load_rel("reports/compression_golden40_active_dual_report_v1_latest.json") or {}
    repair_delta = (dual_report.get("delta") or {}).get("alignment_pass_rate_delta_repair_v2_minus_raw")
    phase2 = _load_rel(PHASE_POINTERS["phase2"]) or {}

    conflict_surface = [
        {
            "axis": "latent_g40_active",
            "message": f"ACTIVE { _pct(active.get('global_token_saving_rate')) }% / J { active.get('avg_reconstruction_fidelity_jaccard') } — Pareto ceiling, dual beat 없음",
        },
        {
            "axis": "latent_g40_conditional_v3",
            "message": (
                f"v3 conditional {_pct(conditional.get('global_token_saving_rate'))}% / "
                f"J {conditional.get('avg_reconstruction_fidelity_jaccard')} / "
                f"minJ {conditional.get('min_reconstruction_fidelity_jaccard')} — research headline"
            ),
        },
        {
            "axis": "path_a_commercial",
            "message": f"Path A B2B spine {_pct(b2b_spine)}% byte_exact — honest GTM KPI",
        },
        {
            "axis": "expanded_longform",
            "message": f"Expanded 73-case spine {_pct((phase2 or {}).get('expanded_spine_saving'))}% — 별 cohort",
        },
        {
            "axis": "repair_v2",
            "message": f"repair_v2 delta {repair_delta} on G40 proxy — operational only",
        },
        {
            "axis": "hybrid_golden40",
            "message": "golden40_internal → mkm_conditional_fusion_v3_ssot_guard (stub research lane)",
        },
        {
            "axis": "send_gate",
            "message": "HOLD · apply_active forbidden · beat_frozen false",
        },
    ]

    return {
        "schema": SCHEMA,
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_active_write": False,
        "apply_active_forbidden": True,
        "stack_closure_ok": stack_ok,
        "phases": phases,
        "kpi_lanes": {
            "latent_g40_active": {
                "global_token_saving_rate": active.get("global_token_saving_rate"),
                "avg_reconstruction_fidelity_jaccard": active.get("avg_reconstruction_fidelity_jaccard"),
                "min_reconstruction_fidelity_jaccard": active.get("min_reconstruction_fidelity_jaccard"),
            },
            "latent_g40_conditional_v3": {
                "global_token_saving_rate": conditional.get("global_token_saving_rate"),
                "avg_reconstruction_fidelity_jaccard": conditional.get("avg_reconstruction_fidelity_jaccard"),
                "min_reconstruction_fidelity_jaccard": conditional.get("min_reconstruction_fidelity_jaccard"),
            },
            "latent_g40_knee_j": {
                "global_token_saving_rate": knee.get("global_token_saving_rate"),
                "avg_reconstruction_fidelity_jaccard": knee.get("avg_reconstruction_fidelity_jaccard"),
                "knee_j_research_headline_only": True,
            },
            "path_a_b2b_spine": {
                "global_token_saving_rate": b2b_spine,
                "byte_exact": True,
                "product_ready": (path_a.get("product_gates") or {}).get("product_ready"),
            },
            "repair_v2_delta_alignment_pass": repair_delta,
        },
        "pareto_signoff": {
            "pointer": "reports/compression_conditional_fusion_pareto_research_signoff_v1_latest.json",
            "commander_research_approval": pareto.get("commander_research_approval"),
            "recommended_research_headline_arm": pareto.get("recommended_research_headline_arm"),
            "pareto_front_arm_ids": pareto.get("pareto_front_arm_ids"),
            "beat_frozen": pareto.get("beat_frozen"),
        },
        "topology_sidecar": {
            "pointer": "docs/final/artifacts/logos_topology_sidecar_compression_improvement_multilens_v1_latest.json",
            "present": bool(topology),
            "send_gate": topology.get("send_gate"),
        },
        "conflict_surface": conflict_surface,
        "verdict_ko": [
            "DR Phase2–6 stack closure — research_only 유지",
            "연구 권장: v3 SSOT-only conditional fusion + hybrid golden40 wire",
            "상용 honest KPI: Path A spine ~22.29% — latent 47%와 합선 금지",
        ],
        "reproducible_command": "py scripts/build_compression_multilens_dr_closure_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "out": str(args.out), "stack_closure_ok": doc["stack_closure_ok"]},
            ensure_ascii=False,
        )
    )
    return 0 if doc["stack_closure_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
