#!/usr/bin/env python3
"""Fact-Lock academic alignment audit 2026Q2 ([HYPO] B-track only).

Separates axes: ops memory harness vs Track A compression vs MOSS evolution vs Latent freeze.
Does NOT claim Track A promotion or live trading readiness.

  py scripts/build_regime_academic_alignment_audit_2026Q2_v1.py
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/regime_academic_alignment_audit_2026Q2_latest.json"

EVOLUTION = ROOT / "docs/final/artifacts/evolution_auto_apply_allowlist_v1_latest.json"
ACTIVE_REPORT = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
OPS_BENCH = ROOT / "reports/mkm_ops_memory_index_token_bench_v1_latest.json"
HARNESS_CONTRACT = ROOT / "reports/multi_res_harness_moss_replay_contract_v1_latest.json"
LOCAL_POINTER = ROOT / "docs/final/LOCAL_MACHINE_POINTER_V1.md"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _compression_summary(doc: dict[str, Any] | None) -> dict[str, Any]:
    if not doc:
        return {"present": False}
    metrics = doc.get("compression_metrics") or {}
    return {
        "present": True,
        "axis": "track_a_frozen_compression_bench",
        "global_token_saving_rate": metrics.get("global_token_saving_rate"),
        "avg_reconstruction_fidelity_jaccard": metrics.get("avg_reconstruction_fidelity_jaccard"),
        "case_count": metrics.get("case_count") or doc.get("run_config", {}).get("case_count"),
        "not_comparable_to": ["harness_1_recall_0_730", "ops_memory_inject_bench"],
    }


def _ops_bench_summary(doc: dict[str, Any] | None) -> dict[str, Any]:
    if not doc:
        return {"present": False}
    off = doc.get("resume_pack_inject_off") or {}
    full = doc.get("full_anchor_slices") or {}
    delta = doc.get("delta_vs_full_slices") or {}
    return {
        "present": True,
        "axis": "ops_memory_inject_bench",
        "inject_off_tokens": off.get("tokens"),
        "full_slices_tokens": full.get("tokens"),
        "reduction_percent": delta.get("reduction_percent"),
        "hypothesis_tag": doc.get("boundary_ack") or "[HYPO]",
        "not_comparable_to": ["track_a_compression_kpi", "harness_1_recall_0_730"],
    }


def _evolution_summary(doc: dict[str, Any] | None) -> dict[str, Any]:
    if not doc:
        return {"present": False}
    rails = doc.get("rails") or {}
    modes = {k: (v or {}).get("auto_apply_mode") for k, v in rails.items()}
    return {
        "present": True,
        "research_only": doc.get("research_only"),
        "rail_auto_apply_modes": modes,
        "forbidden_targets_count": len(doc.get("forbidden_targets") or []),
        "human_signoff_includes_active_report": "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
        in (doc.get("human_signoff_required_for") or []),
        "moss_equivalent_source_rewrite": False,
        "pipeline_shape": "evidence→pytest→human_go",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    evolution = _read_json(EVOLUTION)
    active = _read_json(ACTIVE_REPORT)
    ops_bench = _read_json(OPS_BENCH)
    harness = _read_json(HARNESS_CONTRACT)

    phase1_done = LOCAL_POINTER.is_file() and "Phase1 이동" in LOCAL_POINTER.read_text(encoding="utf-8")

    doc: dict[str, Any] = {
        "schema": "regime_academic_alignment_audit_2026Q2_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "field": "regime_academic_alignment_audit_2026Q2",
        "final_action": "WATCH",
        "freeze_window": {
            "mode": "OPERATION_MODE_B_LEARN_AND_AUDIT",
            "start": "2026-05-16",
            "end": "2026-08-14",
            "source": "docs/final/CENTRAL_AGENT_MEMORY_V1.md",
        },
        "axes": {
            "harness_1_state_externalization": {
                "academic_ref": "arXiv:2606.02373",
                "mkm_maturity": "structural_resonance_not_equivalent",
                "resonance_estimate": "~0.70",
                "ops_harness": _ops_bench_summary(ops_bench),
                "harness_contract_present": harness is not None,
                "overclaim_rejected": [
                    "완전 동치",
                    "recall_0_730_parity",
                    "compression_kpi_as_memory_repair_v2",
                ],
            },
            "moss_self_evolution": {
                "academic_ref": "arXiv:2605.22794",
                "mkm_maturity": "isolated_hold_intentional",
                "evolution_allowlist": _evolution_summary(evolution),
                "global_stop_self_modify": True,
            },
            "latent_agents_internalization": {
                "academic_ref": "arXiv:2604.24881",
                "mkm_maturity": "b_track_hold_roi_review",
                "adapter_mainline_promotion": False,
            },
            "track_a_compression_frozen": _compression_summary(active),
        },
        "raw_repair_dual_reporting": {
            "note": "Never cite repair-only or frozen bench as core harness quality.",
            "track_a_compression": _compression_summary(active),
            "ops_inject_bench": _ops_bench_summary(ops_bench),
        },
        "infra_c_drive": {
            "phase1_status": "done" if phase1_done else "unknown",
            "phase2_scope": ["git_gc", "nemotron_106g_hold_decision_record"],
            "nemotron_106g_decision": "HOLD_wsl_dependency",
            "offload_target": "F:\\workspace_offload",
        },
        "boundary_ack": "B→A·실매매 자동 합선 없음",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
