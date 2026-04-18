# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.78, L:0.9, K:0.58, M:0.52}
# Balance: 87
# Purpose: Emit a single JSON pointer map from B-track insight sources to promotion artifacts (no merge into scores).
# Keywords: btrack, bridge, index, signoff, notebooklm, gates
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "btrack_insight_promotion_bridge_index_v1_latest.json"
DEFAULT_INVENTORY = ROOT / "docs" / "final" / "artifacts" / "btrack_insight_bridge_inventory_v1_latest.json"

SCHEMA = "btrack_insight_promotion_bridge_index_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    return str(p.relative_to(ROOT)).replace("\\", "/") if p.is_relative_to(ROOT) else str(p)


def _optional_link(p: Path) -> dict[str, Any]:
    return {"path": _rel(p), "exists": p.is_file() or p.is_dir()}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--inventory",
        type=Path,
        default=DEFAULT_INVENTORY,
        help="Optional latest inventory JSON to embed as reference (skipped if missing).",
    )
    args = ap.parse_args()

    inventory_ref: dict[str, Any] | None = None
    if args.inventory.is_file():
        inventory_ref = {"path": _rel(args.inventory), "exists": True}

    links: dict[str, Any] = {
        "prophecy_promotion_gates": {
            "latest_compat": _optional_link(ROOT / "docs/final/artifacts/prophecy_promotion_gates_v1_latest.json"),
            "legacy_strict": _optional_link(ROOT / "docs/final/artifacts/prophecy_promotion_gates_v1_legacy_strict_latest.json"),
            "panel_calibrated": _optional_link(ROOT / "docs/final/artifacts/prophecy_promotion_gates_v1_panel_calibrated_latest.json"),
        },
        "prophecy_strict_streak": {
            "legacy": _optional_link(ROOT / "docs/final/artifacts/prophecy_promotion_strict_streak_legacy_v1.json"),
            "panel_calibrated": _optional_link(
                ROOT / "docs/final/artifacts/prophecy_promotion_strict_streak_panel_calibrated_v1.json"
            ),
        },
        "notebooklm_btrack": {
            "mega_insights_jsonl": _optional_link(ROOT / "reports/notebooklm/btrack_mega_insights_10gb.jsonl"),
            "mega_insights_latest_jsonl": _optional_link(ROOT / "reports/notebooklm/btrack_mega_insights_latest.jsonl"),
            "jsonl_kpi": _optional_link(ROOT / "docs/final/artifacts/btrack_notebooklm_jsonl_kpi_latest.json"),
            "triage": _optional_link(ROOT / "reports/notebooklm/btrack_insight_triage_latest.json"),
            "recommendation_pack": _optional_link(ROOT / "reports/notebooklm/btrack_insight_recommendation_pack_latest.json"),
        },
        "multilens_artifacts": {
            "logos_independent_lens": _optional_link(ROOT / "docs/final/artifacts/logos_independent_lens_latest.json"),
            "myeongni_independent_lens": _optional_link(ROOT / "docs/final/artifacts/myeongni_independent_lens_latest.json"),
            "sasang_independent_lens": _optional_link(ROOT / "docs/final/artifacts/sasang_independent_lens_latest.json"),
        },
        "myeongni_logs": {
            "insight_observation_log": _optional_link(ROOT / "data/myeongni/insight_observation_log.jsonl"),
            "state16_experiment_jsonl": _optional_link(ROOT / "data/myeongni/myeongni_16_state_experiment_v1.jsonl"),
            "state16_calendar_stub_jsonl": _optional_link(
                ROOT / "data/myeongni/myeongni_16_state_experiment_v1.calendar_stub_through_202604.jsonl"
            ),
        },
        "sasang_logs": {
            "dynamics_calendar_stub_jsonl": _optional_link(
                ROOT / "data/sasang/sasang_dynamics_regime_mapping_v1.calendar_stub_through_202604.jsonl"
            ),
            "dynamics_sample_jsonl": _optional_link(ROOT / "data/sasang/sasang_dynamics_regime_mapping_v1.sample.jsonl"),
        },
        "operational_rails": {
            "signoff_packet_latest": _optional_link(ROOT / "docs/final/artifacts/btrack_promotion_signoff_packet_v1_latest.json"),
            "live_ab_summary": _optional_link(ROOT / "docs/final/artifacts/prophecy_live_ab_summary_v1_latest.json"),
            "dual_gate_refresh_script": _optional_link(ROOT / "scripts/refresh_prophecy_promotion_gates_dual_v1.py"),
            "signoff_build_script": _optional_link(ROOT / "scripts/build_btrack_promotion_signoff_packet_v1.py"),
            "insight_sidecar_chain_script": _optional_link(ROOT / "scripts/Run-BtrackInsightSidecarChain.ps1"),
        },
        "prophecy_score_insight_sidecar_phase3": {
            "latest_stub": _optional_link(ROOT / "docs/final/artifacts/btrack_prophecy_score_insight_sidecar_v1_latest.json"),
            "build_stub_script": _optional_link(ROOT / "scripts/build_btrack_prophecy_score_insight_sidecar_stub_v1.py"),
            "sidecar_schema": _optional_link(ROOT / "docs/final/schemas/btrack_prophecy_score_insight_sidecar_v1.schema.json"),
            "lens_hit_agreement_eval": _optional_link(
                ROOT / "docs/final/artifacts/btrack_insight_sidecar_lens_hit_agreement_v1_latest.json"
            ),
            "lens_hit_agreement_script": _optional_link(ROOT / "scripts/eval_btrack_insight_sidecar_lens_hit_agreement_v1.py"),
        },
        "ssot_docs": {
            "notebooklm_sources_manifest": _optional_link(ROOT / "docs/NotebookLM_sources_manifest.md"),
            "constitution_implementation_facts": _optional_link(
                ROOT / "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md"
            ),
            "central_agent_memory": _optional_link(ROOT / "docs/final/CENTRAL_AGENT_MEMORY_V1.md"),
        },
    }

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "description_ko": (
            "B-track 통찰·렌즈·NotebookLM·명리 로그와 예언 승격 산출물 사이의 포인터 맵. "
            "scores/walkforward에 자동 합선하지 않음."
        ),
        "inventory_ref": inventory_ref,
        "links": links,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
