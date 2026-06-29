"""Smoke: DR vs T0 question matrix builder."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_dr_vs_t0_matrix_smoke() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/build_cheonyucho_dr_vs_t0_question_matrix_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    out = ROOT / "reports/constitution/btrack_pilot/cheonyucho_dr_vs_t0_question_matrix_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "cheonyucho_dr_vs_t0_question_matrix_v1"
    assert doc["counts"]["closable_dr"] >= 5
    assert doc["counts"]["t0_blocked"] >= 3
    assert doc["primary_hanja_chunk_count"] == 0
    t0_ids = {q["id"] for q in doc["requires_t0_or_human_paste"]}
    assert "Q-T0-primary-hanja" in t0_ids
