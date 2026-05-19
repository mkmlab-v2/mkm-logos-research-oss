import subprocess
import sys
from pathlib import Path


def test_chunk_script_rejects_window_over_binance_cap() -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "build_trading_fee_metrics_chunked_v1.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--days", "1", "--chunk-hours", "200"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 2
    combined = (proc.stdout + proc.stderr).lower()
    assert "binance" in combined or "limit" in combined or "chunk" in combined
