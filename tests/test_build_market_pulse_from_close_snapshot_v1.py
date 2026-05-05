from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
import pytest


_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "build_market_pulse_from_close_snapshot_v1.py"
_TEXT_FIXTURE = _ROOT / "tests" / "fixtures" / "market_close_snapshot_kr_20260504.txt"


def test_build_market_pulse_from_text_snapshot(tmp_path: Path) -> None:
    out = tmp_path / "market_pulse.json"
    cmd = [
        sys.executable,
        str(_SCRIPT),
        "--input-text",
        str(_TEXT_FIXTURE),
        "--out",
        str(out),
        "--updated-at-utc",
        "2026-05-04T09:10:00Z",
    ]
    proc = subprocess.run(cmd, cwd=str(_ROOT), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "market_pulse_v1"
    assert doc["advance_decline_ratio"] == pytest.approx(392 / 476, rel=1e-4)
    assert doc["foreign_net_buy_krw_eok"] == 29308.0
    assert doc["institution_net_buy_krw_eok"] == 20098.0
    assert 0.0 <= doc["theme_leadership_score"] <= 1.0

