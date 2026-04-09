# @MKM12-METADATA
# Type: Logic
# Purpose: Validate compression weekly governance report contract.
# Keywords: compression, governance, weekly, kpi

from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_GOV = _ROOT / "docs" / "final" / "artifacts" / "compression_weekly_governance_report_latest.json"


def _load(path: Path) -> dict:
    assert path.is_file(), f"missing artifact: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def test_compression_weekly_governance_report_contract() -> None:
    d = _load(_GOV)
    assert d.get("schema") == "compression_weekly_governance_report_v1"
    assert d.get("generated_at_utc")
    assert d.get("refresh_calendar_date_utc")
    assert d.get("iso_week_label")
    assert isinstance(d.get("kpi_summary_embed"), dict)
    assert d["kpi_summary_embed"].get("schema") == "ultra_compression_kpi_summary_v1"
    ptr = d.get("artifact_pointers") or {}
    assert "active_report_track_a" in ptr
    gov = d.get("governance") or {}
    assert "chain_runner" in gov
