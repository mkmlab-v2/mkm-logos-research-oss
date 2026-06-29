"""Smoke test for G2-b lexicon_dense long-sequence wirebench."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/g2b_lexicon_dense_long_sequence_wirebench_v1_latest.json"


def test_g2b_long_sequence_wirebench_builds() -> None:
    jsonl = ROOT / "docs/final/artifacts/sasang_routing_sidecar_corpus_31k_v1.jsonl"
    if not jsonl.is_file():
        return
    cp = subprocess.run(
        [sys.executable, "scripts/run_g2b_lexicon_dense_long_sequence_wirebench_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "g2b_lexicon_dense_long_sequence_wirebench_v1"
    assert doc["send_gate"] == "HOLD"
    assert doc["track_a_blocked"] is True
    assert doc["candidate_line_count"] >= 1
    assert doc["candidate_avg_byte_saving_vs_packet"] is not None
