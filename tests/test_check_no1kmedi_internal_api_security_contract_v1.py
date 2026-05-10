"""Regression: no1kmedi internal API security contract checker exits 0 on repo."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_checker_passes_on_workspace_root() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "check_no1kmedi_internal_api_security_contract_v1.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--workspace-root", str(root)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
