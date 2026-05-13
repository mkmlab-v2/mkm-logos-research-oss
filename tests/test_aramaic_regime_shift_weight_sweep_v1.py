"""Smoke: run_aramaic_regime_shift_weight_sweep_v1 CLI writes sweep artifact."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_aramaic_regime_shift_weight_sweep_v1.py"


def test_aramaic_regime_shift_weight_sweep_cli_smoke(tmp_path: Path) -> None:
    out = tmp_path / "sweep.json"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--output-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "aramaic_regime_shift_weight_sweep_v1"
    assert isinstance(doc.get("candidates"), list)
