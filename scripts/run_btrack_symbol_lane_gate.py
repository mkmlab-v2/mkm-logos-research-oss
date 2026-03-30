#!/usr/bin/env python3
"""One-shot runner for B-Track symbol lane extraction and gate evaluation."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(cmd: list[str]) -> None:
    print(f"[run] {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=ROOT)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


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
        "--curate-top-k",
        type=int,
        default=200,
        help="Max rows passed to curate_btrack_symbol_candidates.",
    )
    args = ap.parse_args()
    py = args.python

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
            "--dss",
            "data/logos/manuscripts/dss_parsed_enriched.jsonl",
            "--apo",
            "data/logos/manuscripts/apocrypha_std.jsonl",
            "--out",
            "reports/constitution/btrack_pilot/symbol_candidates_latest.jsonl",
            "--summary",
            "reports/constitution/btrack_pilot/symbol_candidates_summary_latest.json",
        ]
    )
    _run(
        [
            py,
            "scripts/curate_btrack_symbol_candidates.py",
            "--top-k",
            str(args.curate_top_k),
        ]
    )
    _run([py, "scripts/report_btrack_symbol_source_split.py"])
    _run([py, "scripts/build_btrack_symbol_promotion_lanes.py"])
    _run([py, "scripts/evaluate_btrack_symbol_lane_gate.py"])

    print("OK: B-Track symbol lane gate completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
