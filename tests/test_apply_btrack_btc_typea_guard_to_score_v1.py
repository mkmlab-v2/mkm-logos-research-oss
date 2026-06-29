"""Tests for apply_btrack_btc_typea_guard_to_score_v1."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPLY = ROOT / "scripts" / "apply_btrack_btc_typea_guard_to_score_v1.py"


def test_apply_typea_guard_on_operational_score(tmp_path: Path) -> None:
    out = tmp_path / "shadow_score.json"
    summary = tmp_path / "summary.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(APPLY),
            "--out-json",
            str(out),
            "--summary-json",
            str(summary),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    rep = json.loads(summary.read_text(encoding="utf-8"))
    btc_rows = [r for r in doc["rows"] if str(r.get("instrument")).lower() == "btc"]
    assert len(btc_rows) >= 10
    assert rep["schema"] == "btrack_btc_typea_guard_apply_v1"
    assert "delta_hit_rate" in rep
