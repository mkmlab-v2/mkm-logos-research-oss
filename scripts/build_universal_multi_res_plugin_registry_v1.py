#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Emit universal multi-res plugin registry v1 (U3-lite). Validates anchor paths exist."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/universal_multi_res_plugin_registry_v1_latest.json"
VERSION = "1.0.0"
SCHEMA = "universal_multi_res_plugin_registry_v1"

PLUGIN_DEFS: dict[str, dict[str, Any]] = {
    "sasang": {
        "plugin_id": "sasang_context_v1",
        "lane_label_ko": "사상동역학",
        "time_horizon_ko": "단기 톤·강도",
        "expectation_matrix_ref": "docs/final/artifacts/sasang_expectation_vs_fact_matrix_v1.md",
        "inventory_artifact_ref": "docs/final/artifacts/sasang_context_inventory_v1_latest.json",
        "contract_ref": "docs/final/artifacts/SASANG_DYNAMICS_V1_CONTRACT.json",
        "agent_read_order": [
            "docs/final/artifacts/sasang_expectation_vs_fact_matrix_v1.md",
            "docs/final/artifacts/sasang_context_inventory_v1_latest.json",
            "docs/final/artifacts/SASANG_DYNAMICS_V1_CONTRACT.json",
            "docs/final/artifacts/sasang_dynamics_btrack_milestone_v1_latest.json",
        ],
        "low_res_runners": [
            "scripts/build_sasang_persona_grid_v1.py",
            "scripts/run_lens_sasang.py",
            "scripts/sasang_context_inventory_v1.py",
        ],
        "hold_flags": [
            "clinical_diagnosis_output",
            "production_gematria_kernel",
            "live_trading_trigger",
        ],
        "u3_tier": "full",
    },
    "myeongni": {
        "plugin_id": "myeongni_lens_v1",
        "lane_label_ko": "명리학",
        "time_horizon_ko": "중기 방향",
        "expectation_matrix_ref": "docs/final/artifacts/myeongni_expectation_vs_fact_matrix_v1_lite.md",
        "inventory_artifact_ref": "docs/final/artifacts/myeongni_context_inventory_v1_latest.json",
        "contract_ref": "docs/final/artifacts/MYEONGNI_INDEPENDENT_LENS_V0_CONTRACT.json",
        "agent_read_order": [
            "docs/final/artifacts/myeongni_expectation_vs_fact_matrix_v1_lite.md",
            "docs/final/artifacts/myeongni_context_inventory_v1_latest.json",
            "docs/final/artifacts/MYEONGNI_INDEPENDENT_LENS_V0_CONTRACT.json",
            "docs/final/artifacts/myeongni_independent_lens_latest.json",
            "reports/myeongni_conflict_arbitration_runtime_mode_latest.json",
        ],
        "low_res_runners": [
            "scripts/run_lens_myeongni.py",
            "scripts/build_myeongni_full_report_v1.py",
            "scripts/myeongni_context_inventory_v1.py",
        ],
        "hold_flags": [
            "myeongri_16_to_sasang_12_identity_map",
            "market_index_to_birth_chart_substitution",
            "prophecy_auto_promotion",
        ],
        "u3_tier": "lite",
    },
    "logos": {
        "plugin_id": "logos_lens_v1",
        "lane_label_ko": "성경 Logos",
        "time_horizon_ko": "거시 상징·[NON_GATING]",
        "expectation_matrix_ref": "docs/final/artifacts/logos_expectation_vs_fact_matrix_v1_lite.md",
        "inventory_artifact_ref": "docs/final/artifacts/logos_context_inventory_v1_latest.json",
        "contract_ref": "docs/final/artifacts/LOGOS_INDEPENDENT_LENS_V0_CONTRACT.json",
        "agent_read_order": [
            "docs/final/artifacts/logos_expectation_vs_fact_matrix_v1_lite.md",
            "docs/final/artifacts/logos_context_inventory_v1_latest.json",
            "docs/final/artifacts/LOGOS_INDEPENDENT_LENS_V0_CONTRACT.json",
            "docs/final/artifacts/logos_independent_lens_latest.json",
            "docs/final/artifacts/notebooklm_lens_logos_nl_fact_lock_guard_v1_latest.md",
        ],
        "low_res_runners": [
            "scripts/run_lens_logos.py",
            "scripts/logos_context_inventory_v1.py",
        ],
        "hold_flags": [
            "fake_666_anchor",
            "finance_implicit_gating",
            "nl_perfect_integration_claim",
        ],
        "u3_tier": "lite_plus",
    },
    "science": {
        "plugin_id": "uft_core_v1_stub",
        "lane_label_ko": "과학·UFT",
        "time_horizon_ko": "물리 엔진 레인 [HYPO]",
        "expectation_matrix_ref": "docs/final/artifacts/mkm_theory_mathematization_canon_v1_latest.md",
        "inventory_artifact_ref": None,
        "contract_ref": None,
        "agent_read_order": [
            "docs/final/artifacts/mkm_theory_mathematization_canon_v1_latest.md",
            "tools/core/unified_field_theory_engine.py",
        ],
        "low_res_runners": ["tools/core/unified_field_theory_engine.py"],
        "hold_flags": [
            "dt_dx_unified_field_equation",
            "physical_determinism_gating",
            "toe_lens_supremacy",
        ],
        "u3_tier": "stub",
        "stub_status": "u3_lite_reserved",
    },
    "compression": {
        "plugin_id": "compression_track_a_observability_v1",
        "lane_label_ko": "압축·Track A 관측",
        "time_horizon_ko": "운영 벤치",
        "expectation_matrix_ref": "docs/final/COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md",
        "inventory_artifact_ref": None,
        "contract_ref": None,
        "agent_read_order": [
            "docs/final/COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md",
        ],
        "low_res_runners": ["scripts/compression_token_api_v2_stub.py"],
        "hold_flags": ["fail_comp_004_bypass", "repair_only_track_a_promotion"],
        "u3_tier": "lite",
    },
    "ops": {
        "plugin_id": "mkm_ops_default_v1",
        "lane_label_ko": "운영·재개",
        "time_horizon_ko": "세션·인프라",
        "expectation_matrix_ref": None,
        "inventory_artifact_ref": None,
        "contract_ref": None,
        "agent_read_order": ["docs/final/artifacts/mkm_chat_resume_pack_latest.md"],
        "low_res_runners": ["scripts/mkm_intent_router_local_v1.py"],
        "hold_flags": [],
        "u3_tier": "lite",
    },
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: str | None) -> str | None:
    if not path:
        return None
    return path.replace("\\", "/")


def build_registry(*, generated_at_utc: str | None = None, strict: bool = True) -> dict[str, Any]:
    plugins: dict[str, Any] = {}
    missing: list[str] = []
    for lane_id, defn in PLUGIN_DEFS.items():
        row = dict(defn)
        row["lane_id"] = lane_id
        anchors_ok: dict[str, bool] = {}
        for ref_key in (
            "expectation_matrix_ref",
            "inventory_artifact_ref",
            "contract_ref",
        ):
            ref = row.get(ref_key)
            if ref is None:
                continue
            p = ROOT / str(ref)
            ok = p.is_file()
            anchors_ok[ref_key] = ok
            if strict and not ok:
                missing.append(str(ref))
        for ref in row.get("agent_read_order") or []:
            p = ROOT / str(ref)
            key = f"read:{ref}"
            ok = p.is_file()
            anchors_ok[key] = ok
            if strict and not ok and lane_id != "science":
                missing.append(str(ref))
        for ref in row.get("low_res_runners") or []:
            p = ROOT / str(ref)
            key = f"runner:{ref}"
            anchors_ok[key] = ok
            if strict and not ok:
                missing.append(str(ref))
        row["anchors_ok"] = anchors_ok
        plugins[lane_id] = row

    if strict and missing:
        raise FileNotFoundError("missing registry anchors: " + "; ".join(sorted(set(missing))[:12]))

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "generated_at_utc": generated_at_utc or _utc_now(),
        "rail": "B_TRACK",
        "research_only": True,
        "send_gate": "HOLD",
        "promotion_to_a_track_allowed": False,
        "router_schema_ref": "docs/final/schemas/universal_multi_res_router_v1.schema.json",
        "position_ref": "docs/final/artifacts/universal_multi_res_router_y1b_position_v1_latest.md",
        "plugins": plugins,
        "reproduce_command": "py scripts/build_universal_multi_res_plugin_registry_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-o", "--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--no-strict", action="store_true")
    args = ap.parse_args()
    try:
        doc = build_registry(strict=not args.no_strict)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(json.dumps({"plugins": list(doc["plugins"].keys())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
