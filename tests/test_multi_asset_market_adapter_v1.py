"""Multi-asset P31 adapter — offline CSV fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import scripts.multi_asset_market_adapter_v1 as ma
import scripts.score_commander_evening_briefing_v1 as ev


def _write_csv(path: Path, rows: list[tuple[str, float]]) -> None:
    lines = ["Date,Open,High,Low,Close,Volume"]
    for d, c in rows:
        lines.append(f"{d},{c},{c},{c},{c},1000")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_evening_asset_panel_kospi_closed_day(tmp_path: Path, monkeypatch) -> None:
    kospi = tmp_path / "kospi.csv"
    _write_csv(kospi, [("2026-05-21", 100.0), ("2026-05-22", 101.0)])
    monkeypatch.setattr(ma, "KOSPI_CSV", kospi)
    monkeypatch.setattr(ma, "BTC_CSV", tmp_path / "btc.csv")
    monkeypatch.setattr(ma, "_btc_spot_price", lambda: 50000.0)

    panel = ma.build_evening_asset_panel(
        "2026-05-23",
        morning_seal={"btc_usd": {"price": 49000.0}},
    )
    assert panel["kospi"]["direction"] == "market_closed"


def test_evening_asset_panel_kospi(tmp_path: Path, monkeypatch) -> None:
    kospi = tmp_path / "kospi.csv"
    _write_csv(kospi, [("2026-05-21", 100.0), ("2026-05-22", 101.0)])
    monkeypatch.setattr(ma, "KOSPI_CSV", kospi)
    monkeypatch.setattr(ma, "BTC_CSV", tmp_path / "btc.csv")
    monkeypatch.setattr(ma, "_btc_spot_price", lambda: 50000.0)

    panel = ma.build_evening_asset_panel(
        "2026-05-22",
        morning_seal={"btc_usd": {"price": 49000.0}},
    )
    assert panel["kospi"]["direction"] == "up"
    assert panel["btc"]["direction"] == "up"
    assert panel["nasdaq"]["direction"] == "pending_until_morning"


def test_nasdaq_prediction_pending_evening(tmp_path: Path, monkeypatch) -> None:
    kospi = tmp_path / "kospi.csv"
    _write_csv(kospi, [("2026-05-21", 100.0), ("2026-05-22", 99.0)])
    monkeypatch.setattr(ma, "KOSPI_CSV", kospi)
    monkeypatch.setattr(ma, "BTC_CSV", tmp_path / "btc.csv")
    monkeypatch.setattr(ma, "_btc_spot_price", lambda: None)

    pred = {
        "prediction_id": "market_posture:nasdaq_prior",
        "kind": "nasdaq_session_hypo",
        "direction_proxy": "WATCH",
        "score_against": ["nasdaq_close_direction"],
    }
    assets = ma.build_evening_asset_panel("2026-05-22", morning_seal={})
    s = ma.score_prediction_multi_asset(pred, assets=assets)
    assert s["outcome"] == "pending_until_morning"


def test_score_evening_briefing_v2_schema(tmp_path: Path, monkeypatch) -> None:
    kospi = tmp_path / "kospi.csv"
    _write_csv(kospi, [("2026-05-21", 100.0), ("2026-05-22", 101.0)])
    monkeypatch.setattr(ma, "KOSPI_CSV", kospi)
    monkeypatch.setattr(ma, "BTC_CSV", tmp_path / "btc.csv")
    monkeypatch.setattr(ma, "_btc_spot_price", lambda: None)

    arch = tmp_path / "2026-05-22_morning_briefing_v1.json"
    arch.write_text(
        json.dumps(
            {
                "calendar_kst": "2026-05-22",
                "briefing": {
                    "briefing_id": "abc",
                    "calendar_kst": "2026-05-22",
                    "predictions": [
                        {
                            "prediction_id": "market_posture:kospi_morning",
                            "kind": "market_direction_hypo",
                            "direction_proxy": "WATCH",
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    doc = ev.score_evening_briefing(arch, kospi_csv=kospi)
    assert doc["schema"] == "commander_evening_briefing_score_v2"
    assert doc.get("multi_asset")
