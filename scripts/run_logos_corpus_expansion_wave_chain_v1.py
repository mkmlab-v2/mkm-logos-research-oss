#!/usr/bin/env python3
"""Wave merge + corpus enrich + spread dual-gate (expansion slots 101+)."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wave", type=int, default=1)
    parser.add_argument("--skip-merge", action="store_true")
    args = parser.parse_args()

    if not args.skip_merge:
        proc = subprocess.run(
            [
                sys.executable,
                "scripts/apply_logos_corpus_expansion_merge_v1.py",
                "--hd-auto-wave",
                str(args.wave),
                "--skip-validate",
            ],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode
        print("OK: apply_logos_corpus_expansion_merge_v1.py")

    for script, extra in (
        ("scripts/enrich_logos_motif_gematria_from_corpus_v1.py", ["--all-enabled"]),
        ("scripts/run_logos_spread_tuning_chain_v1.py", []),
    ):
        proc = subprocess.run([sys.executable, script, *extra], cwd=ROOT, check=False)
        if proc.returncode != 0:
            print(f"FAIL: {script} exit {proc.returncode}", file=sys.stderr)
            return proc.returncode
        print(f"OK: {script}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
