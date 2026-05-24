#!/usr/bin/env python3
"""Record commander B-track sign-off for RQ-021 (approved scope vs explicit HOLD)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "docs/final/artifacts/rq021_commander_btrack_signoff_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p.resolve()).replace("\\", "/")


def main() -> int:
    ap = argparse.ArgumentParser(description="RQ-021 commander B-track signoff")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--signoff-by", default="commander")
    args = ap.parse_args()

    doc: dict[str, Any] = {
        "schema": "rq021_commander_btrack_signoff_v1",
        "signoff_utc": _utc(),
        "signoff_by": args.signoff_by,
        "hypothesis_tier": "B",
        "research_only": True,
        "approved": {
            "rq021_btrack_continue": True,
            "headline_policy_golden_core_only": {
                "jaccard": 0.872742,
                "source": "golden_core_only",
                "note": "FAIL-COMP-004 — blended N400 not headline",
            },
            "hypo_cooc_sidecar_on_dryrun": True,
            "cooc_v2_prefix_gated_non_gating": True,
            "per_lane_report_ssot": _rel(ROOT / "reports/golden40_expansion_per_lane_report_v1_latest.json"),
            "prophecy_streak_btrack_observation_only": True,
            "evolution_policy_unchanged": True,
        },
        "explicit_hold": {
            "p4_blended_n400_gate": False,
            "active_report_kpi_update": False,
            "ms_paste_hwpx_kpi_body": False,
            "track_a_live_trading_auto_merge": False,
            "promote_op28_headline": False,
            "holdout_threshold_apply": False,
            "security_integrity_task_reenable": False,
        },
        "evidence_pointers": {
            "per_lane_report": _rel(ROOT / "reports/golden40_expansion_per_lane_report_v1_latest.json"),
            "wave5": _rel(ROOT / "reports/rq021_compression_lane_wave5_v1_latest.json"),
            "cooc_v2": _rel(ROOT / "reports/other_cooc_cartesian_routing_poc_v2_latest.json"),
            "bridge_pointer": _rel(
                ROOT / "docs/final/artifacts/ancient_corpus_compression_sre_bridge_pointer_v1_latest.json"
            ),
            "isolation_summary": _rel(
                ROOT / "reports/golden40_expansion_lane_isolation_summary_v1_latest.json"
            ),
        },
        "next_btrack_only": [
            "Operate with per_lane_report + hypo-cooc-sidecar on expansion dryruns",
            "MS lane opens only on explicit 「MS 작업하자」",
            "P4 blended promotion requires new evidence or separate signoff",
        ],
        "fail_comp_004": "This signoff does not authorize ACTIVE or frozen 47.5%/0.890 MS headline changes.",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": _rel(args.out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
