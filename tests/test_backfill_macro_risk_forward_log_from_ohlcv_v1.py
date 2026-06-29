"""Macro risk OHLCV backfill smoke."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_build_backfill_rows_smoke() -> None:
    import scripts.backfill_macro_risk_forward_log_from_ohlcv_v1 as mod
    import scripts.run_three_lens_horizon_empirical_eval_v1 as v1

    if not v1.KOSPI_CSV.is_file():
        pytest.skip("KOSPI CSV missing")
    rows = mod.build_backfill_rows(
        csv_path=v1.KOSPI_CSV,
        date_from="2026-02-01",
        date_to="2026-02-28",
        neutral_bps=5.0,
        vol_stress_pct=75.0,
        watch_mode="neutral",
        vol_only_stress=True,
        heuristic_version="ohlcv_research_backfill_v2",
    )
    assert len(rows) >= 10
    assert rows[0]["schema"] == "macro_risk_forward_log_row_v1_research_backfill"
    assert "decision_state" in rows[0]
    assert rows[0].get("heuristic_version") == "ohlcv_research_backfill_v2"
    states = {r.get("decision_state") for r in rows}
    assert states.issubset({"CALM", "WATCH", "REDUCE", "GO"})


def test_tiered_gate_prefers_operational() -> None:
    import scripts.run_three_lens_horizon_empirical_eval_v2 as mod
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        op = root / "op.jsonl"
        bf = root / "bf.jsonl"
        op.write_text(
            json_line(
                {
                    "schema": "macro_risk_forward_log_row_v1",
                    "logged_at_utc": "2026-06-01T10:00:00Z",
                    "decision_state": "GO",
                    "risk_warning_level": "medium",
                }
            ),
            encoding="utf-8",
        )
        bf.write_text(
            json_line(
                {
                    "schema": "macro_risk_forward_log_row_v1_research_backfill",
                    "session_date": "2026-06-01",
                    "logged_at_utc": "2026-06-01T09:00:00Z",
                    "decision_state": "REDUCE",
                    "risk_warning_level": "elevated",
                }
            ),
            encoding="utf-8",
        )
        by_day = mod._build_gate_by_day_tiered([(3, op), (1, bf)])
        assert by_day["2026-06-01"]["decision_state"] == "GO"


def json_line(obj: dict) -> str:
    import json

    return json.dumps(obj, ensure_ascii=False) + "\n"
