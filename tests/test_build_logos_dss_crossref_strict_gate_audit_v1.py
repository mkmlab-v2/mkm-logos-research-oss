"""Strict partial-anchor gate audit for CROSS_REF + slot mapping."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_logos_dss_crossref_strict_gate_audit_v1.py"
CROSS = ROOT / "docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json"
MAPPING = ROOT / "docs/final/artifacts/logos_dss_crossref_slot_mapping_v1_latest.json"
OUT_TMP = ROOT / "reports" / "tmp" / "logos_dss_crossref_strict_gate_audit_test_v1.json"


@pytest.mark.skipif(not CROSS.is_file() or not MAPPING.is_file(), reason="cross-ref or mapping missing")
def test_strict_gate_audit_smoke() -> None:
    OUT_TMP.parent.mkdir(parents=True, exist_ok=True)
    rc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--entry-ids",
            "ENTRY_06,ENTRY_07",
            "--output",
            str(OUT_TMP),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 0, rc.stderr or rc.stdout
    doc = json.loads(OUT_TMP.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_dss_crossref_strict_gate_audit_v1"
    assert doc["gate"]["cross_ref_contract_ok"] is True
    assert doc["kpi"]["entries_audited"] == 2
    for row in doc["entries"]:
        assert row["cross_ref_marker_ok"] is True
        assert row["slot_mapped"] is True
