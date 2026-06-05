"""Render June 4AI prophecy MD smoke."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_render_markdown_sections() -> None:
    import scripts.render_kospi_june_4ai_prophecy_report_v1 as mod

    doc = {
        "status": "WATCH",
        "content_hash": "abc123",
        "executive_summary_ko": {"stance": "횡보", "conflict_days": 1, "observe_days": 2, "n_trading_days": 2},
        "blend_formula_note": {"v1_legacy_doc": "legacy"},
        "eval_summary": {"as_of_kst": "2026-06-05", "n_scored": 1, "metrics": {"soft_hit_rate": 0.5}},
        "rows": [
            {
                "session_date": "2026-06-01",
                "weekday_ko": "월",
                "four_ai_direction_ko": "횡보·관측",
                "v2_multilens_direction_ko": "하락",
                "reference_close_mid": 8475.5,
                "weight_field": "multilens_conflict_hold",
            }
        ],
    }
    md = mod.render_markdown(doc)
    assert "4AI · v2_multilens" in md
    assert "06-01" in md
    assert "파이어월" in md
    assert "재현" in md
