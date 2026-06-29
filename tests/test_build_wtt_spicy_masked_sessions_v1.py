"""WTT spicy synthetic session corpus builder."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/wtt/examples/wtt_spicy_masked_sessions_v1.example.jsonl"
BUILD = ROOT / "scripts/build_wtt_spicy_masked_sessions_v1.py"


def test_build_writes_25_sessions(tmp_path: Path) -> None:
    out = tmp_path / "sessions.jsonl"
    proc = subprocess.run(
        [sys.executable, str(BUILD), "--out-jsonl", str(out), "--sessions", "25"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    lines = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 25
    row = json.loads(lines[0])
    assert row["synthetic_spicy"] is True
    assert "masked" in row["labels"]
    assert row["customer_provided"] is False
    assert len(row["turns"]) >= 1


def test_committed_example_exists_and_masked() -> None:
    if not OUT.is_file():
        subprocess.run(
            [sys.executable, str(BUILD), "--out-jsonl", str(OUT)],
            cwd=str(ROOT),
            check=True,
        )
    lines = [ln for ln in OUT.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) >= 20
    for line in lines:
        row = json.loads(line)
        assert "session_id" in row
        assert any(t.get("role") == "user" for t in row["turns"])
