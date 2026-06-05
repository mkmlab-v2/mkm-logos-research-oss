"""Smoke test for KOSPI lens ablation backtest."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ablation_produces_four_arms() -> None:
    import scripts.run_kospi_lens_ablation_backtest_v1 as mod
    import scripts.run_kospi_multilens_blend_backtest_v1 as bt

    panel = bt._load_panel(bt.DEFAULT_PANEL)
    closes = bt._load_closes(bt.KOSPI_CSV)
    if not panel or not closes:
        return
    rules = bt._read_json(bt.EVOLUTION_RULES)
    doc = mod.run_ablation(
        panel_by_date=panel,
        closes=closes,
        date_from="2026-04-01",
        date_to="2026-05-30",
        rules=rules,
    )
    assert doc["schema"] == "kospi_lens_ablation_backtest_v1"
    assert doc["watch_ablation_run"] is True
    assert len(doc["arms"]) == 4
    arm_ids = {a["arm_id"] for a in doc["arms"]}
    assert arm_ids == {
        "lens3_runtime",
        "sasang_myeongni_only",
        "three_lens_runtime",
        "lens3_4ai_overlay",
    }
    assert doc.get("four_ai_overlay_uplift_pp_vs_lens3_runtime") is not None
    assert doc.get("best_arm")


def test_ablation_json_on_disk_if_present() -> None:
    path = ROOT / "reports/kospi_lens_ablation_backtest_latest.json"
    if not path.is_file():
        return
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc["schema"] == "kospi_lens_ablation_backtest_v1"
    assert "comparisons" in doc
    assert "verdict_ko" in doc


def test_per_date_static_loader_shape() -> None:
    from scripts.kospi_lens_per_date_static_v1 import static_lenses_for_eval_date

    sa_by = {
        "2026-06-01": {"mapping_target": "bull", "eval_date": "2026-06-01", "stub": False},
    }
    my_by = {
        "2026-06-01": {"mapping_target": "sideways", "eval_date": "2026-06-01", "stub": False},
    }
    out = static_lenses_for_eval_date(
        "2026-06-05",
        sasang_by_day=sa_by,
        myeongni_by_day=my_by,
        baseline={"sasang": {}, "myeongni_independent": {}, "macro": {"loaded": False}},
    )
    assert out["sasang"]["direction"] == "bull"
    assert out["sasang"]["per_date"] is True
    assert out["myeongni_independent"]["direction"] == "neutral"
