from __future__ import annotations

from scripts.fetch_btrack_phase3_onchain_public_proxy_v1 import _ts_to_date, build_proxy_rows


def test_ts_to_date_seconds_and_ms() -> None:
    assert _ts_to_date(1763424000) == "2025-11-18"
    assert _ts_to_date(1763424000000) == "2025-11-18"


def test_build_proxy_rows_has_chain_dates() -> None:
    rows = build_proxy_rows()
    assert len(rows) >= 170
    assert rows[0].get("sensor_id") == "onchain_exchange_netflow"
    assert rows[0].get("research_only") is True
    assert "signed_flow_z" in (rows[0].get("features") or {})
    assert rows[0].get("data_quality") in (
        "measured_public_proxy_v1",
        "measured_chain_activity_proxy_v1",
    )
    assert rows[0].get("note") and "NOT Glassnode" in rows[0]["note"]
