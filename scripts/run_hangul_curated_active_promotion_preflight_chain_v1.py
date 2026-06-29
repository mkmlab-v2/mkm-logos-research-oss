#!/usr/bin/env python3
"""H4: ACTIVE report promotion preflight (+ optional signoff/apply)."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(cmd: list[str]) -> int:
    print("+", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--commander-active-approve",
        action="store_true",
        help="Record signoff and apply ACTIVE swap if packet promotion_ready.",
    )
    ap.add_argument("--dry-run-apply", action="store_true")
    args = ap.parse_args()

    py = sys.executable
    packet_rc = _run([py, "scripts/build_hangul_curated_active_promotion_packet_v1.py"])
    if packet_rc not in (0, 2):
        print("FAIL: active promotion packet build")
        return packet_rc

    candidate = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_HANGUL_CURATED_CANDIDATE_V1.json"
    reg_rc = _run([
        py,
        "scripts/check_compression_golden_bench_regression_v1.py",
        "--active-report",
        str(candidate),
    ])
    if reg_rc != 0:
        print("WARN: candidate regression check exit", reg_rc)

    if args.commander_active_approve:
        if packet_rc == 2:
            print("ABORT: promotion_ready=false — cannot approve")
            return 2
        reg_rc = _run([
            py,
            "scripts/check_compression_golden_bench_regression_v1.py",
            "--active-report",
            str(ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_HANGUL_CURATED_CANDIDATE_V1.json"),
        ])
        if reg_rc != 0:
            print("ABORT: candidate fails golden regression floors")
            return reg_rc
        rc = _run([
            py,
            "scripts/record_hangul_curated_active_promotion_signoff_v1.py",
            "--commander-active-approve",
        ])
        if rc != 0:
            return rc
        apply_cmd = [py, "scripts/apply_hangul_curated_active_report_signoff_v1.py"]
        if args.dry_run_apply:
            apply_cmd.append("--dry-run")
        apply_rc = _run(apply_cmd)
        if apply_rc != 0:
            return apply_rc

    print("OK: hangul_curated_active_promotion_preflight_chain complete")
    return 0 if packet_rc == 0 else packet_rc


if __name__ == "__main__":
    raise SystemExit(main())
