"""B-track vs VPS PnL separation report contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.build_btrack_vps_pnl_separation_report_v1 import build_report, format_observation_line


def test_separation_report_forbids_correlation_claim(tmp_path: Path) -> None:
    prophecy = tmp_path / "prophecy.json"
    prophecy.write_text(
        json.dumps(
            {
                "generated_at_utc": "2026-05-16T00:00:00Z",
                "run_mode": "price",
                "inputs": {"score_json": "score.json"},
                "metrics": {
                    "headline_instrument": "btc",
                    "scoring_mode": "per_date_direction_overrides",
                    "price_directional_hit_rate": 0.5,
                    "n_evaluated": 10,
                    "price_hit_rate_on_directional_calls": 0.6,
                    "n_directional_calls": 5,
                    "n_neutral_predictions": 5,
                },
            }
        ),
        encoding="utf-8",
    )
    gate = tmp_path / "gate.json"
    gate.write_text(
        json.dumps(
            {
                "schema": "strategy_promotion_gate_v1",
                "generated_at_utc": "2026-05-16T01:00:00Z",
                "metrics": {
                    "treatment": {
                        "trades": 3,
                        "hit_rate": 0.33,
                        "net_pnl": -1.5,
                        "profit_factor": 0.9,
                        "max_drawdown": 0.1,
                    },
                    "shadow": {"net_pnl": 100.0},
                },
                "decision": {"promotion_ready": False, "recommended_mode": "hold_shadow"},
            }
        ),
        encoding="utf-8",
    )
    report = build_report(
        prophecy_eval=prophecy,
        trading_gate=gate,
        trade_window=tmp_path / "missing_window.json",
    )
    assert report["correlation_claim_allowed"] is False
    assert report["axes"]["btrack_prophecy"]["available"] is True
    assert report["axes"]["vps_live_trading"]["available"] is True
    assert report["contrast_snapshot"]["same_metric"] is False
    assert report["axes"]["btrack_prophecy"]["auto_triggers_live_trading"] is False
    assert report.get("observation_line")
    assert "MKM-BTRACK-vs-VPS" in report["observation_line"]
    assert "same_metric=false" in report["observation_line"]
    assert format_observation_line(report) == report["observation_line"]
