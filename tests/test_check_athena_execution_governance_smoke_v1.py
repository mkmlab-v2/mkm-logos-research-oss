# -*- coding: utf-8 -*-
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]


def test_execution_governance_smoke_exit_zero():
    proc = subprocess.run(
        [sys.executable, str(_REPO / "scripts" / "check_athena_execution_governance_smoke_v1.py"), "--quiet"],
        cwd=str(_REPO),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
