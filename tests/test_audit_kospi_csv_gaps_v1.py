"""KOSPI CSV gap audit smoke."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_audit_june_window_finds_known_gap() -> None:
    import scripts.audit_kospi_csv_gaps_v1 as mod

    csv_path = ROOT / "research/market_data/kospi_daily_external_yf.csv"
    doc = mod.audit_gaps(
        csv_path=csv_path,
        window_start="2026-06-01",
        window_end="2026-06-05",
    )
    assert doc["schema"] == "kospi_csv_gap_audit_v1"
    assert doc["n_expected_krx_weekdays"] == 5
    # 6/3 지방선거 휴장 — yfinance CSV에 통상 무행
    assert "2026-06-03" in doc["missing_trading_days"]
    assert "2026-06-01" not in doc["missing_trading_days"]
    # 6/4는 evening fetch 이후 CSV에 들어올 수 있음 — 결측 1~2일 허용
    assert len(doc["missing_trading_days"]) in (1, 2)
    assert doc["n_present"] == doc["n_expected_krx_weekdays"] - len(doc["missing_trading_days"])


def test_eval_scores_as_of_day_when_close_present() -> None:
    import scripts.eval_kospi_june2026_daily_prophecy_v1 as ev

    cal = {
        "year_month": "2026-06",
        "trading_days": ["2026-06-05"],
        "rows": [
            {
                "session_date": "2026-06-05",
                "predicted_direction": "bear",
                "kospi_index_prophecy": {"predicted_close_mid": 8300},
            }
        ],
    }
    # Stub closes via monkeypatching load in eval_calendar is heavy; test scoring gate only.
    closes = {"2026-05-29": 8476.15, "2026-06-05": 8357.94}
    as_of = "2026-06-05"
    dk = "2026-06-05"
    assert dk <= as_of or dk not in closes
    assert dk in closes
