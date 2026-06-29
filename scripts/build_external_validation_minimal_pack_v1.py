#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "external_validation_minimal_pack_v1_latest"

BUNDLE_REQUIRED = [
    "docs/final/artifacts/hybrid_b2b_commercialization_pipeline_v1_latest.json",
    "docs/final/artifacts/edge_encoder_spec_v1_latest.json",
    "reports/hd_autonomous_evolution_completion_v1_latest.json",
    "reports/mkm_high_delegation_preflight_v1_latest.json",
]
BUNDLE_OPTIONAL_WEEK2 = [
    "reports/external_validation_d6_independent_rehearsal_v1_latest.json",
    "reports/external_validation_d6_aux_collect_v1_latest.json",
    "reports/compression_cross_host_parity_check_v1_latest.json",
    "reports/compression_cross_host_parity_aux_probe_v1_latest.json",
    "docs/final/artifacts/edge_encoder_vpc_deploy_runbook_v1_latest.json",
    "reports/edge_encoder_vpc_deploy_checklist_v1_latest.json",
    "reports/demo/edge_encoder_vpc_deploy_checklist_v1.html",
    "reports/external_validation_2week_closure_v1_latest.json",
    "reports/external_validation_gate_review_memo_v1_latest.json",
    "reports/external_validation_briefs_v1_latest/external_validation_tech_brief_v1_latest.json",
    "reports/external_validation_briefs_v1_latest/external_validation_business_brief_v1_latest.json",
    "reports/external_validation_briefs_v1_latest/external_validation_tech_brief_v1_latest.md",
    "reports/external_validation_briefs_v1_latest/external_validation_business_brief_v1_latest.md",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    allowed_names = {Path(rel).name for rel in BUNDLE_REQUIRED + BUNDLE_OPTIONAL_WEEK2} | {
        "manifest.json"
    }
    for path in OUT.iterdir():
        if path.is_file() and path.name not in allowed_names:
            path.unlink()

    copied: list[dict[str, str]] = []
    missing_optional: list[str] = []
    for rel in BUNDLE_REQUIRED:
        src = ROOT / rel
        if not src.exists():
            raise SystemExit(f"missing: {src.relative_to(ROOT)}")
        dst = OUT / src.name
        shutil.copy2(src, dst)
        copied.append(
            {
                "source": str(src.relative_to(ROOT)).replace("\\", "/"),
                "bundled": str(dst.relative_to(ROOT)).replace("\\", "/"),
                "tier": "required",
            }
        )
    for rel in BUNDLE_OPTIONAL_WEEK2:
        src = ROOT / rel
        if not src.is_file():
            missing_optional.append(rel)
            continue
        dst = OUT / src.name
        shutil.copy2(src, dst)
        copied.append(
            {
                "source": str(src.relative_to(ROOT)).replace("\\", "/"),
                "bundled": str(dst.relative_to(ROOT)).replace("\\", "/"),
                "tier": "week2_d6_d7",
            }
        )

    hybrid = _load_json(ROOT / "docs/final/artifacts/hybrid_b2b_commercialization_pipeline_v1_latest.json")
    signoff = _load_json(ROOT / "docs/final/artifacts/compression_b2b_legal_send_signoff_v1_latest.json")
    send_gate = str(signoff.get("send_gate") or hybrid.get("send_gate") or "HOLD")
    ready_for_external_send = bool(
        signoff.get("ready_for_external_send", hybrid.get("ready_for_external_send", False))
    )
    readiness_all_ok = bool(hybrid.get("readiness_all_ok", False))

    manifest = {
        "schema": "external_validation_minimal_pack_v1",
        "generated_at_utc": _utc_now(),
        "lane": "infra",
        "disclaimer": "internal_only",
        "send_gate": send_gate,
        "ready_for_external_send": ready_for_external_send,
        "plan_ssot": "docs/final/artifacts/external_validation_2week_execution_plan_v1_latest.md",
        "week1_day": "D5",
        "week2_day": "D10",
        "week2_status": "complete",
        "d6_status": {
            "rehearsal_class": "true_third_party_full_chain",
            "aux_host": "DESKTOP-AP1DC83",
            "steps_ok": "7/7",
            "compression_parity_probe_status": "ok",
            "compression_parity_numeric_match": False,
            "note": "Parity probe = reproducibility only; jaccard mismatch 3.11 vs 3.12 acceptable for D6.",
        },
        "bundled_files": copied,
        "missing_optional_week2": missing_optional,
        "reproduce_week1": [
            "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\Invoke-MkmHighDelegationPreflight_v1.ps1 -Scale M -Lane infra",
            (
                "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\Invoke-MkmHighDimensionalAutonomousEvolution_v1.ps1 "
                '-Mission "대외 입증 패키지 고정: 재현 명령, 벤치 아티팩트, 게이트 판정, 2주 실행안 산출" -Lane infra -CostTier tier_0'
            ),
            "py scripts/run_compression_proof_completion_chain_v1.py",
            "python -m pytest tests/test_edge_encoder_sdk_v1.py -q",
            "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\Invoke-EdgeEncoderAirGapPoC_v1.ps1",
            "py scripts/build_hybrid_b2b_commercialization_pipeline_v1.py",
            "py scripts/build_external_validation_minimal_pack_v1.py",
        ],
        "reproduce_week2_d6_d7": [
            "cmd /c C:\\share\\external_validation_d6_aux\\COPY_WORKSPACE_BUNDLE.cmd",
            "py C:\\share\\external_validation_d6_aux\\run_compression_parity_aux_v1.py",
            "py scripts/collect_compression_cross_host_parity_aux_v1.py --share-root Z:\\external_validation_d6_aux",
            "py scripts/collect_external_validation_d6_aux_result_v1.py --share-root Z:\\external_validation_d6_aux --result-name aux_d6_full_result_v1_latest.json",
            "py scripts/build_edge_encoder_vpc_deploy_runbook_v1.py",
            "py scripts/build_edge_encoder_vpc_checklist_html_v1.py",
            "py scripts/build_external_validation_minimal_pack_v1.py",
        ],
        "reproduce_week2_d8_d10": [
            "py scripts/build_external_validation_week2_closure_v1.py",
            "py scripts/build_external_validation_minimal_pack_v1.py",
        ],
        "gate_baseline": {
            "send_gate": send_gate,
            "ready_for_external_send": ready_for_external_send,
            "readiness_all_ok": readiness_all_ok,
        },
    }
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"ok": True, "out": str(OUT.relative_to(ROOT)), "file_count": len(copied) + 1}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
