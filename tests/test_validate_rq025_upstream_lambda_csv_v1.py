from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATE = ROOT / "scripts/validate_rq025_upstream_lambda_csv_v1.py"
PROXY = ROOT / "reports/backups/sgp_history_master_real_pre_cert_20260611T074914Z.csv"


def test_validate_upstream_csv_ok(tmp_path: Path) -> None:
    if not PROXY.is_file():
        import pytest

        pytest.skip("proxy backup missing")
    proc = subprocess.run(
        [sys.executable, str(VALIDATE), str(PROXY)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_validate_upstream_csv_fail(tmp_path: Path) -> None:
    bad = tmp_path / "bad.csv"
    with bad.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "foo"])
        w.writerow(["2026-01-01", "1"])
    proc = subprocess.run(
        [sys.executable, str(VALIDATE), str(bad)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
