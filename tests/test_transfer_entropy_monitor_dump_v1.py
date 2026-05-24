"""transfer_entropy_market_regime_detector + monitor dump."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "core"))

from transfer_entropy_market_regime_detector import (  # noqa: E402
    TransferEntropyMarketRegimeDetector,
    compute_transfer_entropy_probe,
)


def test_compute_transfer_entropy_probe_positive() -> None:
    rng = np.random.default_rng(42)
    rets = rng.normal(0, 0.02, size=30)
    te = compute_transfer_entropy_probe(rets, None, lookback=20)
    assert 0.0 <= te <= 5.0


def test_detector_async_contract() -> None:
    rets = np.array([0.01, -0.02, 0.015, -0.01, 0.02, -0.005], dtype=float)

    async def _run() -> dict:
        det = TransferEntropyMarketRegimeDetector(lookback=5)
        return await det.detect_market_regime(rets, np.zeros_like(rets), [], __import__("datetime").datetime.utcnow())

    out = asyncio.run(_run())
    assert "transfer_entropy" in out
    assert out.get("implementation") == "btrack_probe_v1"
    assert out.get("regime", {}).get("regime_type")


def test_dump_monitor_snapshot_script(tmp_path: Path) -> None:
    import csv

    csv_path = tmp_path / "btc.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Date", "Close"])
        price = 100.0
        for i in range(30):
            w.writerow([f"2026-02-{i+1:02d}", f"{price:.4f}"])
            price *= 1.01 if i % 2 == 0 else 0.99
    out = tmp_path / "monitoring.json"
    script = ROOT / "scripts" / "dump_unified_trading_monitor_te_snapshot_v1.py"
    cp = subprocess.run(
        [
            sys.executable,
            str(script),
            "--btc-csv",
            str(csv_path),
            "--output",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "unified_trading_monitor_snapshot_v1"
    assert doc["regime_analysis"]["implementation"] == "btrack_probe_v1"
    assert isinstance(doc["transfer_entropy"], (int, float))
