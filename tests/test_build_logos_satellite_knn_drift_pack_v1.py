"""Satellite kNN drift pack (apocrypha + DSS paths)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_logos_satellite_knn_drift_pack_v1.py"
CANON = ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_single_anchor_v1_latest.jsonl"
MEDOIDS = ROOT / "docs/final/artifacts/logos_verse_4d_single_anchor_medoids_v1_latest.json"
APO = ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_apocrypha_lane_v1_latest.jsonl"
DSS_LANE = ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_dss_lane_v1_latest.jsonl"


@pytest.mark.skipif(
    not CANON.is_file() or not MEDOIDS.is_file() or not APO.is_file(),
    reason="canon/medoids/apocrypha lane missing",
)
def test_knn_drift_pack_smoke(tmp_path: Path) -> None:
    if not DSS_LANE.is_file():
        subprocess.run(
            [sys.executable, str(ROOT / "scripts/build_logos_dss_satellite_lane_v1.py")],
            cwd=str(ROOT),
            check=True,
        )
    out = tmp_path / "pack.json"
    rc = subprocess.run(
        [sys.executable, str(SCRIPT), "--output-pack", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 0, rc.stderr or rc.stdout
    pack = json.loads(out.read_text(encoding="utf-8"))
    assert pack["schema"] == "logos_satellite_knn_drift_pack_v1"
    assert pack["satellites"]["apocrypha"]["vectors_used"] > 0
    assert pack["satellites"]["dss"]["vectors_used"] > 0
