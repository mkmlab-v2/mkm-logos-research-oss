# Keywords: magic_orb, post_llm_gate, four_slot

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSIGHT = ROOT / "docs/final/artifacts/magic_orb_question_insight_v1_latest.json"


def test_post_llm_gate_cli() -> None:
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_magic_orb_four_slot_post_llm_gate_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    out = json.loads(r.stdout)
    assert out["ok"] is True
    gate = ROOT / "reports/magic_orb_four_slot_post_llm_gate_v1_latest.json"
    assert gate.is_file()
