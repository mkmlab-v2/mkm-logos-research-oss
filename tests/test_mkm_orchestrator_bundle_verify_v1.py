"""verify_mkm_orchestrator_bundle_v1.py exits 0 in-repo."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_bundle_verify_exits_zero():
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "verify_mkm_orchestrator_bundle_v1.py"
    r = subprocess.run(
        [sys.executable, str(script), "--workspace-root", str(root)],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr + r.stdout
