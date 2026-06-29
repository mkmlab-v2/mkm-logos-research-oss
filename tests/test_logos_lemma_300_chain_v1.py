"""P7 Lemma-300 spike chain (B-track, HYPO)."""

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
def lemma_300_chain() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_logos_lemma_60_chain_v1.py",
            "--target",
            "300",
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


def test_lemma_hit_anchors_at_least_three_hundred(lemma_300_chain: None) -> None:
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    assert bridge["summary"]["lemma_hit_anchors"] >= 300


def test_p7_spike_path_id(lemma_300_chain: None) -> None:
    doc = json.loads(SPIKE.read_text(encoding="utf-8"))
    if int(doc.get("target_lemma_hit_anchors") or 0) == 300:
        assert doc["path_id"] == "lemma_spike_p7_v1"


def test_p7_drift_no_regression_flags(lemma_300_chain: None) -> None:
    if not DRIFT.is_file():
        pytest.skip("drift check artifact missing")
    doc = json.loads(DRIFT.read_text(encoding="utf-8"))
    assert doc.get("pass") is True
    assert doc.get("drift_flags") == []
