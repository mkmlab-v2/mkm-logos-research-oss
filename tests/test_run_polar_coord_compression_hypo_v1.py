"""B-track polar coord compression hypo — schema smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_polar_coord_compression_hypo_v1.py"
LEXICON = ROOT / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41658_rows_latest.json"
OUT = ROOT / "reports/polar_coord_compression_hypo_v1_latest.json"


def test_polar_coord_hypo_runs_and_schema() -> None:
    if not LEXICON.is_file():
        import pytest

        pytest.skip("41658 lexicon not present locally")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--out", str(OUT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc.get("schema") == "polar_coord_compression_hypo_v1"
    assert doc.get("hypothesis_tier") == "B"
    assert doc.get("research_only") is True
    assert "separation_cartesian" in doc
    assert "separation_polar" in doc
    assert isinstance(doc.get("polar_separation_improved_vs_cartesian"), bool)
    counts = doc.get("atom_counts") or {}
    assert counts.get("other", 0) > 0
