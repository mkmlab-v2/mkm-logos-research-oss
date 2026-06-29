"""NEWS-HP-RT bench smoke — skips if cohort missing or too small."""

from __future__ import annotations

from pathlib import Path

from scripts.run_saving_the_news_news_hp_rt_bench_v1 import run_hp_bench

ROOT = Path(__file__).resolve().parents[1]
COHORT = ROOT / "docs/final/artifacts/news_observation_v1_latest.jsonl"


def test_news_hp_rt_bench_runs_or_skips_small_cohort() -> None:
    if not COHORT.is_file():
        return
    doc = run_hp_bench(
        COHORT,
        {
            "sasang_scalar": 0.62,
            "myeongni_day_pillar_prior_hypo": 0.08,
            "wellness_hypo_budget": 0.25,
        },
        min_rows=1,
    )
    assert doc["axis_id"] == "NEWS-HP-RT"
    assert doc["schema"] == "saving_the_news_news_hp_rt_bench_result_v1"
    if doc["measurement_status"] == "COMPLETE":
        kpi = doc["kpi"]
        assert "token_saving_ratio_hp_weighted" in kpi
        assert "delta_vs_news_rt_baseline" in doc
