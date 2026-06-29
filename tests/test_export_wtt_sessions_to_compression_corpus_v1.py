"""WTT -> compression bridge export."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPORT = ROOT / "scripts/export_wtt_sessions_to_compression_corpus_v1.py"
SRC = ROOT / "data/wtt/intake/wtt-customer-live-v1.jsonl"


def test_export_bridge(tmp_path: Path) -> None:
    if not SRC.is_file():
        import pytest

        pytest.skip("wtt-customer-live-v1 intake missing")
    out = tmp_path / "bridge.jsonl"
    meta = tmp_path / "meta.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(EXPORT),
            "--jsonl",
            str(SRC),
            "--out",
            str(out),
            "--meta-out",
            str(meta),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    lines = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 30
    row = json.loads(lines[0])
    assert "text" in row
    assert row.get("wtt_session_id")
    meta_doc = json.loads(meta.read_text(encoding="utf-8"))
    assert meta_doc.get("row_count") == 30
    assert meta_doc.get("send_gate") == "HOLD"
