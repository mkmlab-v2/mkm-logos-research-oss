"""B-track polar hypo v2 smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEXICON = ROOT / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41658_rows_latest.json"
OUT = ROOT / "reports/polar_coord_compression_hypo_v2_latest.json"


def test_polar_v2_runs() -> None:
    if not LEXICON.is_file():
        import pytest

        pytest.skip("41658 lexicon missing")
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_polar_coord_compression_hypo_v2.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc.get("schema") == "polar_coord_compression_hypo_v2"
