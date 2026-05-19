"""KPI-B operational alert threshold contract."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THRESHOLDS = ROOT / "docs/final/artifacts/prophecy_runtime_health_thresholds_v1.json"


def test_kpi_b_threshold_fields_present() -> None:
    obj = json.loads(THRESHOLDS.read_text(encoding="utf-8"))
    assert obj["min_hit_rate_kpi_b_per_date_headline"] == 0.43
    assert obj["min_directional_hit_rate_kpi_b_operational"] == 0.50
    assert "note_kpi_b_alert_ko" in obj
