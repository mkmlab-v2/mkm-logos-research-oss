"""Briefing-primary vs scoring-shadow lane compare [HYPO]."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.kospi_briefing_vs_scoring_lane_lib_v1 import (
    briefing_direction_four_lens_parallel,
    briefing_direction_tail_group,
    build_lane_compare_report,
    load_science_core_directions,
)

ROOT = Path(__file__).resolve().parents[1]


def _fixture_calendar_row(dk: str, *, sasang: str, myeongni: str, logos: str, macro: str, field: str):
    return {
        "session_date": dk,
        "blend": {
            "channels": [
                {"channel": "sasang", "direction": sasang},
                {"channel": "myeongni_independent", "direction": myeongni},
                {"channel": "logos_non_gating", "direction": logos},
                {"channel": "macro", "direction": macro},
                {"channel": "field_regime", "direction": field},
            ]
        },
    }


def test_four_lens_majority_bear_when_three_of_four_bear():
    row = _fixture_calendar_row(
        "2026-06-26",
        sasang="bear",
        myeongni="bull",
        logos="bear",
        macro="bull",
        field="bear",
    )
    science = {"2026-06-26": "bear"}
    assert briefing_direction_four_lens_parallel(row, science_by_date=science) == "bear"
    assert briefing_direction_tail_group(row, science_by_date=science) == "bear"


def test_lane_compare_report_schema_and_deltas(tmp_path: Path):
    science_path = tmp_path / "science.jsonl"
    science_path.write_text('{"session_date":"2026-06-26","direction":"bear"}\n', encoding="utf-8")
    eval_doc = {
        "as_of_kst": "2026-06-26",
        "rows": [
            {
                "session_date": "2026-06-26",
                "predicted_direction": "bull",
                "actual_direction": "bear",
                "outcome": "FAIL",
            }
        ],
    }
    calendar = {
        "rows": [
            _fixture_calendar_row(
                "2026-06-26",
                sasang="bull",
                myeongni="bull",
                logos="bear",
                macro="bull",
                field="bear",
            )
        ]
    }
    science_path = tmp_path / "science.jsonl"
    doc = build_lane_compare_report(
        eval_doc,
        calendar,
        science_jsonl=science_path,
        year_month="2026-06",
    )
    assert doc["schema"] == "kospi_briefing_vs_scoring_lane_compare_v1"
    assert doc["direction_merge_forbidden"] is True
    assert doc["send_gate"] == "HOLD"
    row = doc["rows"][0]
    assert row["scoring_shadow_outcome"] == "FAIL"
    assert row["briefing_four_lens_outcome"] == "NEUTRAL_DRAW"
    assert row["briefing_tail_outcome"] == "HIT"
    assert row["differs_scoring_vs_four_lens"] is True
    assert doc["lanes"]["scoring_shadow"]["raw"]["n_scored"] == 1


def test_load_science_core_directions_skips_bad_lines(tmp_path: Path):
    p = tmp_path / "science.jsonl"
    p.write_text(
        "\n".join(
            [
                '{"session_date":"2026-06-01","direction":"bull"}',
                "not-json",
                '{"session_date":"2026-06-02","direction":"bear"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    out = load_science_core_directions(p)
    assert out["2026-06-01"] == "bull"
    assert out["2026-06-02"] == "bear"


def test_build_script_smoke_if_artifacts_exist():
    ev = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
    cal = ROOT / "reports/kospi_june2026_daily_prophecy_calendar_v1.json"
    if not ev.is_file() or not cal.is_file():
        return
    eval_doc = json.loads(ev.read_text(encoding="utf-8-sig"))
    cal_doc = json.loads(cal.read_text(encoding="utf-8-sig"))
    doc = build_lane_compare_report(
        eval_doc,
        cal_doc,
        science_jsonl=ROOT / "reports/btrack_science_core_per_date_kospi_v1.jsonl",
        year_month="2026-06",
    )
    assert len(doc["rows"]) >= 1
    assert "lanes" in doc
