"""Multi-Orbit B-track chain smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHAIN = ROOT / "scripts/run_logos_multi_orbit_chain_v1.py"
PACK = ROOT / "docs/final/artifacts/logos_multi_orbit_showroom_pack_v1_latest.json"
METRICS = ROOT / "docs/final/artifacts/logos_satellite_drift_metrics_v1_latest.json"
POLICY = ROOT / "data/logos/logos_gap_mt_only_policy_v1.jsonl"
CORPUS = ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_single_anchor_v1_latest.jsonl"


@pytest.mark.skipif(
    not POLICY.is_file() or not CORPUS.is_file(),
    reason="policy or single-anchor corpus missing",
)
def test_run_multi_orbit_chain_smoke() -> None:
    rc = subprocess.run(
        [sys.executable, str(CHAIN)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 0, rc.stderr or rc.stdout
    assert PACK.is_file()
    pack = json.loads(PACK.read_text(encoding="utf-8"))
    assert pack["schema"] == "logos_multi_orbit_showroom_pack_v1"
    assert pack["track_wall"]["ready_for_external_send"] is False
    assert METRICS.is_file()
    metrics = json.loads(METRICS.read_text(encoding="utf-8"))
    assert metrics["canon_population"]["count"] > 0
