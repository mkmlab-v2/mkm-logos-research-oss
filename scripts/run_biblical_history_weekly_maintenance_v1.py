#!/usr/bin/env python3
"""Weekly B-track biblical history maintenance (no apocrypha re-fetch · no full lane permutations)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/biblical_history_weekly_maintenance_latest.json"


def _run(cmd: list[str]) -> int:
    return int(subprocess.run(cmd, cwd=str(ROOT), check=False).returncode)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lookback-days", type=int, default=90)
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[tuple[str, list[str]]] = [
        (
            "production_news_refresh_if_thin",
            [
                sys.executable,
                "scripts/refresh_biblical_history_production_news_v1.py",
                "--lookback-days",
                str(args.lookback_days),
            ],
        ),
        (
            "sync_ndjson_ssot_from_full_surface",
            [sys.executable, "scripts/sync_dss_ndjson_research_context_from_full_surface_v1.py"],
        ),
        ("authority_reconciliation", [sys.executable, "scripts/build_dss_authority_readiness_reconciliation_v1.py"]),
        ("authority_pin_policy", [sys.executable, "scripts/build_dss_authority_pin_policy_v1.py"]),
        (
            "refresh_research_slice",
            [
                sys.executable,
                "scripts/refresh_biblical_history_news_observation_slice_v1.py",
                "--run-resonance-eval",
                "--lookback-days",
                str(args.lookback_days),
            ],
        ),
        (
            "h_dss1_shuffle_negative_control",
            [
                sys.executable,
                "scripts/eval_biblical_history_h_dss1_chronicle_epoch_shuffle_negative_control_v1.py",
                "--shuffle-repeats",
                "500",
            ],
        ),
        ("biblical_resonance_production_ab", [sys.executable, "scripts/build_biblical_resonance_research_production_ab_v1.py"]),
        (
            "biblical_resonance_isolated_production_ab",
            [sys.executable, "scripts/build_biblical_resonance_isolated_production_ab_v1.py"],
        ),
        ("dss_ndjson_resonance_uplift", [sys.executable, "scripts/build_dss_ndjson_resonance_uplift_report_v1.py"]),
    ]
    if not args.skip_pytest:
        steps.append(
            (
                "pytest_research_lane",
                [sys.executable, "-m", "pytest", "tests/test_biblical_history_research_lane_v1.py", "-q"],
            )
        )
        steps.append(
            (
                "resync_ndjson_ssot_after_pytest",
                [sys.executable, "scripts/sync_dss_ndjson_research_context_from_full_surface_v1.py"],
            )
        )

    log: list[dict[str, object]] = []
    for name, cmd in steps:
        rc = _run(cmd)
        log.append({"step": name, "return_code": rc})
        if rc != 0:
            print(json.dumps({"ok": False, "failed_step": name, "log": log}, ensure_ascii=False), file=sys.stderr)
            args.output_json.write_text(
                json.dumps({"schema": "biblical_history_weekly_maintenance_v1", "ok": False, "steps": log}, indent=2)
                + "\n",
                encoding="utf-8",
            )
            return rc

    payload = {
        "schema": "biblical_history_weekly_maintenance_v1",
        "ok": True,
        "steps": log,
        "artifacts": {
            "reconciliation": "reports/dss_authority_readiness_reconciliation_latest.json",
            "ab": "reports/biblical_resonance_research_production_ab_latest.json",
            "isolated_ab": "reports/biblical_resonance_isolated_production_ab_latest.json",
            "uplift": "reports/dss_ndjson_resonance_uplift_latest.json",
            "shuffle_negative_control": "reports/biblical_history_h_dss1_chronicle_epoch_shuffle_negative_control_latest.json",
        },
        "research_rail": "B",
        "hypothesis_tier": "[HYPO]",
        "track_a_promotion": "blocked",
    }
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.output_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
