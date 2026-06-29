#!/usr/bin/env python3
"""[HYPO] Commander research sign-off for NG spine MKVS arms (evidence-only; no ACTIVE headline)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
GOLDEN_EVAL = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_spine_binary_billable_eval_v1_latest.json"
)
LONGFORM_EVAL = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_spine_binary_billable_eval_longform_v1_latest.json"
)
OUT_DEFAULT = ROOT / "reports/ng40_spine_binary_research_signoff_v1_latest.json"
BLS_SCHEDULE_OUT = ROOT / "reports/bls_unemployment_watch_schedule_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--signoff-by", default="commander")
    ap.add_argument(
        "--note",
        default=(
            "NG spine MKVS research lane approved; longform dual_axis is evidence-only "
            "and excluded from promotion headline / ACTIVE apply."
        ),
    )
    args = ap.parse_args()

    golden = _load(GOLDEN_EVAL)
    longform = _load(LONGFORM_EVAL)
    lf_agg = (longform or {}).get("aggregate") or {}

    out = {
        "schema": "ng40_spine_binary_research_signoff_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "signoff_by": args.signoff_by,
        "signoff_utc": _utc(),
        "note": args.note,
        "approved_scope_ko": "NG-40 verbatim spine MKVS binary 연구 샌드박스·concept_bridge prior",
        "forbidden_ko": [
            "longform 또는 golden40 MKVS metrics를 selected_arm / ACTIVE 헤드라인으로 승격",
            "export_prep_ready만으로 Track A apply",
            "실매매·예언 resolve 자동 트리거",
        ],
        "evidence_arms": {
            "golden40": {
                "arm_id": (golden or {}).get("arm_id"),
                "pointer": str(GOLDEN_EVAL.relative_to(ROOT)).replace("\\", "/"),
                "aggregate": (golden or {}).get("aggregate"),
            },
            "longform": {
                "arm_id": (longform or {}).get("arm_id"),
                "pointer": str(LONGFORM_EVAL.relative_to(ROOT)).replace("\\", "/"),
                "aggregate": lf_agg,
                "excluded_from_headline_selection": True,
                "dual_axis_beat_binary_vs_frozen": lf_agg.get(
                    "dual_axis_beat_binary_vs_frozen"
                ),
            },
        },
        "headline_selection": {
            "selected_arm": None,
            "policy": "research_only_arms_registry; see btrack_nextgen_promotion_candidate_packet",
        },
        "pointers": {
            "research_only_arms_manifest": (
                "reports/btrack_nextgen_research_only_arms_v1_latest.json"
            ),
            "promotion_packet": "reports/btrack_nextgen_promotion_candidate_packet_v1_latest.json",
            "commander_phase5_manifest": "reports/ng40_commander_signoff_push_v1_latest.json",
        },
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    bls_sched = {
        "schema": "bls_unemployment_watch_schedule_v1",
        "generated_at_utc": _utc(),
        "question_id": "seed.macro.us_bls_unrate_gt_43_20260606",
        "status": "watch_until_release",
        "release_window_local_date": "2026-06-06",
        "reprobe_sequence": [
            "py scripts/probe_bls_unemployment_may2026_v1.py",
            "powershell -NoProfile -ExecutionPolicy Bypass -File "
            "scripts/Invoke-GeneralProphecyBlsUnrateResolve_v1.ps1 -Outcome <true|false>",
        ],
        "patrol_wrapper": "scripts/run_general_prophecy_pre_june10_patrol_v1.ps1",
        "probe_pointer": "reports/bls_unemployment_probe_v1_latest.json",
        "resolve_only_when": "probe may_2026_release_ready == true",
    }
    BLS_SCHEDULE_OUT.parent.mkdir(parents=True, exist_ok=True)
    BLS_SCHEDULE_OUT.write_text(
        json.dumps(bls_sched, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(
        json.dumps(
            {
                "wrote": str(args.out_json),
                "bls_schedule": str(BLS_SCHEDULE_OUT),
                "longform_dual_axis": lf_agg.get("dual_axis_beat_binary_vs_frozen"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
