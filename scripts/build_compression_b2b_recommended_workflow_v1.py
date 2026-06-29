#!/usr/bin/env python3
"""Refresh compression B2B recommended workflow JSON from latest signoff + pilot ROI."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/final/artifacts/compression_b2b_recommended_workflow_v1.json"
SIGNOFF = ROOT / "docs/final/artifacts/compression_b2b_legal_send_signoff_v1_latest.json"
ROI = ROOT / "docs/final/artifacts/compression_b2b_pilot_roi_report_v1_latest.json"
OFF_THE_SHELF_SKU = ROOT / "docs/final/artifacts/compression_b2b_off_the_shelf_shard_sku_v1.json"
INDUSTRY_BUNDLE = ROOT / "reports/compression_b2b_sku_industry_poc_bundle_v1_latest.json"
SHORT_CAP_COMPARE = ROOT / "reports/compression_b2b_short_context_cap_compare_v1_latest.json"
INDUSTRY_CHAIN = ROOT / "reports/compression_b2b_evidence_v1_industry_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    signoff = _load(SIGNOFF)
    roi = _load(ROI)
    off_shelf = _load(OFF_THE_SHELF_SKU)
    industry_bundle = _load(INDUSTRY_BUNDLE)
    short_cap = _load(SHORT_CAP_COMPARE)
    industry_chain = _load(INDUSTRY_CHAIN)
    proxy = roi.get("measured_proxy") or {}
    saving = proxy.get("mean_token_saving_rate_proxy")
    saving_pct = f"{100 * float(saving):.1f}%" if saving is not None else "—"
    return {
        "schema": "compression_b2b_recommended_workflow_v1",
        "generated_at_utc": _utc(),
        "send_gate": signoff.get("send_gate", "HOLD"),
        "ready_for_external_send": bool(signoff.get("ready_for_external_send")),
        "labels": ["DRAFT", "internal_only", "research_only", "publish_allowed=false"],
        "external_one_liner": {
            "ko": "내부 리허설에서 파이프라인 무결성은 확인했고, 고객 실측·법무 승인 전까지 외부 성과 주장은 하지 않습니다.",
            "en": "Internal rehearsal verified pipeline integrity; no external performance claims until customer measurement and counsel sign-off.",
        },
        "product_model": {
            "summary_ko": "고객 마스킹 JSONL을 받아 공용 압축 API(stateless + shared codebook)로 요청 시 압축·측정 — 고객 전용 사전 오프라인 빌드·Track A 47% 보장은 아님.",
            "summary_en": "Masked customer JSONL compressed on-demand via shared API; not per-tenant offline codebook build or universal 47% warranty.",
            "not_this": [
                "Track A ~47% as customer SLA",
                "Handoff 99.47% as compression API headline",
                f"Prospect rehearsal {saving_pct} as named customer case study",
            ],
        },
        "sku_separation": [
            {
                "sku": "track_a_universal_bench",
                "metric": "~47% / ~0.89 J",
                "role": "internal_regression_ssot",
            },
            {
                "sku": "prospect_pilot_poc",
                "metric": f"{saving_pct} saving proxy ({proxy.get('case_count', '?')}-case rehearsal)",
                "role": "per_tenant_jsonl_measurement",
                "artifact": ROI.relative_to(ROOT).as_posix() if ROI.is_file() else None,
            },
            {
                "sku": "handoff_governance",
                "metric": "99.47% token reduction top-N slices",
                "role": "ops_memory_index_only",
            },
            {
                "sku": "off_the_shelf_b2b_shard",
                "metric": "per-SKU PoC only (not Track A SLA)",
                "role": "forced_shard_id_industry_demo",
                "artifact": OFF_THE_SHELF_SKU.relative_to(ROOT).as_posix()
                if OFF_THE_SHELF_SKU.is_file()
                else None,
                "bundle_report": INDUSTRY_BUNDLE.relative_to(ROOT).as_posix()
                if INDUSTRY_BUNDLE.is_file()
                else None,
                "external_skus": [
                    s.get("external_sku")
                    for s in (off_shelf.get("skus") or [])
                    if s.get("external_sku")
                ]
                if off_shelf
                else [],
            },
        ],
        "recommended_commands": {
            "verify_all": "py scripts/run_compression_proof_completion_chain_v1.py",
            "customer_corpus": "py scripts/run_compression_pilot_roi_chain_v1.py --tenant-id <TENANT_SLUG>",
            "corpus_calibration_pack": "py scripts/run_compression_calibration_pack_v1.py --tenant-id <TENANT_SLUG>",
            "must_keep_overlay": "py scripts/extract_tenant_must_keep_from_corpus_v1.py --tenant-id <TENANT_SLUG> --input-jsonl data/compression/stateless_poc_prospect_<TENANT_SLUG>_v1.jsonl",
            "hydrate_compare": "py scripts/run_compression_pilot_hydrate_compare_v1.py --tenant-id <TENANT_SLUG> --input-jsonl data/compression/stateless_poc_prospect_<TENANT_SLUG>_v1.jsonl --overlay-json docs/final/artifacts/tenant_<TENANT_SLUG>_must_keep_overlay_v1.json",
            "dollar_roi_customer": "py scripts/build_compression_pilot_dollar_roi_v1.py --tenant-id <TENANT_SLUG> --poc-json reports/customer_compression_stateless_poc_<TENANT_SLUG>_v1_latest.json",
            "legal_send_after_counsel": "py scripts/apply_compression_b2b_legal_send_signoff_v1.py --commander-acknowledge --counsel-acknowledge",
            "readiness_gate": "py scripts/check_compression_enterprise_summary_readiness_v1.py",
            "off_the_shelf_sku_spec": "docs/final/artifacts/compression_b2b_off_the_shelf_shard_sku_v1.json",
            "industry_poc_bundle": (
                "py scripts/run_compression_b2b_sku_industry_poc_bundle_v1.py "
                "--compression-profile literal --auto-b2b-overlay --rows-per-sku 30"
            ),
            "industry_evidence_v1_chain": "py scripts/run_compression_b2b_evidence_v1_industry_chain_v1.py",
            "industry_short_cap_ab": "py scripts/run_compression_b2b_short_context_cap_chain_v1.py",
            "industry_corpus_build": "py scripts/build_compression_b2b_industry_poc_corpus_v1.py --rows-per-sku 30",
            "single_sku_poc": (
                "py scripts/run_customer_compression_stateless_poc_v1.py --input-jsonl <CORPUS> "
                "--sku <MKM-SKU> --compression-profile literal --auto-b2b-overlay --out-json <REPORT>"
            ),
            "open_sandbox_corpus": "py scripts/build_compression_open_sandbox_corpus_v1.py --tenant-id open-sandbox-01",
            "open_sandbox_pilot": (
                "py scripts/run_compression_pilot_roi_chain_v1.py --tenant-id open-sandbox-01 "
                "--input-jsonl data/compression/stateless_poc_golden40_public_safe_v1.jsonl "
                "--sandbox-mode --relax-pass-gate --max-cases 40"
            ),
        },
        "solo_ops_policy": {
            "signoff": "SOLO_SELF_AUDIT_20260607",
            "gtm_lane_contract": "docs/final/artifacts/solo_github_gtm_lane_contract_v1_latest.json",
            "primary_gtm_lane": "solo_developer_github_open_bench",
            "counsel_rail": "deprecated_drawer_only",
            "ready_for_external_send": False,
            "send_gate": "HOLD",
            "note_ko": "1인 R&D — 법무/CTO 송부·MS ZIP 메일 아웃바운드 폐기; GitHub·a-codeai·contributor 본선. MS팩=인바운드 부록만.",
            "agent_never_default": [
                "ms_evidence_zip_email_outbound",
                "counsel_zip_proactive_send",
                "interpret_legal_send_gate_open_as_sales_mail_go",
            ],
        },
        "off_the_shelf_shard": {
            "spec_path": OFF_THE_SHELF_SKU.relative_to(ROOT).as_posix()
            if OFF_THE_SHELF_SKU.is_file()
            else None,
            "routing": "forced_shard_id via --sku (b2b shards not in auto route(text))",
            "industry_bundle_ok": industry_bundle.get("bundle_ok"),
            "industry_bundle_path": INDUSTRY_BUNDLE.relative_to(ROOT).as_posix()
            if INDUSTRY_BUNDLE.is_file()
            else None,
            "industry_profile_policy": {
                "default_compression_profile": industry_bundle.get("compression_profile_default", "literal"),
                "must_keep_overlay": industry_bundle.get("must_keep_overlay", True),
                "rows_per_sku": industry_bundle.get("rows_per_sku", 30),
                "short_cap_fallback": short_cap.get("recommended_profile"),
                "evidence_chain_ok": industry_chain.get("chain_ok"),
            },
            "external_skus": [
                s.get("external_sku")
                for s in (off_shelf.get("skus") or [])
                if s.get("external_sku")
            ]
            if off_shelf
            else [],
        },
        "corpus_calibration_pack": {
            "name": "Corpus Calibration Pack",
            "day_scope": "Day 8~30",
            "not_this": "per-tenant 41k offline rebuild",
            "artifact_glob": "reports/compression_calibration_pack_<TENANT>_v1_latest.json",
        },
        "human_gates": [
            {
                "id": "customer_masked_jsonl_20_50",
                "status": "pending" if roi.get("customer_dollar_roi") is None else "measured",
                "unlocks": "customer_dollar_roi / customer_krw_roi",
                "note": "rehearsal corpus does not satisfy this gate — real customer PII-masked JSONL required",
            },
            {
                "id": "rehearsal_corpus_pilot_chain",
                "status": "measured" if roi.get("measured_proxy", {}).get("case_count") else "pending",
                "unlocks": "internal_meeting_demo_only",
                "artifact": ROI.relative_to(ROOT).as_posix() if ROI.is_file() else None,
            },
            {
                "id": "counsel_signoff",
                "status": "superseded_by_solo_self_audit",
                "unlocks": "ready_for_external_send",
                "note": "1인 정책 — counsel 레일 폐기; SOLO_SELF_AUDIT_20260607로 대체",
            },
            {
                "id": "solo_self_audit",
                "status": "active",
                "signoff": "SOLO_SELF_AUDIT_20260607",
                "unlocks": "internal_pipeline_validation_only",
            },
            {
                "id": "industry_masked_corpus_30_50",
                "status": "measured_rehearsal"
                if (industry_bundle.get("rows_per_sku") or 0) >= 20
                else "pending",
                "unlocks": "internal_industry_sku_demo_only",
                "note": "public-safe synthetic industry JSONL — not real customer PII-masked JSONL",
                "artifact": INDUSTRY_BUNDLE.relative_to(ROOT).as_posix()
                if INDUSTRY_BUNDLE.is_file()
                else None,
            },
            {
                "id": "open_sandbox_virtual_tenant",
                "status": "measured"
                if (ROOT / "data/compression/stateless_poc_open_sandbox_open-sandbox-01_v1.jsonl").is_file()
                else "pending",
                "tenant_id": "open-sandbox-01",
                "unlocks": "customer_masked_jsonl_20_50_bypass_for_1p_dev_only",
            },
        ],
        "hybrid_pipeline_pointer": {
            "artifact": "docs/final/artifacts/hybrid_b2b_commercialization_pipeline_v1_latest.json",
            "builder": "py scripts/build_hybrid_b2b_commercialization_pipeline_v1.py",
            "note_ko": "Compression 3A vs Edge SKU-COORD 3B 레인 분리 — FAIL-COMP-004",
        },
        "fact_lock_pointers": [
            SIGNOFF.relative_to(ROOT).as_posix() if SIGNOFF.is_file() else None,
            OFF_THE_SHELF_SKU.relative_to(ROOT).as_posix() if OFF_THE_SHELF_SKU.is_file() else None,
            "docs/final/artifacts/hybrid_b2b_commercialization_pipeline_v1_latest.json",
            "docs/final/artifacts/compression_public_reproduce_pack_v1_latest.json",
            "docs/final/COMPRESSION_SLA_POLICY_V1.md",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.out_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
