#!/usr/bin/env python3
"""One-click DSS B-track research round: ext3 sweep, slice-decoupled AB, compare, handoff."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/dss_research_round_latest.json"
DECOUPLED_SLICE = (
    ROOT / "docs/final/artifacts/news_observation_v1_biblical_history_research_slice_decoupled_latest.jsonl"
)


def _run(cmd: list[str]) -> int:
    return int(subprocess.run(cmd, cwd=str(ROOT), check=False).returncode)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--chunk-sizes", default="40,50,75,100")
    ap.add_argument("--max-surface-rows-per-file", type=int, default=1200)
    ap.add_argument("--lookback-days", type=int, default=90)
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[tuple[str, list[str]]] = [
        (
            "ext3_chunk_size_sweep_apply_best",
            [
                sys.executable,
                "scripts/run_dss_ext3_only_chunk_size_sweep_v1.py",
                "--chunk-sizes",
                args.chunk_sizes,
                "--max-surface-rows-per-file",
                str(args.max_surface_rows_per_file),
                "--apply-best",
            ],
        ),
        (
            "refresh_research_slice_without_ndjson",
            [
                sys.executable,
                "scripts/refresh_biblical_history_news_observation_slice_v1.py",
                "--skip-ndjson-context",
                "--run-resonance-eval",
                "--lookback-days",
                str(args.lookback_days),
            ],
        ),
        (
            "refresh_research_slice_decoupled_no_korea",
            [
                sys.executable,
                "scripts/refresh_biblical_history_news_observation_slice_v1.py",
                "--skip-ndjson-context",
                "--skip-korea-context",
                "--output-jsonl",
                str(DECOUPLED_SLICE),
            ],
        ),
        (
            "isolated_ab_slice_decoupled",
            [
                sys.executable,
                "scripts/build_biblical_resonance_isolated_production_ab_v1.py",
                "--research-slice-jsonl",
                str(DECOUPLED_SLICE),
                "--output-json",
                "reports/biblical_resonance_isolated_production_ab_slice_decoupled_latest.json",
            ],
        ),
        (
            "isolated_ab_default_refresh",
            [sys.executable, "scripts/build_biblical_resonance_isolated_production_ab_v1.py"],
        ),
        ("profile_compare", [sys.executable, "scripts/build_dss_ndjson_profile_surface_compare_v1.py"]),
        ("authority_pin_policy", [sys.executable, "scripts/build_dss_authority_pin_policy_v1.py"]),
        ("research_lane_handoff", [sys.executable, "scripts/build_dss_research_lane_handoff_v1.py"]),
        (
            "shuffle_negative_control",
            [
                sys.executable,
                "scripts/eval_biblical_history_h_dss1_chronicle_epoch_shuffle_negative_control_v1.py",
                "--shuffle-repeats",
                "500",
            ],
        ),
    ]
    if not args.skip_pytest:
        steps.append(
            (
                "pytest_research_lane",
                [sys.executable, "-m", "pytest", "tests/test_biblical_history_research_lane_v1.py", "-q"],
            )
        )

    log: list[dict[str, object]] = []
    for name, cmd in steps:
        rc = _run(cmd)
        log.append({"step": name, "return_code": rc})
        if rc != 0:
            print(json.dumps({"ok": False, "failed_step": name, "log": log}, ensure_ascii=False), file=sys.stderr)
            args.output_json.write_text(
                json.dumps({"schema": "dss_research_round_v1", "ok": False, "steps": log}, indent=2) + "\n",
                encoding="utf-8",
            )
            return rc

    payload = {
        "schema": "dss_research_round_v1",
        "ok": True,
        "steps": log,
        "artifacts": {
            "ext3_chunk_sweep": "reports/dss_ext3_only_chunk_size_sweep_latest.json",
            "profile_compare": "reports/dss_ndjson_profile_surface_compare_latest.json",
            "handoff": "reports/dss_research_lane_handoff_latest.json",
            "slice_decoupled_ab": "reports/biblical_resonance_isolated_production_ab_slice_decoupled_latest.json",
            "slice_decoupled_jsonl": str(DECOUPLED_SLICE.relative_to(ROOT)).replace("\\", "/"),
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
