#!/usr/bin/env python3
"""Legacy alias — delegates to run_ko_shorts_full_chain_v1 --quick [HYPO]."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    cmd = [sys.executable, str(ROOT / "scripts/run_ko_shorts_full_chain_v1.py"), "--quick"]
    cmd.extend(sys.argv[1:])
    return subprocess.call(cmd, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
