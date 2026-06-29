"""P8 Lemma-339 full-cover spike chain (B-track, HYPO)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bridge_v1_latest.json"
SPIKE = ROOT / "docs/final/artifacts/logos_lemma_anchor_spike_v1_latest.json"
DRIFT = ROOT / "docs/final/artifacts/logos_lemma_spike_drift_check_v1_latest.json"


@pytest.fixture(scope="module")
def lemma_339_chain() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_logos_lemma_60_chain_v1.py",
            "--target",
            "339",
            "--skip-pytest",
            "--skip-baseline",
            "--skip-bridge-refresh",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_lemma_hit_anchors_full_cover(lemma_339_chain: None) -> None:
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    anchor_count = int(bridge.get("anchor_count") or bridge["summary"]["anchor_count"])
    assert bridge["summary"]["lemma_hit_anchors"] >= 339
    assert bridge["summary"]["lemma_hit_anchors"] == anchor_count


def test_p8_spike_path_id(lemma_339_chain: None) -> None:
    doc = json.loads(SPIKE.read_text(encoding="utf-8"))
    if int(doc.get("target_lemma_hit_anchors") or 0) == 339:
        assert doc["path_id"] == "lemma_spike_p8_v2"


def test_p8_no_missing_lemma_anchors(lemma_339_chain: None) -> None:
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    missing = [r for r in bridge["per_anchor"] if int(r.get("lemma_edge_count") or 0) == 0]
    assert missing == []


def test_p8_drift_no_regression_flags(lemma_339_chain: None) -> None:
    if not DRIFT.is_file():
        pytest.skip("drift check artifact missing")
    doc = json.loads(DRIFT.read_text(encoding="utf-8"))
    assert doc.get("pass") is True
    assert doc.get("drift_flags") == []
