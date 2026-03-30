from __future__ import annotations

import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RUNNER = PROJECT_ROOT / "ops" / "v2" / "graph" / "runner.py"


def main() -> int:
    if not RUNNER.exists():
        print(f"runner.py not found: {RUNNER}", file=sys.stderr)
        return 2

    proc = subprocess.run(
        [sys.executable, str(RUNNER), "--mode", "shadow"],
        cwd=str(PROJECT_ROOT),
    )
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
