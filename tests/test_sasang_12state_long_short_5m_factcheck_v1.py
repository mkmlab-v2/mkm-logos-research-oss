from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def test_sasang_12state_long_short_5m_factcheck_smoke(tmp_path: Path) -> None:
    t = pd.date_range("2025-01-01", periods=1200, freq="5min", tz="UTC")
    base = pd.Series(range(len(t)), dtype=float)
    close = 50000.0 + (base * 0.8) + (base % 30 - 15) * 2.0
    df = pd.DataFrame(
        {
            "open_time": t.astype(str),
            "open": close.shift(1).fillna(close.iloc[0]),
            "high": close + 20.0,
            "low": close - 20.0,
            "close": close,
            "volume": 10.0 + (base % 50),
        }
    )
    input_csv = tmp_path / "btc_5m_fixture.csv"
    out_json = tmp_path / "report.json"
    df.to_csv(input_csv, index=False)

    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_sasang_12state_long_short_5m_factcheck_v1.py"),
            "--input-csv",
            str(input_csv),
            "--output-json",
            str(out_json),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc.get("schema") == "sasang_12state_long_short_5m_factcheck_v1"
    res = doc.get("results")
    assert isinstance(res, list) and len(res) == 2

