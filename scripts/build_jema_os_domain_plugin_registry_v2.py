#!/usr/bin/env python3
"""Build JEMA OS domain plugin registry v2 — standardized lens + knowledge-pin slots."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/jema_os_domain_plugin_registry_v2_latest.json"
MKMLIFE_PUBLIC = (
    ROOT / "projects/mkm/mkm-life/public/data/jema_os_domain_plugin_registry_v2.json"
)
UMR_V1 = ROOT / "docs/final/artifacts/universal_multi_res_plugin_registry_v1_latest.json"
SCHEMA = "jema_os_domain_plugin_registry_v2"
VERSION = "2.0.0"

SLOT_DEFS: dict[str, dict[str, Any]] = {
    "logos": {
        "slot_kind": "lens_knowledge_pin",
        "lane_label_ko": "성경 Logos",
        "time_horizon_ko": "거시 상징·[NON_GATING]",
        "umr_lane": "logos",
        "spec_gap_intake_lane": "logos",
        "spec_gap_intent_chip": None,
        "plugin_id": "logos_lens_v1",
        "u3_tier": "lite_plus",
        "knowledge_pin": {
            "freeze_manifest_ref": (
                "docs/final/artifacts/logos_corpus_knowledge_freeze_manifest_v1_latest.json"
            ),
            "freeze_checker": "scripts/check_logos_corpus_knowledge_freeze_manifest_v1.py",
            "integrity_guard_module": "scripts/core/logos_lemma_edges_integrity_v1.py",
            "min_line_count_floor": 290_000,
            "edges_asset_key": "lemma_verse_edges_jsonl",
        },
        "inventory_artifact_ref": "docs/final/artifacts/logos_context_inventory_v1_latest.json",
        "contract_ref": "docs/final/artifacts/LOGOS_INDEPENDENT_LENS_V0_CONTRACT.json",
        "low_res_runners": [
            "scripts/run_lens_logos.py",
            "scripts/logos_context_inventory_v1.py",
            "scripts/check_logos_graphrag_router_axis_order_regression_v1.py",
        ],
        "hold_flags": [
            "fake_666_anchor",
            "finance_implicit_gating",
            "nl_perfect_integration_claim",
            "merge_enterprise_corpus_into_logos_pin",
        ],
    },
    "sasang": {
        "slot_kind": "lens_inventory",
        "lane_label_ko": "사상동역학",
        "time_horizon_ko": "단기 톤·강도",
        "umr_lane": "sasang",
        "spec_gap_intake_lane": "sasang",
        "spec_gap_intent_chip": None,
        "plugin_id": "sasang_context_v1",
        "u3_tier": "full",
        "knowledge_pin": None,
        "inventory_artifact_ref": "docs/final/artifacts/sasang_context_inventory_v1_latest.json",
        "contract_ref": "docs/final/artifacts/SASANG_DYNAMICS_V1_CONTRACT.json",
        "low_res_runners": [
            "scripts/run_lens_sasang.py",
            "scripts/sasang_context_inventory_v1.py",
        ],
        "hold_flags": [
            "clinical_diagnosis_output",
            "production_gematria_kernel",
            "live_trading_trigger",
        ],
    },
    "myeongni": {
        "slot_kind": "lens_inventory",
        "lane_label_ko": "명리학",
        "time_horizon_ko": "중기 방향",
        "umr_lane": "myeongni",
        "spec_gap_intake_lane": "myeongri",
        "spec_gap_intent_chip": None,
        "plugin_id": "myeongni_lens_v1",
        "u3_tier": "lite",
        "knowledge_pin": None,
        "inventory_artifact_ref": "docs/final/artifacts/myeongni_context_inventory_v1_latest.json",
        "contract_ref": "docs/final/artifacts/MYEONGNI_INDEPENDENT_LENS_V0_CONTRACT.json",
        "low_res_runners": [
            "scripts/run_lens_myeongni.py",
            "scripts/myeongni_context_inventory_v1.py",
        ],
        "hold_flags": [
            "myeongri_16_to_sasang_12_identity_map",
            "market_index_to_birth_chart_substitution",
            "prophecy_auto_promotion",
        ],
    },
    "enterprise_herbs_formulas": {
        "slot_kind": "enterprise_knowledge_pin",
        "lane_label_ko": "한방 처방·본초 (Enterprise PoC)",
        "time_horizon_ko": "전문가 검토·[HYPO]",
        "umr_lane": "enterprise_herbs_formulas",
        "spec_gap_intake_lane": None,
        "spec_gap_intent_chip": "clinician",
        "plugin_id": "enterprise_herbs_formulas_v1",
        "u3_tier": "lite",
        "knowledge_pin": {
            "freeze_manifest_ref": (
                "docs/final/artifacts/enterprise_herbs_formulas_knowledge_freeze_manifest_v1_latest.json"
            ),
            "freeze_checker": (
                "scripts/check_enterprise_herbs_formulas_knowledge_freeze_manifest_v1.py"
            ),
            "integrity_guard_module": "scripts/core/enterprise_knowledge_ingest_integrity_v1.py",
            "min_line_count_floor": 8,
            "edges_asset_key": "knowledge_edges_jsonl",
        },
        "inventory_artifact_ref": None,
        "contract_ref": None,
        "low_res_runners": [
            "scripts/run_enterprise_herbs_formulas_knowledge_ingest_chain_v1.py",
        ],
        "hold_flags": [
            "clinical_diagnosis_output",
            "patient_facing_without_expert_review",
            "merge_logos_corpus_pin",
            "track_a_promotion",
        ],
    },
    "lens_audio": {
        "slot_kind": "lens_inventory",
        "lane_label_ko": "렌즈 오디오·BGM",
        "time_horizon_ko": "미디어 어댑터·[HYPO]",
        "umr_lane": "unclassified",
        "spec_gap_intake_lane": None,
        "spec_gap_intent_chip": "observe",
        "plugin_id": "lens_audio_adapter_v1",
        "u3_tier": "lite",
        "knowledge_pin": None,
        "inventory_artifact_ref": "reports/audio_gate_latest.json",
        "contract_ref": "docs/final/schemas/audio_bgm_gate_report_v1.schema.json",
        "low_res_runners": [
            "scripts/Run-AudioBgmEconomyChain_v1.ps1",
            "scripts/run_lens_music_gematria_gate_chain_v1.py",
        ],
        "hold_flags": [
            "live_trading_trigger",
            "track_a_promotion",
            "clinical_diagnosis_output",
            "merge_compression_kpi_headline",
        ],
    },
    "design_surface": {
        "slot_kind": "lens_inventory",
        "lane_label_ko": "디자인 서피스·쇼룸",
        "time_horizon_ko": "Trust Composition·[HYPO]",
        "umr_lane": "design",
        "spec_gap_intake_lane": None,
        "spec_gap_intent_chip": "developer",
        "plugin_id": "design_surface_adapter_v1",
        "u3_tier": "lite",
        "knowledge_pin": None,
        "inventory_artifact_ref": "docs/final/artifacts/clinic_km_mmp_loi_tracker_v1_latest.json",
        "contract_ref": "docs/final/schemas/design_reference_seed_v1.schema.json",
        "low_res_runners": [
            "scripts/Run-ClinicLoiLandingDesignChain_v1.ps1",
            "scripts/check_clinic_km_mmp_landing_gate_v1.py",
        ],
        "hold_flags": [
            "patient_facing_without_expert_review",
            "track_a_promotion",
            "merge_logos_corpus_pin",
            "live_trading_trigger",
        ],
    },
}

ISOLATION_RULES: list[dict[str, Any]] = [
    {
        "rule_id": "logos_enterprise_pin_wall",
        "description_ko": "Logos 31k·lemma pin과 Enterprise herbs_formulas pin은 자산 경로·sha256 합병 금지",
        "slot_ids": ["logos", "enterprise_herbs_formulas"],
    },
    {
        "rule_id": "lens_knowledge_pin_independence",
        "description_ko": "렌즈 inventory(slots sasang/myeongni)는 knowledge_pin 슬롯과 자동 합선 금지",
        "slot_ids": ["logos", "sasang", "myeongni"],
    },
    {
        "rule_id": "media_adapter_independence",
        "description_ko": "lens_audio·design_surface 어댑터는 렌즈 knowledge_pin과 자동 합선 금지",
        "slot_ids": ["lens_audio", "design_surface", "logos"],
    },
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _anchor_ok(path: str | None) -> bool | None:
    if not path:
        return None
    return (ROOT / path).is_file()


def _pin_asset_paths(pin: dict[str, Any] | None) -> set[str]:
    if not pin:
        return set()
    manifest_ref = pin.get("freeze_manifest_ref")
    if not manifest_ref:
        return set()
    manifest_path = ROOT / str(manifest_ref)
    if not manifest_path.is_file():
        return set()
    doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    assets = doc.get("assets") or {}
    paths: set[str] = set()
    for spec in assets.values():
        if isinstance(spec, dict) and spec.get("path"):
            paths.add(str(spec["path"]).replace("\\", "/"))
    return paths


def build_registry(*, generated_at_utc: str | None = None, strict: bool = True) -> dict[str, Any]:
    umr_plugins: dict[str, Any] = {}
    if UMR_V1.is_file():
        umr_doc = json.loads(UMR_V1.read_text(encoding="utf-8"))
        umr_plugins = umr_doc.get("plugins") or {}

    slots: dict[str, Any] = {}
    missing: list[str] = []

    for slot_id, defn in SLOT_DEFS.items():
        row = dict(defn)
        row["slot_id"] = slot_id
        umr_lane = str(row.get("umr_lane") or slot_id)
        umr_row = umr_plugins.get(umr_lane)
        if umr_row and umr_row.get("plugin_id"):
            row["plugin_id"] = umr_row["plugin_id"]

        anchors_ok: dict[str, bool] = {}
        for ref_key in ("inventory_artifact_ref", "contract_ref"):
            ref = row.get(ref_key)
            if ref:
                ok = _anchor_ok(str(ref))
                anchors_ok[ref_key] = bool(ok)
                if strict and not ok:
                    missing.append(str(ref))

        pin = row.get("knowledge_pin")
        if isinstance(pin, dict):
            for ref_key in ("freeze_manifest_ref", "freeze_checker", "integrity_guard_module"):
                ref = pin.get(ref_key)
                if ref:
                    ok = _anchor_ok(str(ref))
                    anchors_ok[f"pin:{ref_key}"] = bool(ok)
                    if strict and not ok:
                        missing.append(str(ref))

        for ref in row.get("low_res_runners") or []:
            ok = _anchor_ok(str(ref))
            anchors_ok[f"runner:{ref}"] = bool(ok)
            if strict and not ok:
                missing.append(str(ref))

        row["anchors_ok"] = anchors_ok
        if row.get("knowledge_pin") is None:
            row.pop("knowledge_pin", None)
        slots[slot_id] = row

    logos_paths = _pin_asset_paths(slots["logos"].get("knowledge_pin"))
    enterprise_paths = _pin_asset_paths(slots["enterprise_herbs_formulas"].get("knowledge_pin"))
    overlap = sorted(logos_paths & enterprise_paths)
    if strict and overlap:
        missing.append("isolation_overlap:" + ",".join(overlap[:3]))

    if strict and missing:
        raise FileNotFoundError("missing registry v2 anchors: " + "; ".join(sorted(set(missing))[:12]))

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "generated_at_utc": generated_at_utc or _utc_now(),
        "rail": "B_TRACK",
        "research_only": True,
        "send_gate": "HOLD",
        "promotion_to_a_track_allowed": False,
        "live_llm_on_surface": False,
        "umr_registry_v1_ref": "docs/final/artifacts/universal_multi_res_plugin_registry_v1_latest.json",
        "intake_policy_ref": "docs/final/artifacts/oracle_sphere_l0_spec_gap_intake_policy_v1_latest.json",
        "enterprise_template_ref": "docs/final/artifacts/enterprise_knowledge_ingest_template_v1_latest.json",
        "slots": slots,
        "isolation_rules": ISOLATION_RULES,
        "reproduce_command": "py scripts/build_jema_os_domain_plugin_registry_v2.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-o", "--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--no-strict", action="store_true")
    ap.add_argument("--skip-mkmlife-public", action="store_true")
    args = ap.parse_args()
    try:
        doc = build_registry(strict=not args.no_strict)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 1
    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(f"WROTE: {args.out}")
    if not args.skip_mkmlife_public:
        MKMLIFE_PUBLIC.parent.mkdir(parents=True, exist_ok=True)
        MKMLIFE_PUBLIC.write_text(text, encoding="utf-8")
        print(f"WROTE: {MKMLIFE_PUBLIC}")
    print(json.dumps({"slots": list(doc["slots"].keys())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
