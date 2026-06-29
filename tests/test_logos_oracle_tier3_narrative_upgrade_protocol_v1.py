"""Oracle Logos Tier-3 narrative upgrade protocol gate."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs/final/artifacts/logos_oracle_tier3_narrative_upgrade_protocol_v1_latest.json"
MANIFEST = ROOT / "reports/logos_oracle_tier2_cursor_inject_manifest_v1_latest.json"


@pytest.fixture(scope="module")
def tier3_chain() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/run_logos_oracle_tier3_narrative_upgrade_protocol_chain_v1.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_tier3_protocol_schema(tier3_chain: None) -> None:
    doc = json.loads(PROTOCOL.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "logos_oracle_tier3_narrative_upgrade_protocol_v1"
    matrix = doc.get("blocker_release_matrix") or []
    all_released = all(row["released"] for row in matrix)
    assert doc["tier3_constitution_narrative_full_upgrade_ready"] == all_released
    assert doc["tier2_prerequisite_met"] is True
    assert len(matrix) == 4


def test_tier3_protocol_blocked_until_legal_gate(tier3_chain: None) -> None:
    doc = json.loads(PROTOCOL.read_text(encoding="utf-8-sig"))
    matrix = doc.get("blocker_release_matrix") or []
    assert matrix[0]["blocker_id"] == "tier2_prerequisite"
    assert matrix[0]["released"] is True


def test_tier2_manifest_reflects_unlock(tier3_chain: None) -> None:
    subprocess.run(
        [sys.executable, "scripts/build_logos_oracle_tier2_cursor_inject_manifest_v1.py"],
        cwd=ROOT,
        check=True,
    )
    doc = json.loads(MANIFEST.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "logos_oracle_tier2_cursor_inject_manifest_v1"
    assert doc["tier2_gate"]["tier2_cursor_rules_full_upgrade_ready"] is True
    assert doc["tier3_gate"]["tier3_constitution_narrative_full_upgrade_ready"] is True
    assert len(doc.get("tier2_inject_pins") or []) >= 2
