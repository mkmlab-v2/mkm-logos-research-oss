"""Satellite dev chain smoke (apocrypha bootstrap + kNN)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHAIN = ROOT / "scripts/run_logos_satellite_dev_chain_v1.py"
CORPUS = ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_single_anchor_v1_latest.jsonl"
APO_OUT = ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_apocrypha_lane_v1_latest.jsonl"
KNN_OUT = ROOT / "docs/final/artifacts/logos_satellite_knn_drift_v1_latest.json"


@pytest.mark.skipif(not CORPUS.is_file(), reason="single-anchor corpus missing")
def test_satellite_dev_chain_smoke() -> None:
    rc = subprocess.run(
        [
            sys.executable,
            str(CHAIN),
            "--force-apocrypha-bootstrap",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 0, rc.stderr or rc.stdout
    assert APO_OUT.is_file()
    assert KNN_OUT.is_file()
    knn = json.loads(KNN_OUT.read_text(encoding="utf-8"))
    assert knn["satellite"]["row_count"] > 0
