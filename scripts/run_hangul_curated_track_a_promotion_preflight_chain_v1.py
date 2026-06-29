#!/usr/bin/env python3
"""H3: build Track A lexicon promotion packet (+ optional signoff/apply)."""
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
        "--commander-track-a-lexicon-approve",
        action="store_true",
        help="Record signoff and apply production lexicon swap if packet promotion_ready.",
    )
    ap.add_argument("--dry-run-apply", action="store_true")
    args = ap.parse_args()

    py = sys.executable
    rc = _run([py, "scripts/build_hangul_curated_track_a_promotion_packet_v1.py"])
    if rc != 0 and rc != 2:
        print("FAIL: promotion packet build")
        return rc

    if args.commander_track_a_lexicon_approve:
        if rc == 2:
            print("ABORT: promotion_ready=false — cannot approve")
            return 2
        rc = _run([
            py,
            "scripts/record_hangul_curated_track_a_lexicon_promotion_signoff_v1.py",
            "--commander-track-a-lexicon-approve",
        ])
        if rc != 0:
            return rc
        apply_cmd = [py, "scripts/apply_hangul_curated_production_lexicon_signoff_v1.py"]
        if args.dry_run_apply:
            apply_cmd.append("--dry-run")
        rc = _run(apply_cmd)
        if rc != 0:
            return rc
        rc = _run([py, "scripts/build_master_codebook_bench_lexicon_pointer_v1.py"])
        if rc != 0:
            return rc

    print("OK: track_a_promotion_preflight_chain complete")
    return 0 if rc == 0 else rc


if __name__ == "__main__":
    raise SystemExit(main())
