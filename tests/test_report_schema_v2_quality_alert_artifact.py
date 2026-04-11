from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts" / "report_schema_v2_quality_alert_latest.json"


def test_report_schema_v2_quality_alert_artifact() -> None:
    assert ART.is_file(), f"missing artifact: {ART}"
    doc = json.loads(ART.read_text(encoding="utf-8"))
    assert doc.get("schema") == "report_schema_v2_quality_alert_v1"
    status = doc.get("status") or {}
    metrics = doc.get("metrics") or {}
    assert status.get("severity") in {"INFO", "WARN", "FAIL"}
    assert isinstance(status.get("delta_streak_alert"), bool)
    assert isinstance(status.get("reason_codes"), list)
    assert "grounded_false_rate" in metrics
