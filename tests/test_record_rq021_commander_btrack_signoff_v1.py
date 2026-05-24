"""RQ-021 commander B-track signoff artifact contract."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIGNOFF = ROOT / "docs/final/artifacts/rq021_commander_btrack_signoff_v1_latest.json"


def test_signoff_schema_and_holds() -> None:
    assert SIGNOFF.is_file(), "run record_rq021_commander_btrack_signoff_v1.py first"
    doc = json.loads(SIGNOFF.read_text(encoding="utf-8"))
    assert doc["schema"] == "rq021_commander_btrack_signoff_v1"
    assert doc["approved"]["hypo_cooc_sidecar_on_dryrun"] is True
    holds = doc["explicit_hold"]
    assert holds["active_report_kpi_update"] is False
    assert holds["ms_paste_hwpx_kpi_body"] is False
    assert holds["p4_blended_n400_gate"] is False
