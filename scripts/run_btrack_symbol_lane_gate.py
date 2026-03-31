#!/usr/bin/env python3
"""One-shot runner for B-Track symbol lane extraction and gate evaluation."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GATE_TEMPLATE = ROOT / "data" / "logos" / "btrack_pilot" / "gates" / "symbol_lane_gate_template.json"
DEFAULT_NUMERIC_TEMPLATE = ROOT / "data" / "logos" / "btrack_pilot" / "gates" / "symbol_numeric_seed_v1.json"


def _run(cmd: list[str]) -> None:
    print(f"[run] {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=ROOT)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def _tag_path(path: str, tag: str) -> str:
    if tag == "latest":
        return path
    marker = "_latest"
    if marker in path:
        return path.replace(marker, f"_{tag}_latest")
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description="Run B-Track symbol lane gate in one shot")
    ap.add_argument("--python", default=sys.executable, help="Python executable")
    ap.add_argument(
        "--include-shared-vault",
        action="store_true",
        help="Include shared vault docs while building DSS enriched jsonl.",
    )
    ap.add_argument(
        "--extract-top-k",
        type=int,
        default=1000,
        help="Candidate pool size for extract_btrack_symbol_candidates (align with fusion evidence loop).",
    )
    ap.add_argument(
        "--extract-min-df",
        type=int,
        default=2,
        help="Minimum document frequency for symbol extraction (default keeps lane gate stable).",
    )
    ap.add_argument(
        "--curate-top-k",
        type=int,
        default=200,
        help="Max rows passed to curate_btrack_symbol_candidates.",
    )
    ap.add_argument(
        "--curate-min-count",
        type=int,
        default=200,
        help="Minimum curated rows guaranteed by curate_btrack_symbol_candidates fallback.",
    )
    ap.add_argument(
        "--gate-template",
        default=str(DEFAULT_GATE_TEMPLATE),
        help="Gate template path for evaluate_btrack_symbol_lane_gate.",
    )
    ap.add_argument(
        "--profile-tag",
        default="stable",
        help="Output profile tag (e.g. stable, exploratory).",
    )
    ap.add_argument(
        "--numeric-template",
        default=str(DEFAULT_NUMERIC_TEMPLATE),
        help="Numeric symbol seed template for injection coverage report.",
    )
    ap.add_argument(
        "--approve-numeric-near-miss",
        action="store_true",
        help="Enable numeric near-miss promotion candidate export (requires explicit approval).",
    )
    args = ap.parse_args()
    py = args.python
    tag = str(args.profile_tag).strip() or "stable"

    cand_jsonl = _tag_path("reports/constitution/btrack_pilot/symbol_candidates_latest.jsonl", tag)
    cand_summary = _tag_path("reports/constitution/btrack_pilot/symbol_candidates_summary_latest.json", tag)
    curated_jsonl = _tag_path("reports/constitution/btrack_pilot/symbol_candidates_curated_latest.jsonl", tag)
    curated_summary = _tag_path("reports/constitution/btrack_pilot/symbol_candidates_curated_summary_latest.json", tag)
    source_split_json = _tag_path("reports/constitution/btrack_pilot/symbol_source_split_latest.json", tag)
    lane_dss_jsonl = _tag_path("reports/constitution/btrack_pilot/symbol_lane_dss_priority_latest.jsonl", tag)
    lane_mixed_jsonl = _tag_path("reports/constitution/btrack_pilot/symbol_lane_mixed_latest.jsonl", tag)
    lane_apo_jsonl = _tag_path("reports/constitution/btrack_pilot/symbol_lane_apocrypha_priority_latest.jsonl", tag)
    lane_summary_json = _tag_path("reports/constitution/btrack_pilot/symbol_lane_summary_latest.json", tag)
    lane_gate_json = _tag_path("reports/constitution/btrack_pilot/symbol_lane_gate_latest.json", tag)
    thematic_json = _tag_path("reports/constitution/btrack_pilot/symbol_top50_by_source_thematic_latest.json", tag)
    abc_jsonl = _tag_path("reports/constitution/btrack_pilot/symbol_candidates_abc_labeled_latest.jsonl", tag)
    abc_summary = _tag_path("reports/constitution/btrack_pilot/symbol_candidates_abc_summary_latest.json", tag)
    c_queue_jsonl = _tag_path("reports/constitution/btrack_pilot/symbol_c_validation_queue_latest.jsonl", tag)
    numeric_report_json = _tag_path("reports/constitution/btrack_pilot/symbol_numeric_injection_latest.json", tag)
    numeric_promotion_json = _tag_path("reports/constitution/btrack_pilot/numeric_promotion_candidates_latest.json", tag)

    dss_cmd = [py, "scripts/build_btrack_dss_enriched_from_docs.py"]
    if args.include_shared_vault:
        dss_cmd.append("--include-shared-vault")
    _run(dss_cmd)
    _run(
        [
            py,
            "scripts/extract_btrack_symbol_candidates.py",
            "--top-k",
            str(args.extract_top_k),
            "--min-df",
            str(args.extract_min_df),
            "--dss",
            "data/logos/manuscripts/dss_parsed_enriched.jsonl",
            "--apo",
            "data/logos/manuscripts/apocrypha_std.jsonl",
            "--out",
            cand_jsonl,
            "--summary",
            cand_summary,
        ]
    )
    _run(
        [
            py,
            "scripts/curate_btrack_symbol_candidates.py",
            "--top-k",
            str(args.curate_top_k),
            "--min-curated-count",
            str(args.curate_min_count),
            "--in-jsonl",
            cand_jsonl,
            "--out-jsonl",
            curated_jsonl,
            "--out-summary",
            curated_summary,
        ]
    )
    _run(
        [
            py,
            "scripts/report_symbol_numeric_injection.py",
            "--input-jsonl",
            curated_jsonl,
            "--raw-jsonl",
            cand_jsonl,
            "--numeric-template",
            str(args.numeric_template),
            "--out-json",
            numeric_report_json,
        ]
    )
    approval_flag = "approve_numeric_near_miss=true" if args.approve_numeric_near_miss else ""
    _run(
        [
            py,
            "scripts/build_symbol_numeric_promotion_candidates.py",
            "--input-json",
            numeric_report_json,
            "--out-json",
            numeric_promotion_json,
            "--approval-flag",
            approval_flag,
        ]
    )
    _run([py, "scripts/report_btrack_symbol_source_split.py", "--in-jsonl", curated_jsonl, "--out-json", source_split_json])
    _run(
        [
            py,
            "scripts/build_btrack_symbol_promotion_lanes.py",
            "--in-jsonl",
            curated_jsonl,
            "--out-dss-jsonl",
            lane_dss_jsonl,
            "--out-mixed-jsonl",
            lane_mixed_jsonl,
            "--out-apocrypha-jsonl",
            lane_apo_jsonl,
            "--out-summary-json",
            lane_summary_json,
        ]
    )
    _run(
        [
            py,
            "scripts/evaluate_btrack_symbol_lane_gate.py",
            "--lane-summary",
            lane_summary_json,
            "--gate",
            str(args.gate_template),
            "--out",
            lane_gate_json,
        ]
    )
    _run([py, "scripts/report_symbol_top_by_source_thematic.py", "--input-jsonl", curated_jsonl, "--out-json", thematic_json])
    _run(
        [
            py,
            "scripts/label_symbol_candidates_abc.py",
            "--single-jsonl",
            curated_jsonl,
            "--profile-tag",
            tag,
            "--out-jsonl",
            abc_jsonl,
            "--out-summary",
            abc_summary,
            "--out-c-queue-jsonl",
            c_queue_jsonl,
        ]
    )

    print("OK: B-Track symbol lane gate completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
