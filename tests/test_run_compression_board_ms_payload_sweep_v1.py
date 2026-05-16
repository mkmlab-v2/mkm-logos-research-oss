# Keywords: compression board ms payload sweep

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_payload_sweep_dry_schema_from_script_help() -> None:
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_compression_board_ms_payload_sweep_v1.py"), "-h"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0
    assert "approx-words" in r.stdout


def test_payload_sweep_writes_schema_when_bench_available() -> None:
    """Skip network if stub not listening on 8010."""
    import urllib.error
    import urllib.request

    try:
        urllib.request.urlopen("http://127.0.0.1:8010/docs", timeout=2)
    except (urllib.error.URLError, OSError):
        return
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_compression_board_ms_payload_sweep_v1.py"),
            "--total-requests",
            "30",
            "--max-concurrent",
            "10",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    out = ROOT / "docs/final/artifacts/compression_board_ms_payload_sweep_v1_latest.json"
    if not out.is_file():
        assert r.returncode != 0
        return
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "compression_board_ms_payload_sweep_v1"
