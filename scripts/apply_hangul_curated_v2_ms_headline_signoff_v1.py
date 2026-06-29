#!/usr/bin/env python3
"""Apply v2 MS headline policy from ACTIVE bench (submission archive KPI preserved)."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SIGNOFF = ROOT / "docs/final/artifacts/hangul_curated_v2_ms_headline_promotion_signoff_v1_latest.json"
PACKET = ROOT / "reports/hangul_curated_v2_ms_headline_promotion_packet_v1_latest.json"
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
HEADLINE_POLICY = ROOT / "reports/compression_track_a_headline_policy_v1_latest.json"
APPLY_LOG = ROOT / "reports/hangul_curated_v2_ms_headline_apply_v1_latest.json"
PASTE_SNIPPET = (
    ROOT / "reports/ms_rq019_paste_ready/track_a_internal_bench_headline_v2_hangul_curated_paste.txt"
)
P41708 = ROOT / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41708_rows_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _rel(p: Path) -> str:
    return str(p.relative_to(ROOT)).replace("\\", "/")


def _paste_body(proposed: dict[str, Any], archive: dict[str, Any]) -> str:
    p_pct = proposed.get("global_token_saving_rate_pct")
    p_j = proposed.get("avg_reconstruction_fidelity_jaccard_rounded") or round(
        float(proposed.get("avg_reconstruction_fidelity_jaccard") or 0), 3
    )
    a_pct = archive.get("global_token_saving_rate_pct")
    a_j = round(float(archive.get("avg_reconstruction_fidelity_jaccard") or 0), 3)
    return "\n".join(
        [
            "[Track A · internal bench headline · Hangul curated v2 · 41708 lexicon]",
            f"- Active Golden-40 bench (economy, bridge OFF): token saving ~{p_pct}%, Jaccard ~{p_j} (40 cases).",
            f"- MS submission archive (closed): ~{a_pct}% / Jaccard ~{a_j} — HWPX/PDF files not rewritten.",
            "- Do not merge CJK/RAG/prophecy % into this headline. repair_v2 is operational evidence only.",
            "- Source: docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json",
            "",
        ]
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not SIGNOFF.is_file() or not json.loads(SIGNOFF.read_text(encoding="utf-8")).get("approved"):
        print("ABORT: v2 ms headline signoff missing or not approved")
        return 1
    if not PACKET.is_file():
        print("ABORT: v2 ms headline packet missing")
        return 1

    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    proposed = packet.get("proposed_ms_lane_headline") or {}
    archive = packet.get("frozen_headline_prior_ms_archive") or {}

    policy_backup = None
    if HEADLINE_POLICY.is_file():
        policy_backup = HEADLINE_POLICY.with_name(
            f"compression_track_a_headline_policy_v1.pre_v2_ms_headline_{_stamp()}.json"
        )

    plan = {
        "headline_policy_path": _rel(HEADLINE_POLICY),
        "headline_policy_backup": _rel(policy_backup) if policy_backup else None,
        "paste_snippet_path": _rel(PASTE_SNIPPET),
        "pointer_rebuild": "scripts/build_master_codebook_bench_lexicon_pointer_v1.py",
    }

    if args.dry_run:
        print(json.dumps({"dry_run": True, "plan": plan}, ensure_ascii=False))
        return 0

    if HEADLINE_POLICY.is_file() and policy_backup:
        shutil.copy2(HEADLINE_POLICY, policy_backup)

    saving = float(proposed.get("global_token_saving_rate") or 0)
    jaccard = float(proposed.get("avg_reconstruction_fidelity_jaccard") or 0)
    new_policy = {
        "schema": "compression_track_a_headline_policy_v1",
        "generated_at_utc": _utc(),
        "decision": "PASS_CANDIDATE",
        "final_action": "MS_LANE_HEADLINE_SYNC (internal policy)",
        "headline_kpi_update": "APPLIED_v2_hangul_curated_ms_lane",
        "headline_kpi_update_reason": (
            "Commander MS lane: sync policy/pointer to v2 ACTIVE bench (41708 lexicon). "
            "MS submission HWPX archive KPI preserved under ms_submission_archive."
        ),
        "frozen_headline_prior": {
            "global_token_saving_rate": saving,
            "global_token_saving_rate_pct": proposed.get("global_token_saving_rate_pct"),
            "avg_reconstruction_fidelity_jaccard": jaccard,
            "note": "MS lane · CENTRAL · NVIDIA paste — Track A ACTIVE bench (Hangul v2, 41708)",
        },
        "ms_submission_archive": {
            "global_token_saving_rate": float(archive.get("global_token_saving_rate") or 0.47538677918424754),
            "global_token_saving_rate_pct": archive.get("global_token_saving_rate_pct") or 47.54,
            "avg_reconstruction_fidelity_jaccard": float(
                archive.get("avg_reconstruction_fidelity_jaccard") or 0.8904921794966301
            ),
            "note": "Submitted MS ma-jung HWPX/PDF — do not auto-rewrite",
        },
        "delta_vs_ms_submission_archive_pp": packet.get("delta_vs_prior_ms_archive_pp"),
        "remeasure_41708": {
            "script": "scripts/run_ultra_compression_default.py",
            "regression_script": "scripts/check_compression_golden_bench_regression_v1.py",
            "lexicon_path": _rel(P41708) if P41708.is_file() else None,
            "lexicon_term_count": 41708,
            "case_count": proposed.get("case_count") or 40,
            "global_token_saving_rate": saving,
            "global_token_saving_rate_pct": proposed.get("global_token_saving_rate_pct"),
            "avg_reconstruction_fidelity_jaccard": jaccard,
            "sensitive_violation_count": proposed.get("sensitive_violation_count"),
            "active_report": _rel(ACTIVE),
        },
        "dual_reporting": packet.get("dual_reporting_contract"),
        "hangul_curated_v2_ms_headline_signoff": _rel(SIGNOFF),
        "boundary": (
            "Production bench ACTIVE = v2 41708. MS submission files unchanged. "
            "External copy must label archive vs active bench when both cited."
        ),
    }
    HEADLINE_POLICY.parent.mkdir(parents=True, exist_ok=True)
    HEADLINE_POLICY.write_text(json.dumps(new_policy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    PASTE_SNIPPET.parent.mkdir(parents=True, exist_ok=True)
    PASTE_SNIPPET.write_text(_paste_body(proposed, archive), encoding="utf-8")

    log = {
        "schema": "hangul_curated_v2_ms_headline_apply_v1",
        "applied_at_utc": _utc(),
        "plan": plan,
        "proposed_ms_lane_headline": proposed,
        "ms_submission_archive": new_policy["ms_submission_archive"],
        "headline_kpi_update": new_policy["headline_kpi_update"],
        "raw_repair_note": "Policy/pointer MS lane only; not repair_v2 uplift claim.",
    }
    APPLY_LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "headline_kpi_update": new_policy["headline_kpi_update"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
