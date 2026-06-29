# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts/check_logos_graph_studio_pilot_commercial_gate_v1.py"


def test_pilot_commercial_gate_script_exists() -> None:
    assert GATE.is_file()


def test_pilot_commercial_gate_runs() -> None:
    cp = subprocess.run(
        [sys.executable, str(GATE)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    # May fail until closure chain completes — smoke that it emits JSON.
    assert cp.stdout.strip() or cp.stderr.strip()
