"""WTT spicy corpus FSM batch runner."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BATCH = ROOT / "scripts/run_wtt_spicy_corpus_fsm_batch_v1.py"
BUILD = ROOT / "scripts/build_wtt_spicy_masked_sessions_v1.py"


def test_fsm_batch_on_synthetic_corpus(tmp_path: Path) -> None:
    jsonl = tmp_path / "sessions.jsonl"
    out = tmp_path / "batch.json"
    subprocess.run(
        [sys.executable, str(BUILD), "--out-jsonl", str(jsonl)],
        cwd=str(ROOT),
        check=True,
    )
    proc = subprocess.run(
        [sys.executable, str(BATCH), "--jsonl", str(jsonl), "--out", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["session_count"] == 25
    assert report["fsm_state_counts"]
    assert len(report["sessions"]) == 25
