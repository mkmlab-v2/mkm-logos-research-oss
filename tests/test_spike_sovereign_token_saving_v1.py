# -*- coding: utf-8 -*-
"""Smoke: spike_sovereign_token_saving_v1 subprocess exit 0 + schema."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_spike_sovereign_token_saving_stdout_schema() -> None:
    script = ROOT / "scripts" / "spike_sovereign_token_saving.py"
    cp = subprocess.run(
        [
            sys.executable,
            str(script),
            "--samples",
            "20",
            "--seed",
            "1",
            "--stdout-only",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(cp.stdout.strip())
    assert doc.get("schema") == "spike_sovereign_token_saving_v1"
    assert doc.get("hypothesis_tier") == "B"
    assert doc.get("boundary_ack") is True
    for k in ("baseline_token_count", "sovereign_token_count", "delta_saving_ratio", "tokenizer"):
        assert k in doc
