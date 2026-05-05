from __future__ import annotations

from datetime import UTC, datetime, timedelta

from scripts.build_fragility_macro_risk_weekly_report_v1 import build_weekly_report


def test_weekly_report_counts_recent_rows_only() -> None:
    now = datetime(2026, 5, 4, 15, 30, tzinfo=UTC)
    rows = [
        {
            "ts_utc": (now - timedelta(days=1)).isoformat().replace("+00:00", "Z"),
            "status": "pass",
            "gate": "AMBER",
            "decision_state": "WATCH",
            "source_mode": "fallback_defaults",
            "quaternion_signal": "phase_shift_mid",
        },
        {
            "ts_utc": (now - timedelta(days=3)).isoformat().replace("+00:00", "Z"),
            "status": "fail",
            "gate": "RED",
            "decision_state": "FORCE_HOLD",
            "source_mode": "fred_live",
            "quaternion_signal": "phase_shift_high",
        },
        {
            "ts_utc": (now - timedelta(days=10)).isoformat().replace("+00:00", "Z"),
            "status": "pass",
            "gate": "GREEN",
            "decision_state": "GO",
            "source_mode": "fred_live",
            "quaternion_signal": "phase_shift_low",
        },
    ]
    report = build_weekly_report(rows, now=now)
    assert report["sample_count"] == 2
    assert report["status_counts"]["pass"] == 1
    assert report["status_counts"]["fail"] == 1
    assert report["gate_counts"]["AMBER"] == 1
    assert report["gate_counts"]["RED"] == 1
