"""Post-mortem joiner (no network)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import eval_btrack_prophecy_post_mortem_v1 as pm  # noqa: E402


def test_lens_accuracy_multi_row() -> None:
    hypothesis = {
        "schema": "btrack_hypothesis_prophecy_v1",
        "ts_utc": "2026-05-04T00:00:00Z",
        "label": "[HYPO] test",
        "prediction": {"instrument": "multi", "horizon": "1d", "direction": "bear"},
        "runtime_meta": {
            "lens_values": {
                "price": {"score": -0.5, "confidence": 0.5},
                "news": {"score": 0.2, "confidence": 0.1},
            }
        },
    }
    score = {
        "schema": "btrack_prophecy_score_v1",
        "eval_date": "2026-04-29",
        "rows": [
            {
                "instrument": "kospi",
                "eval_date": "2026-04-29",
                "predicted_direction": "bear",
                "actual_direction": "bear",
            },
            {
                "instrument": "btc",
                "eval_date": "2026-04-29",
                "predicted_direction": "bear",
                "actual_direction": "bull",
            },
        ],
    }
    hit = {
        "schema": "prophecy_hit_rate_eval_report_v2",
        "status": "ok",
        "run_mode": "price",
        "metrics": {"price_directional_hit_rate": 0.5, "n_evaluated": 2},
    }
    out = pm.build_post_mortem(
        hypothesis=hypothesis,
        score=score,
        hit_rate=hit,
        hypothesis_path=Path("/tmp/hyp.json"),
        score_path=Path("/tmp/score.json"),
        hit_rate_path=Path("/tmp/hit.json"),
    )
    assert out["schema"] == pm.SCHEMA
    # price → bear both rows: kospi bear hit; btc bull miss
    assert out["lens_accuracy"]["price"]["hits"] == 1
    assert out["lens_accuracy"]["price"]["n_evaluated"] == 2
    # news → bull both rows: kospi bear miss; btc bull hit
    assert out["lens_accuracy"]["news"]["hits"] == 1
    assert out["lens_accuracy"]["news"]["n_evaluated"] == 2
    assert out["hit_rate_eval_summary"]["metrics"]["n_evaluated"] == 2


def test_no_lens_values_warning() -> None:
    hypothesis = {
        "schema": "btrack_hypothesis_prophecy_v1",
        "prediction": {"direction": "bull"},
    }
    score = {
        "schema": "btrack_prophecy_score_v1",
        "eval_date": "2026-04-29",
        "rows": [
            {
                "instrument": "kospi",
                "eval_date": "2026-04-29",
                "predicted_direction": "bull",
                "actual_direction": "bull",
            }
        ],
    }
    out = pm.build_post_mortem(
        hypothesis=hypothesis,
        score=score,
        hit_rate=None,
        hypothesis_path=Path("h.json"),
        score_path=Path("s.json"),
        hit_rate_path=None,
    )
    assert "hypothesis_missing_runtime_meta_lens_values" in out["warnings"]
    assert out["lens_accuracy"] == {}
