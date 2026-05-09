#!/usr/bin/env python3
"""
Probe optional deps for strict audio gate evaluation (LUFS via pyloudnorm).

Exit 0: informational JSON on stdout.
Exit 1: only with --require-all when LUFS chain (numpy + pyloudnorm) is unavailable.

Use before running `evaluate_audio_gate.py` without --waive-lufs in local/CI strict mode.
"""

from __future__ import annotations

import argparse
import json
import sys


def main() -> int:
    ap = argparse.ArgumentParser(description="Check numpy/pyloudnorm for audio gate LUFS.")
    ap.add_argument(
        "--require-all",
        action="store_true",
        help="Exit 1 if integrated LUFS measurement cannot run (missing numpy or pyloudnorm).",
    )
    args = ap.parse_args()

    has_np = False
    has_pln = False
    try:
        import numpy  # noqa: F401

        has_np = True
    except ImportError:
        pass
    try:
        import pyloudnorm  # noqa: F401

        has_pln = True
    except ImportError:
        pass

    lufs_ok = bool(has_np and has_pln)
    out = {
        "numpy": has_np,
        "pyloudnorm": has_pln,
        "lufs_measurement_available": lufs_ok,
    }
    print(json.dumps(out, indent=2))
    if args.require_all and not lufs_ok:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
