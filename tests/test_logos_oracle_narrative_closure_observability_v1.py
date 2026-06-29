"""Oracle narrative + closure observability chain."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/final/artifacts/logos_oracle_narrative_closure_observability_v1_latest.json"


@pytest.fixture(scope="module")
def observability_chain() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_logos_oracle_narrative_closure_observability_chain_v1.py",
            "--skip-pytest",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_observability_schema(observability_chain: None) -> None:
    doc = json.loads(OUT.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "logos_oracle_narrative_closure_observability_v1"
    assert doc["observation_pass"] is True
    assert doc["send_gate"] == "HOLD"
    snap = doc.get("snapshot") or {}
    assert snap.get("resonance_cap") is not None
    assert snap.get("read_only") is True


def test_observability_includes_narrative_and_tier2(observability_chain: None) -> None:
    doc = json.loads(OUT.read_text(encoding="utf-8-sig"))
    ids = {row["observation_id"] for row in doc.get("observations") or []}
    assert "bible_advancement_closure_hold" in ids
    assert "narrative_path_eval_rates" in ids
    assert "tier2_module_prep" in ids
    assert "tier2_incremental_append_unlock" in ids
    assert "tier3_narrative_upgrade_unlock" in ids
    assert doc["observations_total"] == 10
