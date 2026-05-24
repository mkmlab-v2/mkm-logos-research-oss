"""export_btrack_transfer_entropy_snapshot_v1 — B-track TE export contract."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "export_btrack_transfer_entropy_snapshot_v1.py"


def test_export_te_from_nested_monitor_json(tmp_path: Path) -> None:
    src = tmp_path / "monitor.json"
    src.write_text(
        json.dumps({"regime_analysis": {"transfer_entropy": 2.75, "regime": {"regime_type": "X"}}}),
        encoding="utf-8",
    )
    out = tmp_path / "te.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--source-json",
            str(src),
            "--no-scan-candidates",
            "--output",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "btrack_transfer_entropy_snapshot_v1"
    assert doc["method"] == "monitor_json"
    assert doc["transfer_entropy"] == 2.75


def test_export_te_proxy_from_btc_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "btc.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Date", "Close"])
        price = 100.0
        for i in range(25):
            w.writerow([f"2026-01-{i+1:02d}", f"{price:.2f}"])
            price *= 1.01 if i % 2 == 0 else 0.99
    out = tmp_path / "te.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--btc-csv",
            str(csv_path),
            "--no-scan-candidates",
            "--output",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["method"] in ("te_proxy_btc_returns_v1", "transfer_entropy_detector_btrack_probe_v1")
    assert isinstance(doc["transfer_entropy"], (int, float))
