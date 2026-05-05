from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_sasang_daily_regime_backtest_smoke() -> None:
    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_sasang_daily_indicator_mapping_v1.py"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr

    cp2 = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_sasang_daily_regime_backtest_v1.py"),
            "--years",
            "3",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp2.returncode == 0, cp2.stderr

    report = ROOT / "docs" / "final" / "artifacts" / "sasang_daily_regime_backtest_v1_latest.json"
    doc = json.loads(report.read_text(encoding="utf-8"))
    assert doc.get("schema") == "sasang_daily_regime_backtest_v1"

