"""Logos DSS cross-ref slot mapping wrapper."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_logos_dss_crossref_slot_mapping_v1.py"
DSS = ROOT / "data/logos/manuscripts/dss_parsed_enriched.jsonl"
CROSS = ROOT / "docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json"
ARTIFACT = ROOT / "docs/final/artifacts/logos_dss_crossref_slot_mapping_v1_latest.json"


@pytest.mark.skipif(not DSS.is_file() or not CROSS.is_file(), reason="DSS enriched or cross-ref missing")
def test_logos_dss_crossref_slot_mapping_smoke() -> None:
    rc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 0, rc.stderr or rc.stdout
    assert ARTIFACT.is_file()
    doc = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_dss_crossref_slot_mapping_v1"
    assert doc["track_wall"]["ready_for_external_send"] is False
    kpi = doc["kpi"]
    assert kpi["slot_count"] == 16
    assert kpi["mapped_slot_count"] == 16
