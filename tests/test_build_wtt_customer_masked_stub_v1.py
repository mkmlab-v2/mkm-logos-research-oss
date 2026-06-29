"""Customer-masked WTT stub template builder."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts/build_wtt_customer_masked_stub_v1.py"


def test_build_20_stub_sessions(tmp_path: Path) -> None:
    out = tmp_path / "stub.jsonl"
    proc = subprocess.run(
        [sys.executable, str(BUILD), "--out-jsonl", str(out), "--sessions", "20"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    lines = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 20
    row = json.loads(lines[0])
    assert "synthetic_stub" in row["labels"]
    assert "synthetic_spicy" not in row["labels"]
    assert row["customer_provided"] is False
