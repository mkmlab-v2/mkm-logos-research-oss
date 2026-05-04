from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "evaluate_btc_loop_interval_matrix_v1.py"
_CSV = _ROOT / "tests" / "fixtures" / "btc_close_series_sample_v1.csv"


def test_evaluate_btc_loop_interval_matrix_from_csv(tmp_path: Path) -> None:
    out = tmp_path / "loop_matrix.json"
    cmd = [
        sys.executable,
        str(_SCRIPT),
        "--input-csv",
        str(_CSV),
        "--intervals",
        "1",
        "--out",
        str(out),
    ]
    proc = subprocess.run(cmd, cwd=str(_ROOT), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "btc_loop_interval_matrix_v1"
    assert doc["recommended"]["best_loop_hours"] == 1
    assert len(doc["results"]) == 1
    row = doc["results"][0]
    assert "train_score" in row
    assert "test_score" in row
    assert "stability" in row

