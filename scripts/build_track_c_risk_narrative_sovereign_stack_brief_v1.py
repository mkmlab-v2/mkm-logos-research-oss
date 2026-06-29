#!/usr/bin/env python3
"""Refresh Track C §3.2 Sovereign Stack / Precursor Protocol brief pack (JSON)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _exists(root: Path, rel: str) -> bool:
    return (root / rel).is_file()


def _build_doc(*, generated_at: str, root: Path) -> dict:
    deliverable_paths = [
        ("sovereign_stack_watch", "reports/civilization_apocalypse_sovereign_stack_watch_v1.json"),
        ("rev13_counter_axis_map", "reports/civilization_apocalypse_rev13_architecture_map_v1.json"),
        ("t1_stub_fixture", "tests/fixtures/general_prophecy_registry_sovereign_stack_t1_stub_v1.json"),
        ("canonical_civ_registry", "tests/fixtures/general_prophecy_registry_civilization_apocalypse_v1.json"),
        ("production_registry", "docs/final/artifacts/general_prophecy_latest.json"),
        ("logos_deep_onepager", "docs/final/artifacts/track_c_logos_deep_risk_narrative_offer_onepager_v1_latest.md"),
    ]
    deliverables = [
        {"id": did, "path": p, "present": _exists(root, p)} for did, p in deliverable_paths
    ]
    all_core = all(
        d["present"]
        for d in deliverables
        if d["id"] in {"sovereign_stack_watch", "t1_stub_fixture", "canonical_civ_registry"}
    )
    return {
        "schema": "track_c_risk_narrative_sovereign_stack_brief_v1",
        "generated_at_utc": generated_at,
        "status": "DRAFT_INTERNAL",
        "legal_review_required_before_external_send": True,
        "aligned_with": [
            "docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md §3.2",
            "docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md v1.7",
            "docs/final/artifacts/track_c_logos_deep_risk_narrative_offer_onepager_v1_latest.md",
        ],
        "research_rail": "B",
        "hypothesis_tier": "[HYPO]",
        "gating_status": "NON_GATING",
        "product_sku": "Risk Narrative Brief — Precursor Protocol / Sovereign Stack Module",
        "positioning": {
            "public_engineering_label": "Precursor Protocol — off-ledger survivability stack",
            "internal_logos_auxiliary": "John-the-Baptist wilderness precursor [NON_GATING]",
            "not_positioned_as": [
                "messiah_technology",
                "religious_fulfillment_claim",
                "trade_signal",
                "track_a_compression_kpi",
            ],
        },
        "field_primary": "regime_on_device_sovereignty_prior_infrastructure",
        "field_counter_pressure": "regime_beast_governance_platform_identification",
        "tactical_contrarian_thesis": "As seal/mark binding-cluster pressure rises, measurable sovereign-stack adoption metrics may support §3.2 narrative premium — Brier falsification required.",
        "measurable_backbone_question_ids": [
            "civ.gov.ondevice_did_mandate_oecd3_2035",
            "civ.tech.e2ee_default_messenger_dau_1b_2032",
            "civ.finance.self_custody_wallet_oecd5_50pct_2038",
        ],
        "cartel_pressure_reference_ids": [
            "civ.finance.cbdc_retail_oecd10_2035",
            "civ.gov.digital_id_treaty_g7plus_2040",
            "civ.finance.cash_retail_ban_g7_one_2040",
            "civ.tech.neural_wallet_default_payment_oecd5_2048",
        ],
        "deliverables": deliverables,
        "artifact_evidence_status": "ALL_CORE_PRESENT" if all_core else "GAPS_REVIEW",
        "builder_chain": [
            "scripts/build_track_c_risk_narrative_sovereign_stack_brief_v1.py",
            "scripts/build_track_c_logos_b2b_offer_onepager_v1.py",
            "scripts/build_track_c_combined_b2b_offer_onepager_v1.py",
        ],
        "governance": {
            "track_a_merge": False,
            "live_trading_trigger": False,
            "b_to_a_auto_merge": False,
            "external_send": False,
        },
        "final_action": "WATCH_SOVEREIGN_STACK",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = _root()
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    doc = _build_doc(generated_at=generated_at, root=root)
    out = root / "reports/track_c_risk_narrative_sovereign_stack_brief_v1.json"

    if args.dry_run:
        print(json.dumps({"out": str(out), "artifact_evidence_status": doc["artifact_evidence_status"]}, indent=2))
        return 0

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out}")
    if doc["artifact_evidence_status"] != "ALL_CORE_PRESENT":
        print("WARN: core sovereign-stack artifacts missing")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
