#!/usr/bin/env python3
"""Refresh W4 B2B bench prep pack — launch checklist + MASK HYPO chain + guardrails."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT_DEFAULT = ROOT / "docs/final/artifacts/compression_b2b_w4_bench_prep_pack_v1_latest.json"
LAUNCH_CHECKLIST = ROOT / "docs/final/artifacts/a_codeai_public_benchmark_launch_checklist_v1.json"
HYPO_AUDIT = ROOT / "docs/final/artifacts/compression_mask_hypo_passive_cross_audit_v1_latest.json"
CLOSEOUT = ROOT / "reports/compression_spiking_closeout_v1.json"
SKU_BRIEF = ROOT / "docs/final/artifacts/compression_sku_separation_brief_v1_latest.json"
SIGNAL_LIGHT = ROOT / "docs/final/artifacts/track_a_signal_light_report_latest.json"
BINDING_CHECK = ROOT / "docs/final/artifacts/a_codeai_public_binding_check_latest.json"
OPS_READINESS = ROOT / "docs/final/artifacts/pointerguard_ops_readiness_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
        return doc if isinstance(doc, dict) else {}
    except Exception:
        return {}


def _git_head_sha() -> str | None:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        sha = (proc.stdout or "").strip()
        return sha or None
    except Exception:
        return None


def build_pack(*, workspace_root: Path = ROOT) -> dict[str, Any]:
    launch = _load_json(workspace_root / LAUNCH_CHECKLIST.relative_to(ROOT))
    hypo = _load_json(workspace_root / HYPO_AUDIT.relative_to(ROOT))
    binding = _load_json(workspace_root / BINDING_CHECK.relative_to(ROOT))
    ops = _load_json(workspace_root / OPS_READINESS.relative_to(ROOT))
    signal = _load_json(workspace_root / SIGNAL_LIGHT.relative_to(ROOT))

    launch_summary = launch.get("summary") if isinstance(launch.get("summary"), dict) else {}
    launch_pass = int(launch_summary.get("pass_count") or 0)
    launch_total = int(launch_summary.get("total") or 0)
    technical_decision = str(launch_summary.get("decision") or "HOLD_NEEDS_HARDENING")

    hypo_agg = hypo.get("aggregate") if isinstance(hypo.get("aggregate"), dict) else {}
    hypo_all_pass = bool(hypo_agg.get("all_steps_pass"))
    hypo_step_count = int(hypo_agg.get("step_count") or 0)

    track_a_signal = str(signal.get("overall_signal") or signal.get("signal") or "UNKNOWN")
    metering_band = str(signal.get("metering_band_gate") or "unknown")

    return {
        "schema": "compression_b2b_w4_bench_prep_pack_v1",
        "generated_at_utc": _utc(),
        "git_head_sha": _git_head_sha(),
        "technical_launch_decision": technical_decision,
        "external_launch_decision": "BLOCKED_BY_READINESS",
        "external_launch_note_ko": "기술 체크리스트와 HYPO 체인 통과와 별도; 파일럿 미팅·P1 발송은 인간 게이트(HOLD).",
        "launch_checks_pass": launch_pass,
        "launch_checks_total": launch_total,
        "pointerguard_ops_readiness_all_ok": bool(ops.get("all_ok", False)),
        "a_codeai_binding_decision": "PASS" if bool(binding.get("all_ok", False)) else "FAIL",
        "track_a_signal": track_a_signal,
        "metering_band_gate": metering_band,
        "mask_hypo_chain": {
            "research_only": True,
            "send_gate": "HOLD",
            "passive_cross_audit_artifact": HYPO_AUDIT.relative_to(ROOT).as_posix(),
            "all_steps_pass": hypo_all_pass,
            "step_count": hypo_step_count,
            "closeout": CLOSEOUT.relative_to(ROOT).as_posix(),
            "sku_brief": SKU_BRIEF.relative_to(ROOT).as_posix(),
            "v2_stub_shadow_bind_metadata": True,
            "daily_task": "MKM_Compression_MaskHypoPassiveCrossAudit_Daily",
            "reproduce": "py scripts/run_compression_mask_hypo_passive_cross_audit_v1.py",
        },
        "scripts": {
            "launch_checklist": "scripts/build_a_codeai_public_benchmark_launch_checklist_v1.py",
            "binding_check": "scripts/check_a_codeai_public_binding_v1.py",
            "ops_readiness": "scripts/check_pointerguard_ops_readiness_v1.py",
            "track_a_daily": "scripts/run_track_a_commercialization_daily_chain.ps1",
            "signal_light": "scripts/build_track_a_signal_light_report.py",
            "mask_hypo_passive_audit": "scripts/run_compression_mask_hypo_passive_cross_audit_v1.py",
            "w4_routine": "scripts/Run-CompressionB2bWeek4Routine_v1.ps1",
            "w4_pack_builder": "scripts/build_compression_b2b_w4_bench_prep_pack_v1.py",
        },
        "artifacts": {
            "launch_checklist": LAUNCH_CHECKLIST.relative_to(ROOT).as_posix(),
            "binding_check": BINDING_CHECK.relative_to(ROOT).as_posix(),
            "ops_readiness": OPS_READINESS.relative_to(ROOT).as_posix(),
            "nginx_example": "scripts/deploy/nginx/a-codeai.com.static-plus-compression-api.conf.example",
            "evidence_index": "docs/final/artifacts/compression_public_evidence_pack_v0_index_latest.json",
            "p1_transition": "docs/final/P1_COMPRESSION_API_PILOT_TRANSITION_CHECKLIST_V1.md",
            "post_meeting": "docs/final/artifacts/compression_b2b_post_meeting_transition_v1_latest.json",
        },
        "track_c_parallel": {
            "rehearsal_script": "reports/track_c_b2b_15min_rehearsal_script_v1_latest.md",
            "rehearsal_readiness": "reports/track_c_b2b_internal_rehearsal_readiness_v1_latest.json",
            "counsel_zip": "docs/final/artifacts/track_c_b2b_counsel_export_pack_v1.zip",
            "ready_for_external_send": False,
        },
        "guardrails": {
            "public_bench_claims_conditional_only": True,
            "no_global_savings_headline": True,
            "fail_comp_004": True,
            "send_gate": "HOLD",
            "track_a_active_untouched": True,
        },
        "phase2_mkmlife_scan": {
            "readiness": "docs/final/artifacts/mkmlife_section11_readiness_v1_latest.json",
            "monorepo_routes_ok": True,
            "payment_e2e_deferred": True,
            "next_phase": "2026-07~08 PayApp E2E",
        },
        "aggregate": {
            "w4_pack_ok": hypo_all_pass and launch_total > 0,
            "hypo_chain_ok": hypo_all_pass,
            "ready_for_external_send": False,
        },
        "reproduce": "powershell -File scripts/Run-CompressionB2bWeek4Routine_v1.ps1",
    }


def write_pack(doc: dict[str, Any], *, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    args = ap.parse_args()

    doc = build_pack(workspace_root=args.workspace_root)
    write_pack(doc, out_path=args.out)
    agg = doc["aggregate"]
    print(
        json.dumps(
            {
                "ok": bool(agg.get("w4_pack_ok")),
                "hypo_chain_ok": agg.get("hypo_chain_ok"),
                "technical_launch_decision": doc.get("technical_launch_decision"),
                "external_launch_decision": doc.get("external_launch_decision"),
                "out": str(args.out),
            },
            ensure_ascii=False,
        )
    )
    return 0 if agg.get("hypo_chain_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
