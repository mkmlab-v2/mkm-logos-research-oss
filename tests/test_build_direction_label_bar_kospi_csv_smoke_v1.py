# Keywords: build_direction_label_bar_jsonl_from_ohlcv_v1, KOSPI
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_direction_label_bar_jsonl_from_ohlcv_v1.py"
KOSPI_CSV = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"


@pytest.mark.skipif(not KOSPI_CSV.is_file(), reason="kospi_daily_external_yf.csv not present")
def test_kospi_ohlcv_build_smoke(tmp_path: Path):
    out = tmp_path / "kospi_1d.jsonl"
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--csv",
            str(KOSPI_CSV),
            "--instrument-id",
            "KOSPI",
            "--horizon",
            "1d",
            "--neutral-bps",
            "8",
            "--output",
            str(out),
            "--max-rows",
            "5",
            "--validate-labels",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    lines = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert 1 <= len(lines) <= 5
    assert "direction_label_bar_v1" in lines[0]
