#!/usr/bin/env python3
"""One-shot: build web_ops_regime_gate from Nebius/Azure probe JSON + check policy."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "scripts/build_web_ops_regime_gate_v1.py"
CHECK = ROOT / "scripts/check_web_ops_regime_gate_v1.py"
DEFAULT_OUT = ROOT / "reports/web_ops_regime_gate_v1_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-azure", action="store_true")
    ap.add_argument("--require-gate-pass", action="store_true", default=True)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    build_cmd = [sys.executable, str(BUILD), "--out", str(args.out)]
    if args.skip_azure:
        build_cmd.append("--skip-azure")
    r1 = subprocess.run(build_cmd, cwd=str(ROOT))
    if r1.returncode != 0:
        return r1.returncode

    check_cmd = [sys.executable, str(CHECK), "--in-json", str(args.out)]
    if args.require_gate_pass:
        check_cmd.append("--require-gate-pass")
    r2 = subprocess.run(check_cmd, cwd=str(ROOT))
    print(
        json.dumps(
            {"bundle": "web_ops_regime_portal_v1", "build_rc": r1.returncode, "check_rc": r2.returncode},
            ensure_ascii=False,
        )
    )
    return r2.returncode


if __name__ == "__main__":
    raise SystemExit(main())
