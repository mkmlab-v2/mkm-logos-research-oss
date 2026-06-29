from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts/build_sasang_curated_joint_ingest_gate_v1.py"


def test_ingest_gate_input_missing_hold() -> None:
    r = subprocess.run(
        [sys.executable, str(_SCRIPT)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    gate_path = _ROOT / "docs/final/artifacts/sasang_curated_joint_ingest_gate_v1_latest.json"
    doc = json.loads(gate_path.read_text(encoding="utf-8-sig"))
    assert doc["gate_ok"] is True
    if not (_ROOT / "data/myeongni/curated_saju_joint_v1.jsonl").is_file():
        assert doc["ingest_status"] == "input_missing_hold"
