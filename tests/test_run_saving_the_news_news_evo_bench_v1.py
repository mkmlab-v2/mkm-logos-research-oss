"""NEWS-EVO-BENCH offline runner smoke."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.run_saving_the_news_news_evo_bench_v1 import run_bench

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def test_news_evo_bench_aggregates_four_axes(tmp_path: Path) -> None:
    price = tmp_path / "price.json"
    price.write_text(
        json.dumps(
            {
                "metrics": {"price_directional_hit_rate": 0.6, "n_evaluated": 10},
            }
        ),
        encoding="utf-8",
    )
    general = tmp_path / "general.json"
    general.write_text(
        json.dumps(
            {
                "metrics": {
                    "mean_brier_score": 0.1,
                    "n_evaluated": 4,
                    "ece_binary": {"weighted_ece": 0.2, "n_bins": 10},
                }
            }
        ),
        encoding="utf-8",
    )
    rt = tmp_path / "rt.json"
    rt.write_text(
        json.dumps(
            {
                "measurement_status": "COMPLETE",
                "kpi": {"token_saving_ratio": 0.4, "jaccard_fidelity_proxy": 0.5},
            }
        ),
        encoding="utf-8",
    )
    hp = tmp_path / "hp.json"
    hp.write_text(
        json.dumps(
            {
                "kpi": {"token_saving_ratio_hp_weighted": 0.48},
                "delta_vs_news_rt_baseline": {"token_saving_ratio_delta_hp_minus_baseline": 0.08},
            }
        ),
        encoding="utf-8",
    )
    doc = run_bench(
        price_path=price,
        general_path=general,
        news_rt_path=rt,
        news_hp_path=hp,
        calibration_path=tmp_path / "missing_join.json",
        contract_path=ROOT / "docs/final/artifacts/fixtures/news_evo_bench_contract_v1.example.json",
    )
    assert doc["schema"] == "saving_the_news_news_evo_bench_result_v1"
    assert doc["measurement_status"] in ("COMPLETE", "COMPLETE_PARTIAL")
    assert doc["loss_axes"]["L_price"]["measurement_status"] == "COMPLETE"
    assert doc["loss_axes"]["L_compression_raw"]["operational_post_processor"]["delta_hp_minus_baseline"] == 0.08
    assert doc["composite_hypo"]["L_total_hypo"] is not None
    assert doc["raw_repair_dual_report"]["raw"]["news_rt_token_saving"] == 0.4


def test_news_evo_bench_live_workspace_smoke() -> None:
    doc = run_bench()
    assert doc["axis_id"] == "NEWS-EVO-BENCH"
    assert doc["lane"] == "research_only"
    assert "L_price" in doc["loss_axes"]
    assert doc["forbidden_interpretation"]
