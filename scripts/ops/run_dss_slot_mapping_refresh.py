# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.7, L:0.8, K:0.7, M:0.7}
# Balance: 87
# Purpose: Refresh DSS slot mapping artifacts with confidence v2.
# Keywords: dss, slot mapping, confidence, btrack, reports
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
FILTER = ROOT / "scripts" / "filter_dss_enriched_canonical_only.py"
MAPPER = ROOT / "scripts" / "map_dss_rows_to_16_anchor_slots.py"
COMPARE = ROOT / "scripts" / "report_dss_slot_mapping_comparison.py"
CALIB = ROOT / "scripts" / "ops" / "export_dss_confidence_calibration_log.py"

FULL_IN = ROOT / "data" / "logos" / "manuscripts" / "dss_parsed_enriched.jsonl"
CANON_IN = ROOT / "data" / "logos" / "manuscripts" / "dss_parsed_enriched_canonical_only.jsonl"
FULL_OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_dss_direct_slot_mapping_latest.json"
CANON_OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_dss_direct_slot_mapping_canonical_latest.json"


def _run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd)}\n{r.stdout}\n{r.stderr}")
    if r.stdout:
        print(r.stdout.strip())


def main() -> int:
    ap = argparse.ArgumentParser(description="Refresh DSS slot-mapping reports with confidence v2.")
    ap.add_argument("--confidence-mode", choices=("v1", "v2"), default="v2")
    args = ap.parse_args()

    _run([sys.executable, str(FILTER)])
    _run(
        [
            sys.executable,
            str(MAPPER),
            "--dss-enriched",
            str(FULL_IN),
            "--out",
            str(FULL_OUT),
            "--confidence-mode",
            args.confidence_mode,
        ]
    )
    _run(
        [
            sys.executable,
            str(MAPPER),
            "--dss-enriched",
            str(CANON_IN),
            "--out",
            str(CANON_OUT),
            "--confidence-mode",
            args.confidence_mode,
        ]
    )
    _run([sys.executable, str(COMPARE)])
    _run([sys.executable, str(CALIB)])
    print("DONE: DSS slot mapping refresh complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
