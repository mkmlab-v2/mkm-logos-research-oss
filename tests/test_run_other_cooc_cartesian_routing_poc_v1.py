"""B-track cooc cartesian routing PoC smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEXICON = ROOT / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41658_rows_latest.json"
OUT = ROOT / "reports/other_cooc_cartesian_routing_poc_v1_latest.json"


def test_cooc_routing_poc_runs() -> None:
    if not LEXICON.is_file():
        import pytest

        pytest.skip("41658 lexicon missing")
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_other_cooc_cartesian_routing_poc_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc.get("schema") == "other_cooc_cartesian_routing_poc_v1"
    assert "threshold_sweep" in doc
    assert doc["affinity_mean"]["delta"] > 0
