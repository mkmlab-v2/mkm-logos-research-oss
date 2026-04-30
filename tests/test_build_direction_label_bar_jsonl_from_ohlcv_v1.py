# Keywords: direction_label_bar_v1, OHLCV
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_direction_label_bar_jsonl_from_ohlcv_v1.py"


def test_build_direction_label_bar_jsonl_smoke(tmp_path: Path):
    csv_path = tmp_path / "mini.csv"
    csv_path.write_text(
        "Date,Open,High,Low,Close,Volume\n"
        "2024-01-02,1,1,1,100.0,1\n"
        "2024-01-03,1,1,1,102.0,1\n"
        "2024-01-04,1,1,1,101.0,1\n",
        encoding="utf-8",
    )
    out = tmp_path / "labels.jsonl"
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--csv",
            str(csv_path),
            "--instrument-id",
            "TESTIDX",
            "--horizon",
            "1d",
            "--neutral-bps",
            "8",
            "--output",
            str(out),
            "--validate-labels",
            "--max-rows",
            "10",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert out.is_file()
    lines = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 2
    assert "direction_label_bar_v1" in lines[0]
