# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.5, K:0.2, M:0.2}
# Balance: 92
# Purpose: Smoke test for prophecy panel coverage delta probe script
# Keywords: pytest, prophecy, probe
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_probe_script_runs_on_minimal_fixture(tmp_path: Path) -> None:
    ws = Path(__file__).resolve().parents[1]
    score = {
        "schema": "btrack_prophecy_score_v1",
        "neutral_bps": 10000.0,
        "rows": [
            {
                "instrument": "kospi",
                "eval_date": "2026-01-02",
                "predicted_direction": "bear",
                "actual_direction": "bull",
                "daily_return": 0.01,
            },
            {
                "instrument": "kospi",
                "eval_date": "2026-01-03",
                "predicted_direction": "bear",
                "actual_direction": "bear",
                "daily_return": -0.01,
            },
        ],
    }
    p_score = tmp_path / "score.json"
    p_score.write_text(json.dumps(score), encoding="utf-8")
    p_out = tmp_path / "out.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ws / "scripts" / "run_prophecy_panel_coverage_delta_probe_v1.py"),
            "--score-json",
            str(p_score),
            "--kospi-csv",
            str(ws / "research" / "market_data" / "kospi_daily_external_yf.csv"),
            "--output",
            str(p_out),
        ],
        cwd=str(ws),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(p_out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "prophecy_panel_coverage_delta_probe_v1"
    assert isinstance(doc.get("lanes"), list) and len(doc["lanes"]) >= 3
