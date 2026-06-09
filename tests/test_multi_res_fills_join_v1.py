"""Integration tests for multi_res_fills_join_v1 ([HYPO])."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JOIN = ROOT / "scripts/multi_res_fills_join_v1.py"
FIXTURE = ROOT / "tests/fixtures/multi_res_trades_smoke_v1.json"
OUT = ROOT / "reports/tmp_multi_res_fills_index_test.json"


def test_join_cli_writes_index(tmp_path: Path) -> None:
    out = tmp_path / "index.json"
    proc = subprocess.run(
        [sys.executable, str(JOIN), "--trades-json", str(FIXTURE), "--out", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["meta"]["n_fill_rows"] == 3
    assert "daily_by_utc_date" in doc["low_res"]


def test_coordinate_map_links_daily_to_rows() -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from multi_res_fills_join_v1 import build_multi_res_index

    doc = build_multi_res_index(trades_path=FIXTURE, generated_at_utc="2026-06-09T00:00:00Z")
    jan10 = next(c for c in doc["coordinate_map"] if c["utc_date"] == "2026-01-10")
    assert len(jan10["high_res_row_ids"]) == 2
