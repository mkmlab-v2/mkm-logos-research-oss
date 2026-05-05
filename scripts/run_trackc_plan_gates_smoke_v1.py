#!/usr/bin/env python3
"""Track C business-plan aligned smoke: orchestrator bundle verify + orchestrator pytest subset."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=None)
    args = ap.parse_args()
    root = (
        args.workspace_root.resolve()
        if args.workspace_root
        else Path(__file__).resolve().parents[1]
    )

    verify = root / "scripts" / "verify_mkm_orchestrator_bundle_v1.py"
    r1 = subprocess.run(
        [sys.executable, str(verify), "--workspace-root", str(root)],
        cwd=str(root),
        timeout=120,
    )
    if r1.returncode != 0:
        return r1.returncode

    tests = [
        "tests/test_mkm_orchestrator_queue_v1.py",
        "tests/test_mkm_orchestrator_telegram_v1.py",
        "tests/test_mkm_orchestrator_poll_smoke_v1.py",
        "tests/test_mkm_orchestrator_bundle_verify_v1.py",
        "tests/test_apply_trackc_plan_bridge_v1.py",
    ]
    cmd = [sys.executable, "-m", "pytest", "-q", *[str(root / t) for t in tests]]
    r2 = subprocess.run(cmd, cwd=str(root), timeout=600)
    return int(r2.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
