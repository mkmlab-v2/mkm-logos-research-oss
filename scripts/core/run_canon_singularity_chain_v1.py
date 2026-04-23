#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str], dry_run: bool) -> int:
    print(" ".join(cmd))
    if dry_run:
        return 0
    cp = subprocess.run(cmd, check=False)
    return int(cp.returncode)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Run canon-only singularity report + balanced + lane summary chain."
    )
    ap.add_argument("--canon-jsonl", default="data/logos/verse_decoded_v2.jsonl")
    ap.add_argument("--regime-map-json", default="data/regimes/regime_map_btc_ext.json")
    ap.add_argument("--top-n", type=int, default=50)
    ap.add_argument("--quota-per-regime", type=int, default=12)
    ap.add_argument(
        "--report-output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_only_v1.json",
    )
    ap.add_argument(
        "--balanced-output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_balanced_canon_only_v1.json",
    )
    ap.add_argument(
        "--summary-output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_lane_summary_v1.json",
    )
    ap.add_argument(
        "--quality-gate-output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_quality_gate_v1.json",
    )
    ap.add_argument(
        "--quality-gate-history-jsonl",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_quality_gate_history_v1.jsonl",
    )
    ap.add_argument(
        "--quality-gate-health-summary-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_quality_gate_health_summary_v1.json",
    )
    ap.add_argument(
        "--quality-gate-policy-output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_quality_gate_policy_eval_v1.json",
    )
    ap.add_argument(
        "--insight-output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_insight_minimum_v1.json",
    )
    ap.add_argument(
        "--insight-quality-gate-output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_insight_minimum_quality_gate_v1.json",
    )
    ap.add_argument("--insight-top-n", type=int, default=12)
    ap.add_argument("--skip-insight", action="store_true")
    ap.add_argument("--quality-gate-health-window", type=int, default=30)
    ap.add_argument("--enforce-health", action="store_true")
    ap.add_argument("--health-max-fail-count", type=int, default=0)
    ap.add_argument("--health-min-pass-rate", type=float, default=1.0)
    ap.add_argument("--health-allow-yellow", action="store_true")
    ap.add_argument("--summary-top-n", type=int, default=20)
    ap.add_argument("--expected-canon-rows", type=int, default=28741)
    ap.add_argument("--skip-validate", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[2]
    py = sys.executable

    cmd_report = [
        py,
        str(root / "scripts" / "core" / "build_original_corpus_regime_singularity_report_v1.py"),
        "--canon-only",
        "--canon-jsonl",
        str(args.canon_jsonl),
        "--top-n",
        str(int(args.top_n)),
        "--output-json",
        str(args.report_output_json),
    ]
    cmd_balanced = [
        py,
        str(root / "scripts" / "core" / "build_original_corpus_regime_singularity_balanced_report_v1.py"),
        "--canon-only",
        "--canon-jsonl",
        str(args.canon_jsonl),
        "--regime-map-json",
        str(args.regime_map_json),
        "--quota-per-regime",
        str(int(args.quota_per_regime)),
        "--output-json",
        str(args.balanced_output_json),
    ]
    cmd_summary = [
        py,
        str(root / "scripts" / "core" / "build_canon_singularity_lane_summary_v1.py"),
        "--input-json",
        str(args.report_output_json),
        "--top-n",
        str(int(args.summary_top_n)),
        "--output-json",
        str(args.summary_output_json),
    ]
    cmd_validate = [
        py,
        str(root / "scripts" / "core" / "validate_canon_singularity_outputs_v1.py"),
        "--report-json",
        str(args.report_output_json),
        "--balanced-json",
        str(args.balanced_output_json),
        "--summary-json",
        str(args.summary_output_json),
        "--expected-canon-rows",
        str(int(args.expected_canon_rows)),
        "--output-json",
        str(args.quality_gate_output_json),
        "--history-jsonl",
        str(args.quality_gate_history_jsonl),
    ]
    cmd_health_summary = [
        py,
        str(root / "scripts" / "core" / "build_canon_singularity_gate_health_summary_v1.py"),
        "--history-jsonl",
        str(args.quality_gate_history_jsonl),
        "--window",
        str(int(args.quality_gate_health_window)),
        "--output-json",
        str(args.quality_gate_health_summary_json),
    ]
    cmd_enforce_health = [
        py,
        str(root / "scripts" / "core" / "enforce_canon_singularity_gate_health_v1.py"),
        "--health-summary-json",
        str(args.quality_gate_health_summary_json),
        "--max-fail-count",
        str(int(args.health_max_fail_count)),
        "--min-pass-rate",
        str(float(args.health_min_pass_rate)),
        "--output-json",
        str(args.quality_gate_policy_output_json),
    ]
    if bool(args.health_allow_yellow):
        cmd_enforce_health.append("--allow-yellow")
    cmd_insight = [
        py,
        str(root / "scripts" / "core" / "build_canon_singularity_insight_minimum_v1.py"),
        "--summary-json",
        str(args.summary_output_json),
        "--top-n",
        str(int(args.insight_top_n)),
        "--output-json",
        str(args.insight_output_json),
    ]
    cmd_insight_gate = [
        py,
        str(root / "scripts" / "core" / "validate_canon_singularity_insight_minimum_v1.py"),
        "--input-json",
        str(args.insight_output_json),
        "--output-json",
        str(args.insight_quality_gate_output_json),
    ]

    cmds = [cmd_report, cmd_balanced, cmd_summary]
    rc_validate = 0

    for cmd in cmds:
        rc = _run(cmd, dry_run=bool(args.dry_run))
        if rc != 0:
            return rc
    if not args.skip_validate:
        rc_validate = _run(cmd_validate, dry_run=bool(args.dry_run))
        rc_health = _run(cmd_health_summary, dry_run=bool(args.dry_run))
        if rc_validate != 0:
            return rc_validate
        if rc_health != 0:
            return rc_health
        if bool(args.enforce_health):
            rc_enforce = _run(cmd_enforce_health, dry_run=bool(args.dry_run))
            if rc_enforce != 0:
                return rc_enforce
    if not args.skip_insight:
        rc_insight = _run(cmd_insight, dry_run=bool(args.dry_run))
        if rc_insight != 0:
            return rc_insight
        rc_insight_gate = _run(cmd_insight_gate, dry_run=bool(args.dry_run))
        if rc_insight_gate != 0:
            return rc_insight_gate
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

