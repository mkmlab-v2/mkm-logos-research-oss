#!/usr/bin/env python3
"""MS lane: headline policy sync from v2 ACTIVE (commander; submission archive unchanged)."""
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
    ap.add_argument("--commander-ms-approve", action="store_true")
    ap.add_argument("--dry-run-apply", action="store_true")
    args = ap.parse_args()

    py = sys.executable
    packet_rc = _run([py, "scripts/build_hangul_curated_v2_ms_headline_promotion_packet_v1.py"])
    if packet_rc not in (0, 2):
        return packet_rc

    if args.commander_ms_approve:
        if packet_rc == 2:
            print("ABORT: promotion_ready=false")
            return 2
        rc = _run([
            py,
            "scripts/record_hangul_curated_v2_ms_headline_promotion_signoff_v1.py",
            "--commander-ms-approve",
            "--note",
            "commander MS lane: headline policy 48.8%/0.869 from v2 ACTIVE; submission archive hold",
        ])
        if rc != 0:
            return rc
        apply_cmd = [py, "scripts/apply_hangul_curated_v2_ms_headline_signoff_v1.py"]
        if args.dry_run_apply:
            apply_cmd.append("--dry-run")
        rc = _run(apply_cmd)
        if rc != 0:
            return rc
        return _run([py, "scripts/build_master_codebook_bench_lexicon_pointer_v1.py"])

    print("OK: v2_ms_headline_chain complete (packet only; use --commander-ms-approve to apply)")
    return 0 if packet_rc == 0 else packet_rc


if __name__ == "__main__":
    raise SystemExit(main())
