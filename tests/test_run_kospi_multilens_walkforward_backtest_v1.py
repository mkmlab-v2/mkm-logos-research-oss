"""Short-window smoke for KOSPI multilens walk-forward prefilter."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_walkforward_short_window_produces_folds() -> None:
    import scripts.run_kospi_multilens_walkforward_backtest_v1 as mod

    if not mod.KOSPI_CSV.is_file() or not mod.DEFAULT_PANEL.is_file():
        return
    doc = mod.run_walkforward(
        panel_csv=mod.DEFAULT_PANEL,
        kospi_csv=mod.KOSPI_CSV,
        train_days=40,
        test_days=15,
        step_days=15,
        max_window_days=100,
    )
    assert doc["schema"] == "kospi_multilens_walkforward_backtest_v1"
    assert doc["research_only"] is True
    assert doc["summary"]["n_folds"] >= 1
    top2 = doc["summary"].get("recommended_prefilter_variants_top2") or []
    assert len(top2) >= 1
    assert doc["summary"]["selection_top1_hit_rate"] is not None


def test_walkforward_json_on_disk_if_present() -> None:
    path = ROOT / "reports/kospi_multilens_walkforward_backtest_latest.json"
    if not path.is_file():
        return
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc["schema"] == "kospi_multilens_walkforward_backtest_v1"
    assert "folds" in doc
    assert "summary" in doc
    assert doc["summary"].get("n_folds", 0) >= 1
