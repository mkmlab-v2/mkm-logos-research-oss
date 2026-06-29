#!/usr/bin/env python3
"""H4 v2: ACTIVE candidate → signoff → apply (commander; MS paste HOLD)."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANDIDATE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_HANGUL_CURATED_V2_CANDIDATE.json"


def _run(cmd: list[str]) -> int:
    print("+", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commander-active-approve", action="store_true")
    ap.add_argument("--dry-run-apply", action="store_true")
    args = ap.parse_args()

    py = sys.executable
    packet_rc = _run([py, "scripts/build_hangul_curated_v2_active_promotion_packet_v1.py"])
    if packet_rc not in (0, 2):
        return packet_rc

    reg_args = [
        py,
        "scripts/check_compression_golden_bench_regression_v1.py",
        "--active-report",
        str(CANDIDATE),
        "--min-avg-jaccard",
        "0.868",
    ]
    reg_rc = _run(reg_args)

    if args.commander_active_approve:
        if packet_rc == 2:
            print("ABORT: promotion_ready=false")
            return 2
        if reg_rc != 0:
            reg_rc = _run(reg_args)
            if reg_rc != 0:
                print("ABORT: v2 candidate regression check failed")
                return reg_rc
        rc = _run([
            py,
            "scripts/record_hangul_curated_v2_active_promotion_signoff_v1.py",
            "--commander-active-approve",
            "--note",
            "commander approved v2 ACTIVE (41708 lexicon)",
        ])
        if rc != 0:
            return rc
        apply_cmd = [py, "scripts/apply_hangul_curated_v2_active_report_signoff_v1.py"]
        if args.dry_run_apply:
            apply_cmd.append("--dry-run")
        return _run(apply_cmd)

    print("OK: v2_active_promotion_chain complete")
    return 0 if packet_rc == 0 else packet_rc


if __name__ == "__main__":
    raise SystemExit(main())
