#!/usr/bin/env python3
"""Tiered DSS authority pin policy — ingest gate vs historical frontline cycle (B-track)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXT3 = ROOT / "projects/dss-4d-ingest/outputs/authority_readiness_command_center_followup_20260327_h_ext3.json"
DEFAULT_RECON = ROOT / "reports/dss_authority_readiness_reconciliation_latest.json"
DEFAULT_FUSION = ROOT / "reports/fusion_join_policy_research_v1_latest.json"
DEFAULT_COMPARE = ROOT / "reports/dss_ndjson_profile_surface_compare_latest.json"
DEFAULT_OUT = ROOT / "reports/dss_authority_pin_policy_research_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ext3-authority-json", type=Path, default=DEFAULT_EXT3)
    ap.add_argument("--reconciliation-json", type=Path, default=DEFAULT_RECON)
    ap.add_argument("--fusion-policy-json", type=Path, default=DEFAULT_FUSION)
    ap.add_argument("--profile-compare-json", type=Path, default=DEFAULT_COMPARE)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    ext3 = _load(args.ext3_authority_json)
    recon = _load(args.reconciliation_json)
    fusion = _load(args.fusion_policy_json)
    profile_compare = _load(args.profile_compare_json)

    ext3_status = str(ext3.get("status") or "MISSING").upper()
    cycle_auth = None
    if recon:
        fc = recon.get("frontline_cycle") if isinstance(recon.get("frontline_cycle"), dict) else {}
        cycle_auth = fc.get("authority_readiness_status_parsed")
    fusion_status = None
    if fusion:
        gate = fusion.get("latest_gate") if isinstance(fusion.get("latest_gate"), dict) else {}
        fusion_status = gate.get("status")

    tier1_ok = ext3_status == "READY" and fusion_status == "PASS"
    ingest_rec = "MANIFEST_SUMMARY" if tier1_ok else "WATCH"
    if ext3_status == "BLOCKED":
        ingest_rec = "BLOCKED_EXT3"

    cycle_note = (
        "Unified frontline cycle authority aligned with ext3 pin."
        if cycle_auth == "READY"
        else "Pre-ext3 ext2-era insight brief; BLOCKED is expected until ext3 supersedes cycle pin."
    )
    operator_summary = (
        "tier_1 ext3 READY + tier_2 cycle READY aligned; fusion PASS governs manifest-summary ingest."
        if ext3_status == "READY" and cycle_auth == "READY"
        else (
            "Use tier_1 ext3 READY + fusion PASS for manifest-summary ingest; "
            "tier_2 cycle BLOCKED is historical baseline, not ingest veto."
        )
    )

    payload = {
        "schema": "dss_authority_pin_policy_research_v1",
        "generated_at_utc": _utc_now(),
        "research_rail": "B",
        "hypothesis_tier": "[HYPO]",
        "gating_status": "NON_GATING",
        "tiers": {
            "tier_1_ingest_gate": {
                "ssot": "ext3_hebrew_priority_pin",
                "path": str(args.ext3_authority_json),
                "status": ext3_status,
                "governs": ["ingest_dss_ndjson_token_manifest", "biblical_resonance_ndjson_uplift"],
            },
            "tier_2_cycle_historical": {
                "ssot": "unified_frontline_cycle_authority_readiness",
                "status": cycle_auth,
                "note": cycle_note,
            },
        },
        "fusion_join": {
            "policy_path": str(args.fusion_policy_json),
            "status": fusion_status,
        },
        "ndjson_profiles": {
            "compare_path": str(args.profile_compare_json),
            "recommended_profile": profile_compare.get("recommended_profile"),
            "weekly_ab_ssot": "default_3file",
            "hebrew_priority_reports": "ext3_only",
        },
        "resolution": {
            "ext3_vs_cycle_status_equal": ext3_status == cycle_auth if cycle_auth else None,
            "policy_aligned_for_ingest": tier1_ok,
            "ingest_recommendation": ingest_rec,
            "operator_summary": operator_summary,
        },
        "track_a_promotion": "blocked",
        "live_trading_trigger": "forbidden",
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output": str(args.output_json),
                "policy_aligned_for_ingest": tier1_ok,
                "ingest_recommendation": ingest_rec,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
