"""Tests for massive Universal Root pair generator."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "scripts/bench/generate_massive_universal_root_pairs_v1.py"


def test_generate_massive_pairs_smoke(tmp_path: Path) -> None:
    out = tmp_path / "bench_120.json"
    report = tmp_path / "report.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(GEN),
            "--target",
            "120",
            "--seed",
            "7",
            "--out",
            str(out),
            "--report",
            str(report),
            "--skip-ip-governance",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["pair_count"] == 120
    assert doc["schema"] == "nsm_41k_lexicon_crosswalk_massive_v1"
    assert doc["generation"]["canonical_overlap_rate"] == 0.0
    rep = json.loads(report.read_text(encoding="utf-8"))
    assert rep["ok"] is True
    assert rep["pair_count"] == 120
    en_b0 = sum(1 for s in doc["samples"] if s.get("source_note") == "massive_gen_english_surface_b0")
    assert en_b0 >= 1
