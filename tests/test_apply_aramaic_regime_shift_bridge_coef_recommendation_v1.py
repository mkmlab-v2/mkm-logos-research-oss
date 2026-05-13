"""Smoke: apply_aramaic_regime_shift_bridge_coef_recommendation_v1 CLI writes recommendation JSON."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "apply_aramaic_regime_shift_bridge_coef_recommendation_v1.py"


def test_apply_bridge_coef_recommendation_cli_smoke(tmp_path: Path) -> None:
    out = tmp_path / "bridge.json"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--output-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "aramaic_regime_shift_bridge_coef_recommendation_v1"
    assert "aramaic_to_hebrew" in (doc.get("recommended") or {}).get("bridge_lang_coef", {})
