# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.7, K:0.3, M:0.5}
# Balance: 86
# Purpose: Smoke test threshold sweep artifact creation.
# Keywords: pytest, sweep, threshold, gate
from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "sweep_survivor_crash_falsification_thresholds_v1.py"


def test_threshold_sweep_writes_rows(tmp_path: Path) -> None:
    out = tmp_path / "sweep.json"
    proxy = ROOT / "docs" / "final" / "artifacts" / "btrack_survivor_crash_correlation_backtest_proxy_latest.json"
    real = ROOT / "docs" / "final" / "artifacts" / "btrack_survivor_crash_correlation_backtest_real_latest.json"
    proc = subprocess.run(
        [
            "py",
            str(SCRIPT),
            "--proxy-backtest-json",
            str(proxy),
            "--real-backtest-json",
            str(real),
            "--threshold-grid",
            "0.3,0.5",
            "--output",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "btrack_survivor_crash_falsification_threshold_sweep_v1"
    assert len(doc.get("rows") or []) == 2

