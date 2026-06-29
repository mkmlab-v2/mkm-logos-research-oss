"""Oracle Logos Tier-2 incremental append protocol gate."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs/final/artifacts/logos_oracle_tier2_incremental_append_protocol_v1_latest.json"


@pytest.fixture(scope="module")
def tier2_protocol_chain() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/run_logos_oracle_tier2_incremental_append_protocol_chain_v1.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_tier2_protocol_schema(tier2_protocol_chain: None) -> None:
    doc = json.loads(PROTOCOL.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "logos_oracle_tier2_incremental_append_protocol_v1"
    matrix = doc.get("blocker_release_matrix") or []
    all_released = all(row["released"] for row in matrix)
    assert doc["tier2_cursor_rules_full_upgrade_ready"] == all_released
    assert doc["tier3_constitution_narrative_full_upgrade_ready"] is False
    assert len(matrix) == 4


def test_tier2_protocol_has_incremental_steps(tier2_protocol_chain: None) -> None:
    doc = json.loads(PROTOCOL.read_text(encoding="utf-8-sig"))
    steps = doc.get("incremental_append_steps") or []
    assert len(steps) == 4
    assert doc.get("pin_schema_snapshot_sha256")


def test_sidecar_has_logos_segment(tier2_protocol_chain: None) -> None:
    sidecar = json.loads(
        (ROOT / "storage/meta/mkm_sidecar_constitution_paths_v1.json").read_text(encoding="utf-8-sig")
    )
    seg = (sidecar.get("segments") or {}).get("logos_ops_memory_cursor_inject")
    assert seg is not None
    paths = seg.get("extracted_paths") or []
    assert any("run_logos_oracle_cursor_inject_tier1_readiness_chain_v1.py" in p for p in paths)
