#!/usr/bin/env python3
"""Track B: cross-bridge + matrix + showroom slice + B2B appendix (subprocess chain)."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_STEPS = (
    ("cross_bridge", [sys.executable, str(ROOT / "scripts/build_logos_verse_myeongri_cross_bridge_v1.py"), "--validate-schema"]),
    ("cross_bridge_matrix", [sys.executable, str(ROOT / "scripts/build_logos_verse_myeongri_cross_bridge_matrix_v1.py")]),
    ("showroom_slice", [sys.executable, str(ROOT / "scripts/build_logos_verse_4d_showroom_slice_v1.py")]),
    ("b2b_appendix", [sys.executable, str(ROOT / "scripts/build_logos_b2b_verse_4d_appendix_v1.py")]),
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--matrix-top-n", type=int, default=10)
    ap.add_argument("--skip-cross-bridge", action="store_true")
    ap.add_argument("--skip-matrix", action="store_true")
    ap.add_argument("--skip-showroom", action="store_true")
    ap.add_argument("--skip-b2b", action="store_true")
    args = ap.parse_args()

    for name, cmd in _STEPS:
        if name == "cross_bridge" and args.skip_cross_bridge:
            continue
        if name == "cross_bridge_matrix" and args.skip_matrix:
            continue
        if name == "showroom_slice" and args.skip_showroom:
            continue
        if name == "b2b_appendix" and args.skip_b2b:
            continue
        run_cmd = list(cmd)
        if name == "cross_bridge_matrix":
            run_cmd.extend(["--top-n", str(args.matrix_top_n)])
        print(f"[showroom-b2b-chain] {name}", flush=True)
        rc = subprocess.run(run_cmd, cwd=str(ROOT)).returncode
        if rc != 0:
            print(f"[showroom-b2b-chain] failed {name} exit={rc}", flush=True)
            return rc
    print("[showroom-b2b-chain] done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
