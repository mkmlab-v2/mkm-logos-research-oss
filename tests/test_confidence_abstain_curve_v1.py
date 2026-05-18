# @MKM12-METADATA
# Type: Logic
# Purpose: confidence_abstain_curve_v1 preset metrics and lens unanimity
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts/confidence_abstain_curve_v1.py"
_POLICY = _ROOT / "docs/final/artifacts/confidence_abstain_policy_v1.1.json"


def test_lens_unanimous_requires_three_same_sign() -> None:
    from scripts.confidence_abstain_curve_v1 import lens_unanimous_direction

    lens = {
        "price": {"score": 0.2},
        "macro": {"score": 0.1},
        "news": {"score": 0.05},
    }
    ok, direction = lens_unanimous_direction(
        lens, lens_keys=["price", "macro", "news"], min_lenses=3, epsilon=1e-6
    )
    assert ok is True
    assert direction == "bull"

    lens_conflict = {
        "price": {"score": 0.2},
        "macro": {"score": -0.1},
        "news": {"score": 0.05},
    }
    ok2, _ = lens_unanimous_direction(
        lens_conflict, lens_keys=["price", "macro", "news"], min_lenses=3, epsilon=1e-6
    )
    assert ok2 is False


def test_lens_min_agree_two_of_three() -> None:
    from scripts.confidence_abstain_curve_v1 import lens_majority_agreement_direction

    lens_two_bull = {
        "price": {"score": 0.2},
        "macro": {"score": 0.1},
        "news": {"score": -0.05},
    }
    ok, direction = lens_majority_agreement_direction(
        lens_two_bull,
        lens_keys=["price", "macro", "news"],
        min_lenses_agree=2,
        epsilon=1e-6,
    )
    assert ok is True
    assert direction == "bull"


def test_metric_bundle_call_rate_and_directional_skill() -> None:
    from scripts.confidence_abstain_curve_v1 import metric_bundle

    rows = [
        {"predicted_direction": "bull", "actual_direction": "bull"},
        {"predicted_direction": "neutral", "actual_direction": "bear"},
        {"predicted_direction": "bear", "actual_direction": "bull"},
    ]
    m = metric_bundle(rows)
    assert m["n_evaluated"] == 3
    assert m["n_directional_calls"] == 2
    assert m["n_abstain"] == 1
    assert m["call_rate"] == round(2 / 3, 6)
    assert m["directional_skill"] == 0.5
    assert m["headline_skill"] == round(1 / 3, 6)


def test_abstain_preset_blocks_low_confidence() -> None:
    from scripts.confidence_abstain_curve_v1 import apply_abstain_preset_to_direction

    row = {
        "preliminary_direction": "bull",
        "confidence": 0.35,
        "weighted_score": 0.15,
        "lens_values": {
            "price": {"score": 0.2},
            "macro": {"score": 0.1},
            "news": {"score": 0.05},
        },
    }
    preset = {
        "min_confidence": 0.4,
        "min_abs_weighted_margin": 0.03,
        "require_lens_unanimous": False,
        "use_preliminary_direction": True,
    }
    direction, meta = apply_abstain_preset_to_direction(
        row,
        preset,
        lens_keys=["price", "macro", "news"],
        min_lenses=3,
        lens_epsilon=1e-6,
    )
    assert direction == "neutral"
    assert meta["abstain_reason"] == "below_min_confidence"


def test_policy_json_exists_and_has_five_presets() -> None:
    doc = json.loads(_POLICY.read_text(encoding="utf-8"))
    assert doc["schema"] == "confidence_abstain_policy_v1"
    assert doc.get("version") == "1.1.0"
    assert doc.get("research_only") is True
    presets = doc.get("presets") or []
    assert len(presets) >= 5
    ids = {p["policy_id"] for p in presets}
    assert "B0_operational_score_panel" in ids
    assert "P1_5_balanced_sniper_proxy" in ids
    assert "P2_lens3_unanimous_conf_0_50" in ids


def test_btc_actual_direction_by_date_smoke() -> None:
    btc = _ROOT / "research/market_data/btc_daily_external_yf.csv"
    if not btc.is_file():
        import pytest

        pytest.skip(f"missing prerequisite: {btc}")
    from scripts.confidence_abstain_curve_v1 import btc_actual_direction_by_date

    # Use two known adjacent dates from file tail via recent helper
    from scripts.confidence_abstain_curve_v1 import eval_dates_from_recent_trading_days

    kospi = _ROOT / "research/market_data/kospi_daily_external_yf.csv"
    dates = eval_dates_from_recent_trading_days(kospi_csv=kospi, btc_csv=btc, n=5)
    if len(dates) < 2:
        import pytest

        pytest.skip("insufficient trading dates")
    m = btc_actual_direction_by_date(btc, dates, neutral_bps=5.0)
    assert len(m) >= 2
    assert m[dates[-1]] in ("bull", "bear", "neutral")


def test_confidence_abstain_curve_smoke_on_live_panel() -> None:
    score = _ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
    bundle = _ROOT / "docs/final/artifacts/btrack_llm_input_bundle_latest.json"
    btc = _ROOT / "research/market_data/btc_daily_external_yf.csv"
    for p in (score, bundle, btc, _POLICY):
        if not p.is_file():
            import pytest

            pytest.skip(f"missing prerequisite: {p}")
    out = _ROOT / "reports/_tmp_confidence_abstain_curve_v1_test.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--score-json",
            str(score),
            "--output",
            str(out),
            "--min-panel-rows",
            "20",
        ],
        capture_output=True,
        text=True,
        cwd=str(_ROOT),
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "confidence_abstain_curve_v1"
    assert doc["inputs"]["n_joined_rows"] >= 20
    assert len(doc.get("presets") or []) >= 5
    assert doc.get("policy_version") == "1.1.0"
    b0 = next(p for p in doc["presets"] if p["policy_id"] == "B0_operational_score_panel")
    assert b0["full_panel"]["n_evaluated"] >= 20
