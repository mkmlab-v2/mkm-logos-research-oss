#!/usr/bin/env python3
"""Aggregate Saving the News Phase 1–3b closure snapshot (research_only)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
OUT_JSON = ART / "saving_the_news_internal_roadmap_closure_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def build_closure() -> dict[str, Any]:
    p1 = _read(ART / "saving_the_news_phase1_poc_status_v1_latest.json")
    p2 = _read(ART / "saving_the_news_phase2_poc_status_v1_latest.json")
    p3 = _read(ART / "saving_the_news_phase3_poc_status_v1_latest.json")
    p3b = _read(ART / "saving_the_news_phase3b_poc_status_v1_latest.json")
    p4 = _read(ART / "saving_the_news_phase4_dual_arch_status_v1_latest.json")
    news_rt = _read(ART / "saving_the_news_news_rt_bench_result_v1_latest.json")
    news_hp = _read(ART / "saving_the_news_news_hp_rt_bench_result_v1_latest.json")
    news_evo = _read(ART / "saving_the_news_news_evo_bench_result_v1_latest.json")
    legal = _read(ART / "saving_the_news_legal_counsel_signoff_v1_latest.json")
    design_ui = _read(ART / "saving_the_news_design_ui_status_v1_latest.json")

    p3b_complete = p3b.get("status") == "POC_COMPLETE"
    design_ui_complete = design_ui.get("status") == "DESIGN_UI_POC_COMPLETE"
    p4_complete = p4.get("status") == "POC_COMPLETE"
    phases_complete = all(
        [
            p1.get("status") == "POC_COMPLETE" or (p1.get("exit_criteria") or {}).get("promote_to_phase2"),
            p2.get("status") == "POC_COMPLETE",
            p3.get("status") == "POC_COMPLETE",
            p3b_complete,
            p4_complete,
        ]
    )

    return {
        "schema": "saving_the_news_internal_roadmap_closure_v1",
        "generated_at_utc": _utc_now(),
        "lane": "research_only",
        "hypothesis_tier": "B",
        "ready_for_external_send": False,
        "internal_poc_roadmap_complete": phases_complete,
        "promote_track_a_or_live": False,
        "phases": {
            "phase1_poc_status_v1": {
                "status": p1.get("status", "UNKNOWN"),
                "promote": (p1.get("exit_criteria") or {}).get("promote_to_phase2"),
                "ready_for_external_send": False,
            },
            "phase2_poc_status_v1": {
                "status": p2.get("status", "UNKNOWN"),
                "promote": (p2.get("exit_criteria") or {}).get("promote_to_phase3"),
                "ready_for_external_send": False,
            },
            "phase3_poc_status_v1": {
                "status": p3.get("status", "UNKNOWN"),
                "promote": None,
                "ready_for_external_send": False,
            },
            "phase3b_hyper_personal_poc_status_v1": {
                "status": p3b.get("status", "UNKNOWN"),
                "promote": None,
                "ready_for_external_send": False,
                "shadow_observation_only": True,
            },
            "phase4_dual_arch_poc_status_v1": {
                "status": p4.get("status", "UNKNOWN"),
                "promote": None,
                "ready_for_external_send": False,
                "shadow_observation_only": True,
                "blueprint_section": "§11",
            },
        },
        "news_rt": {
            "measurement_status": news_rt.get("measurement_status"),
            "token_saving_ratio": (news_rt.get("kpi") or {}).get("token_saving_ratio"),
            "observation_row_count": news_rt.get("observation_row_count"),
        },
        "news_hp_rt": {
            "measurement_status": news_hp.get("measurement_status"),
            "token_saving_ratio_baseline": (news_hp.get("kpi") or {}).get(
                "token_saving_ratio_baseline_news_rt"
            ),
            "token_saving_ratio_hp_weighted": (news_hp.get("kpi") or {}).get(
                "token_saving_ratio_hp_weighted"
            ),
            "delta_hp_minus_baseline": (news_hp.get("delta_vs_news_rt_baseline") or {}).get(
                "token_saving_ratio_delta_hp_minus_baseline"
            ),
            "interpretation": "research_only_delta",
        },
        "news_evo_bench": {
            "measurement_status": news_evo.get("measurement_status"),
            "L_total_hypo": (news_evo.get("composite_hypo") or {}).get("L_total_hypo"),
            "interpretation": "offline_4axis_aggregate_not_promotion_gate",
        },
        "legal_posture_status": legal.get("status", "PRIMARY_SOURCE_REVIEWED_PENDING_COUNSEL"),
        "counsel_signoff_required": True,
        "layer_b_appendix_present": (ART / "saving_the_news_perspective_appendix_v1_latest.json").is_file(),
        "showroom": {
            "html": (
                "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/"
                "public_showroom_saving_the_news_matrix_v1.html"
            ),
            "smoke_report": "reports/saving_the_news_showroom_local_smoke_v1_latest.json",
        },
        "design_ui": {
            "status": design_ui.get("status", "UNKNOWN"),
            "poc_complete": design_ui_complete,
            "surfaces": design_ui.get("surfaces") or {},
            "exit_criteria": design_ui.get("exit_criteria") or {},
            "ready_for_external_send": False,
            "shadow_observation_only": True,
        },
        "explicit_next": [
            "§11 NEWS-EVO-BENCH contract frozen; DSPy/GEPA runtime TBD",
            "Daily: pre-news + RadioOp intake-only; weekly NEWS-HP-RT refresh (not_before 2026-06-08)",
            "Design UI local PoC: Run-SavingTheNewsDesignUiSync_v1.ps1 — mkmlife deploy manual (-DeployMkmlifeAssets)",
            "CMS publish lock product (not shipped)",
        ],
        "refresh_gate_ref": "docs/final/artifacts/saving_the_news_news_hp_rt_refresh_gate_v1_latest.json",
        "refs": {
            "blueprint": "docs/research/saving_the_news_blueprint_v1.md",
            "blueprint_section_10": "docs/research/saving_the_news_blueprint_v1.md",
            "phase3b_status": "docs/final/artifacts/saving_the_news_phase3b_poc_status_v1_latest.json",
            "hyper_personal_intake": "docs/final/artifacts/hyper_personal_news_intake_v1_latest.json",
            "news_evo_bench_contract": "docs/final/artifacts/fixtures/news_evo_bench_contract_v1.example.json",
            "phase4_dual_arch": "docs/final/artifacts/saving_the_news_phase4_dual_arch_status_v1_latest.json",
            "design_ui_status": "docs/final/artifacts/saving_the_news_design_ui_status_v1_latest.json",
            "perplexity_grounding": "docs/research/saving_the_news_perplexity_external_grounding_v1.md",
            "track_c_onepager": "docs/final/artifacts/track_c_saving_the_news_offer_onepager_v1_latest.md",
        },
    }


def main() -> int:
    doc = build_closure()
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT_JSON} complete={doc['internal_poc_roadmap_complete']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
