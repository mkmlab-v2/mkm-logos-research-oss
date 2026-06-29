"""Operator panel policy observe (unlabeled corpus)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JSONL = ROOT / "data/wtt/examples/wtt_operator_panel_sessions_v1.example.jsonl"
SCRIPT = ROOT / "scripts/observe_wtt_operator_panel_policy_v1.py"


def test_observe_operator_panel_exits_zero(tmp_path: Path) -> None:
    if not JSONL.is_file():
        import pytest

        pytest.skip("operator panel example jsonl missing")
    out = tmp_path / "observe.json"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--jsonl", str(JSONL), "--out", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "wtt_operator_panel_policy_observe_v1"
    assert doc.get("not_eligible_for_send") is True
    assert doc["baseline"]["session_count"] == 30
