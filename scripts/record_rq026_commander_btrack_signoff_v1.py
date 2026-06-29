#!/usr/bin/env python3
"""Record commander B-track sign-off for RQ-026 (temperament sim scope vs explicit HOLD)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "docs/final/artifacts/rq026_commander_btrack_signoff_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p.resolve()).replace("\\", "/")


def main() -> int:
    ap = argparse.ArgumentParser(description="RQ-026 commander B-track signoff")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--signoff-by", default="commander")
    args = ap.parse_args()

    phase2 = ROOT / "docs/final/artifacts/sasang_temperament_agents_phase2_eval_v1_latest.json"
    promotion = ROOT / "docs/final/artifacts/rq026_pathology_matrix_v1_2_btrack_promotion_v1_latest.json"
    promotion_v1_1 = ROOT / "docs/final/artifacts/rq026_pathology_matrix_v1_1_btrack_promotion_v1_latest.json"
    phase2_doc: dict[str, Any] = {}
    promotion_doc: dict[str, Any] = {}
    if phase2.is_file():
        phase2_doc = json.loads(phase2.read_text(encoding="utf-8"))
    if promotion.is_file():
        promotion_doc = json.loads(promotion.read_text(encoding="utf-8"))

    default_matrix = ROOT / "experiments/sasang_temperament_agents_v1/specs/pathology_transition_matrix_v1_2.json"

    matrix_promotion_snapshot = None
    if promotion_doc:
        matrix_promotion_snapshot = {
            "promoted_matrix_version": promotion_doc.get("promoted_matrix_version"),
            "promotion_utc": promotion_doc.get("promotion_utc"),
        }

    doc: dict[str, Any] = {
        "schema": "rq026_commander_btrack_signoff_v1",
        "signoff_utc": _utc(),
        "signoff_by": args.signoff_by,
        "hypothesis_tier": "B",
        "research_only": True,
        "rq_id": "RQ-026",
        "approved": {
            "rq026_btrack_continue": True,
            "temperament_sim_namespace": _rel(
                ROOT / "experiments/sasang_temperament_agents_v1"
            ),
            "pathology_matrix_coupled_sim": True,
            "default_pathology_matrix_v1_2": True,
            "eval_axis_separation_permanent": True,
            "phase2_eval_separation_ok": phase2_doc.get("eval_separation_ok"),
            "four_agent_not_conflation_with_4ai_core": True,
        },
        "explicit_hold": {
            "ng40_codec_merge": False,
            "active_report_kpi_update": False,
            "ms_paste_hwpx_kpi_body": False,
            "track_a_live_trading_auto_merge": False,
            "ohlcv_hit_rate_as_rq026_promotion_gate": False,
            "constitution_body_edit": False,
            "agi_consciousness_marketing": False,
            "patient_care_clinical_gating_auto_merge": False,
        },
        "evidence_pointers": {
            "research_open_questions_rq026": _rel(ROOT / "docs/research/RESEARCH_OPEN_QUESTIONS_V1.md"),
            "sim_report": _rel(ROOT / "reports/sasang_temperament_agents_sim_v1_latest.json"),
            "phase2_eval": _rel(phase2),
            "eval_contract": _rel(
                ROOT
                / "experiments/sasang_temperament_agents_v1/specs/temperament_eval_axes_contract_v1.json"
            ),
            "pathology_matrix": _rel(default_matrix),
            "pathology_matrix_baseline_v1_1": _rel(
                ROOT
                / "experiments/sasang_temperament_agents_v1/specs/pathology_transition_matrix_v1_1.json"
            ),
            "pathology_matrix_baseline_v1": _rel(
                ROOT
                / "experiments/sasang_temperament_agents_v1/specs/pathology_transition_matrix_v1.json"
            ),
            "pathology_matrix_promotion_v1_2": _rel(promotion) if promotion.is_file() else None,
            "pathology_matrix_promotion_v1_1": _rel(promotion_v1_1) if promotion_v1_1.is_file() else None,
            "matrix_sweep": _rel(
                ROOT / "docs/final/artifacts/sasang_temperament_agents_matrix_sweep_v1_latest.json"
            ),
            "paired_stats_guard": _rel(
                ROOT
                / "docs/final/artifacts/session_myeongni_vs_agct_paired_stats_v1_latest.json"
            ),
        },
        "next_btrack_only": [
            "Run run_sasang_temperament_agents_rq026_chain_v1.py after env refresh",
            "Extend matrix/spec only under experiments/sasang_temperament_agents_v1/",
            "RQ-026 CLOSED only after separate human gate — not from sim scores alone",
        ],
        "boundary_ko": (
            "본 signoff는 B-track 연구 레일 지속만 승인. Track A·NG-40·실매매·MS paste·"
            "압축 커널 합선·AGI/의식 완성 주장을 승인하지 않음."
        ),
    }
    if matrix_promotion_snapshot is not None:
        doc["matrix_promotion_snapshot"] = matrix_promotion_snapshot

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": _rel(args.out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
