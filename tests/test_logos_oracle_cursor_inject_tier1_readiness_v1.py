"""Oracle Logos Cursor-inject Tier-1 readiness gate."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/final/artifacts/logos_oracle_cursor_inject_tier1_readiness_v1_latest.json"


@pytest.fixture(scope="module")
def tier1_chain() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_logos_oracle_cursor_inject_tier1_readiness_chain_v1.py",
            "--skip-pytest",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_tier1_readiness_schema(tier1_chain: None) -> None:
    doc = json.loads(OUT.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "logos_oracle_cursor_inject_tier1_readiness_v1"
    assert doc["tier1_module_ssot_ready"] is True
    assert doc["tier2_prep_ready"] is True
    assert doc["tier2_pin_schema_aligned"] is True
    assert doc.get("tier2_incremental_append_protocol")
    assert doc.get("tier3_narrative_upgrade_protocol")
    tier3 = doc.get("tier3_constitution_narrative_full_upgrade_ready")
    assert isinstance(tier3, bool)
    snap = doc.get("tier2_pin_schema_snapshot") or {}
    assert snap.get("resonance_cap") is not None
    assert snap.get("hd_mission_version")


def test_tier1_checks_include_wiring_and_overlay(tier1_chain: None) -> None:
    doc = json.loads(OUT.read_text(encoding="utf-8-sig"))
    ids = {row["check_id"] for row in doc.get("checks") or []}
    assert "logos_math_overlay_chain" in ids
    assert "cursor_session_upgrade_oracle" in ids
    assert "logos_theory_wiring_registry" in ids
    assert "hd_mission_pin_snapshot" in ids
    assert "resonance_cap_cross_ssot" in ids
    assert "han_vocology_pilot_closure" in ids
