#!/usr/bin/env python3
"""Frontline-compat alias → ``run_dss_token_pilot.py`` (B-track rebuild).

Legacy name from 2026-03-27 unified frontline cycle. Delegates to pilot manifest.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    manifest = "dss_pilot_manifest_tf4.json"
    if "--manifest" in sys.argv:
        idx = sys.argv.index("--manifest")
        if idx + 1 < len(sys.argv):
            legacy = sys.argv[idx + 1]
            if legacy == "dss_ci_manifest_tf4.json":
                sys.argv[idx + 1] = manifest

    cmd = [sys.executable, str(ROOT / "run_dss_token_pilot.py"), *sys.argv[1:]]
    return subprocess.call(cmd, cwd=str(ROOT))


if __name__ == "__main__":
    raise SystemExit(main())
