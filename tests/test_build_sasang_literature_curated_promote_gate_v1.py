from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_GATE_SCRIPT = _ROOT / "scripts/build_sasang_literature_curated_promote_gate_v1.py"


def test_promote_gate_csv_missing_hold(tmp_path: Path) -> None:
    out = tmp_path / "gate.json"
    r = subprocess.run(
        [sys.executable, str(_GATE_SCRIPT), "--out", str(out)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["gate_ok"] is True
    if not (_ROOT / "data/myeongni/sasang_saju_joint_review_queue_v1.csv").is_file():
        assert doc["promote_status"] == "csv_missing_hold"
    else:
        assert doc["promote_status"] in ("idle_no_curator_rows", "ready_to_apply", "applied")
