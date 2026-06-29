"""P3 Root Generator weekly runner smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
WEEKLY = REPO / "scripts/run_p3_root_generator_weekly_v1.py"
OUT = REPO / "reports/p3_root_generator_weekly_v1_latest.json"
BASELINE = REPO / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41658_rows_latest.json"


@pytest.mark.skipif(not BASELINE.is_file(), reason="41658 baseline export missing")
def test_weekly_runner_offline():
    r = subprocess.run(
        [sys.executable, str(WEEKLY), "--offline-shallow"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    assert OUT.is_file()
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc.get("ok") is True
    assert doc.get("extension", {}).get("decision") == "ADVANCE_EXTENSION_CANDIDATE"
