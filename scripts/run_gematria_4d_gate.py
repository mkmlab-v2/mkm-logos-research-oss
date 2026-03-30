#!/usr/bin/env python3
"""Run symbol-vector join, alignment, uplift A/B, then gate check."""

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
    ap = argparse.ArgumentParser(description="One-shot gematria-4d gate runner")
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--min-resonance-rate", type=float, default=0.80)
    ap.add_argument("--min-mean-axis-pearson", type=float, default=-0.20)
    ap.add_argument("--min-saving-delta", type=float, default=-0.20)
    args = ap.parse_args()
    py = args.python

    _run([py, "scripts/join_symbol_vector_4d.py"])
    _run(
        [
            py,
            "scripts/report_symbol_gematria_alignment.py",
            "--input",
            "reports/constitution/btrack_pilot/symbol_candidates_with_vector4d_latest.jsonl",
            "--out",
            "reports/constitution/btrack_pilot/symbol_gematria_alignment_test_nonzero.json",
            "--sample-mode",
            "gematria_nonzero",
            "--sample-size",
            "120",
            "--resonance-threshold",
            "0.85",
        ]
    )
    _run([py, "scripts/report_gematria_4d_uplift_ab.py"])
    _run(
        [
            py,
            "scripts/check_gematria_4d_gate.py",
            "--min-resonance-rate",
            str(args.min_resonance_rate),
            "--min-mean-axis-pearson",
            str(args.min_mean_axis_pearson),
            "--min-saving-delta",
            str(args.min_saving_delta),
        ]
    )
    print("OK: gematria-4d gate pipeline completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
