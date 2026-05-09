"""Smoke test for sync_cursor_trade_history_latest_24h SSOT output file."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_sync_writes_cursor_trade_history_ssot_file(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parent.parent
    script = root / "scripts" / "sync_cursor_trade_history_latest_24h.py"
    source_dir = tmp_path / "source"
    dest_dir = tmp_path / "dest"
    source_dir.mkdir(parents=True, exist_ok=True)

    # Minimal required inputs.
    (source_dir / "trades_control.json").write_text("[]\n", encoding="utf-8")
    (source_dir / "trades_treatment.json").write_text("[]\n", encoding="utf-8")

    cp = subprocess.run(
        [
            sys.executable,
            str(script),
            "--source-dir",
            str(source_dir),
            "--dest-dir",
            str(dest_dir),
            "--hours",
            "24",
        ],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout

    all_latest_path = dest_dir / "all_trades_latest_24h.json"
    ssot_latest_path = dest_dir / "cursor_trade_history_latest_24h.json"
    assert all_latest_path.is_file()
    assert ssot_latest_path.is_file()

    all_latest = json.loads(all_latest_path.read_text(encoding="utf-8"))
    ssot_latest = json.loads(ssot_latest_path.read_text(encoding="utf-8"))
    assert all_latest == ssot_latest
    assert all_latest.get("schema") == "cursor_trade_history_latest_window_v1"
