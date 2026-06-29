"""B-track daily hero board 5-slot smoke tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_hero_board_lib_slot_ids():
    from scripts.btrack_daily_hero_board_lib_v1 import slot_ids

    assert len(slot_ids()) == 5
    assert "kospi_direction" in slot_ids()
    assert "foreign_flow" in slot_ids()


def test_build_calendar_schema():
    from scripts.build_btrack_daily_hero_board_calendar_v1 import build_calendar

    doc = build_calendar(year_month="2026-06", seal_date="2026-06-26")
    assert doc["schema"] == "btrack_daily_hero_board_calendar_v1"
    assert doc["n_trading_days"] >= 20
    row = next(r for r in doc["rows"] if r["session_date"] == "2026-06-26")
    assert "kospi_direction" in row["slots"]
    assert row["slots"]["foreign_flow"].get("probability_0_1") is not None


def test_eval_board_smoke():
    from scripts.build_btrack_daily_hero_board_calendar_v1 import build_calendar
    from scripts.eval_btrack_daily_hero_board_v1 import eval_board

    cal = build_calendar(year_month="2026-06", seal_date=None)
    doc = eval_board(cal, as_of_kst="2026-06-26")
    assert doc["schema"] == "btrack_daily_hero_board_eval_v1"
    assert doc["n_session_days"] >= 1
    assert "kospi_direction" in doc["slot_metrics"]


def test_sync_hero_board_weather_gt_from_csv(tmp_path):
    from scripts.sync_hero_board_weather_gt_from_openmeteo_v1 import sync_jsonl

    csv_path = tmp_path / "weather.csv"
    csv_path.write_text(
        "date,seoul_precip_mm,seoul_weather_source\n2026-06-26,6.2,open_meteo_archive\n",
        encoding="utf-8-sig",
    )
    jsonl_path = tmp_path / "gt.jsonl"
    doc = sync_jsonl(csv_path=csv_path, jsonl_path=jsonl_path, threshold_mm=5.0, merge=False)
    assert doc["june_2026_rows"] == 1
    row = json.loads(jsonl_path.read_text(encoding="utf-8").strip())
    assert row["observation_date_local"] == "2026-06-26"
    assert row["precip_binary_ge_threshold"] is True


def test_macro_news_shock_uses_pre_news_meta():
    from scripts.btrack_daily_hero_board_lib_v1 import predict_slot

    pred = predict_slot("macro_news_shock", "2026-06-26")
    meta = pred.get("meta") or {}
    assert pred.get("source") == "news_lens+pre_news_shadow"
    assert "pre_news_rows" in meta


def test_headline_verify_lib_session_match():
    from scripts.btrack_macro_news_shock_headline_verify_lib_v1 import headline_gt_for_session

    pre = {
        "rows": [
            {
                "headline": "FOMC 금리 인상 쇼크에 코스피 급락",
                "pub_date": "Fri, 26 Jun 2026 06:24:00 +0900",
            }
        ]
    }
    gt = headline_gt_for_session(pre, "2026-06-26")
    assert gt["headline_scorable"] is True
    assert gt["actual_binary_headline"] is True


def test_macro_news_shock_dual_verify_score():
    from scripts.btrack_daily_hero_board_lib_v1 import predict_slot, score_slot

    pred = predict_slot("macro_news_shock", "2026-06-26")
    sc = score_slot("macro_news_shock", "2026-06-26", pred)
    assert sc.get("scorable") is True
    assert "outcome_proxy" in sc
    assert "verify_mode" in sc


def test_hero_board_chain_evening_smoke():
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_btrack_daily_hero_board_chain_v1.py"),
            "--phase",
            "evening",
            "--skip-kospi-loop",
            "--skip-llm-insight",
            "--skip-data-refresh",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    rep = json.loads((ROOT / "reports/btrack_daily_hero_board_daily_chain_v1_latest.json").read_text(encoding="utf-8"))
    assert rep.get("ok") is True
    assert any(s["name"] == "eval_hero_board" for s in rep.get("steps") or [])


def test_daily_hero_board_fixture_merges():
    gen = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/generate_general_prophecy_v1.py"),
            "--output",
            "docs/final/artifacts/general_prophecy_latest.json",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert gen.returncode == 0, gen.stderr
    reg = json.loads((ROOT / "docs/final/artifacts/general_prophecy_latest.json").read_text(encoding="utf-8"))
    ids = {q["question_id"] for q in reg.get("questions") or []}
    assert "hero.macro.us_cpi_yoy_ge_3_20260715" in ids
