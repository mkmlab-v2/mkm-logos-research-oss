"""Proxy forward eval smoke."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_proxy_may_forward_gate_pass() -> None:
    import json

    import scripts.run_kospi_june2026_proxy_forward_eval_v1 as mod

    rules = json.loads(
        (ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json").read_text(encoding="utf-8")
    )
    from scripts.build_kospi_june2026_daily_prophecy_calendar_v1 import KOSPI_CSV

    if not KOSPI_CSV.is_file():
        return
    doc = mod.run_proxy_forward_eval(
        rules=rules,
        proxy_year_month="2026-05",
        candidate_id="v2_lens3_heavy",
    )
    assert doc["schema"] == "kospi_june2026_proxy_forward_eval_v1"
    assert int(doc["active"]["n_scored"] or 0) >= 15
    assert doc["gate_pass"] is True
