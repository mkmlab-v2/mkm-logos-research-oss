#!/usr/bin/env python3
"""Bridge #7: wisdom under uncertainty via Gemini ([HYPO], aligns q04 gold)."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_concept_bridge_wisdom_uncertainty_gemini_v1_latest.json"
CONCEPT_KO = "불확실과 두려움 속 지혜"
CONCEPT_ID = "concept:wisdom_under_uncertainty"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    cmd = [
        sys.executable,
        str(ROOT / "scripts/build_logos_concept_bridge_gemini_v1.py"),
        "--concept-ko",
        CONCEPT_KO,
        "--concept-id",
        CONCEPT_ID,
        "--output-json",
        str(DEFAULT_OUT),
        "--raw-out",
        str(ROOT / "reports/gemini_batch/logos_concept_bridge_wisdom_uncertainty_gemini_v1_raw.txt"),
    ]
    if args.dry_run:
        cmd.append("--dry-run")
    return subprocess.call(cmd, cwd=str(ROOT))


if __name__ == "__main__":
    raise SystemExit(main())
