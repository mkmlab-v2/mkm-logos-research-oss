"""Smoke test for KOSPI multilens blend backtest sweep."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_backtest_produces_ranked_variants() -> None:
    import scripts.run_kospi_multilens_blend_backtest_v1 as mod

    panel = mod._load_panel(mod.DEFAULT_PANEL)
    closes = mod._load_closes(mod.KOSPI_CSV)
    if not panel or not closes:
        return
    rules = mod._read_json(mod.EVOLUTION_RULES)
    doc = mod.run_backtest(
        panel_by_date=panel,
        closes=closes,
        date_from="2026-04-01",
        date_to="2026-05-30",
        rules=rules,
    )
    assert doc["schema"] == "kospi_multilens_blend_backtest_v1"
    assert len(doc["variants"]) >= 8
    assert doc.get("best_variant")
    assert doc["best_variant"]["metrics"]["n_scored"] >= 1


def test_backtest_json_on_disk_if_present() -> None:
    path = ROOT / "reports/kospi_multilens_blend_backtest_latest.json"
    if not path.is_file():
        return
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert "comparison_highlights" in doc
    assert "ranked_top5" in doc
