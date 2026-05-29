from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_logos_track_l_l0_readiness_v1.py"


def test_l0_readiness_exit_and_shape(tmp_path):
    out = tmp_path / "l0.json"
    proc = subprocess.run(
        [sys.executable, str(RUNNER), "-o", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    doc = json.loads(proc.stdout)
    assert doc["schema"] == "logos_track_l_l0_readiness_v1"
    assert doc["gate_level"] == "L0"
    assert "checks" in doc
    assert doc["track_wall"]["a_track_live_trigger"] is False
    if proc.returncode == 0:
        assert doc["l0_ok"] is True
        ids = {c["id"] for c in doc["checks"]}
        assert "resolver_john_19_34" in ids
        assert "corpus_row_jhn_19_34" in ids
