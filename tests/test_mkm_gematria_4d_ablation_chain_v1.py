"""K-track gematria 4D ablation chain — isolated from router/gold metrics."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/mkm_gematria_4d_ablation_chain_v1_latest.json"
ABLATION = ROOT / "docs/final/artifacts/gematria_4d_ablation_latest.json"


@pytest.fixture(scope="module")
def ablation_chain() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_mkm_gematria_4d_ablation_chain_v1.py",
            "--skip-pytest",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_ablation_chain_report(ablation_chain: None) -> None:
    doc = json.loads(OUT.read_text(encoding="utf-8-sig"))
    assert doc["chain_pass"] is True
    assert doc["source_track"] == "K"
    snap = doc.get("snapshot") or {}
    assert "router_hit_rate" not in snap
    assert "gold_required_all_pass" not in snap


def test_ablation_snapshot_fields(ablation_chain: None) -> None:
    doc = json.loads(ABLATION.read_text(encoding="utf-8-sig"))
    snap = doc["snapshot"]
    assert "score_with_4d" in snap
    assert "score_without_4d" in snap
    assert isinstance(snap["delta_with_minus_without"], (int, float))
    assert doc["policy_gate"]["allow_execution_trigger"] is False
