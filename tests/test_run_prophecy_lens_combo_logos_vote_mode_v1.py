"""Logos vote mode in lens combo backtest (NON_GATING-aligned omit default)."""
from __future__ import annotations

import json
from pathlib import Path

from scripts.run_prophecy_lens_combo_backtest_v1 import (
    _extract_lens_maps,
    _simulate_variant,
)


def _minimal_rows(n: int = 3) -> list[dict]:
    return [
        {
            "eval_date": f"2026-04-{10 + i:02d}",
            "instrument": "btc",
            "actual_direction": "bull",
            "daily_return": 0.01,
        }
        for i in range(n)
    ]


def test_extract_lens_maps_returns_confidence() -> None:
    my, sa, lg, conf = _extract_lens_maps({})
    assert my == {}
    assert sa == {}
    assert lg == 0
    assert conf == 0.0


def test_coordinator_does_not_override_abstain_under_omit() -> None:
    rows = _minimal_rows()
    my_map = {str(r["eval_date"]): 0 for r in rows}
    sa_map = {str(r["eval_date"]): 0 for r in rows}
    btc_prior = {str(r["eval_date"]): 0.05 for r in rows}
    base = {
        "lenses": ["logos", "myeongni", "sasang"],
        "use_coordinator": True,
    }
    with_coord = _simulate_variant(
        variant={**base, "id": "logos+myeongni+sasang+coordinator"},
        rows=rows,
        btc_prior=btc_prior,
        myeongni_map=my_map,
        sasang_map=sa_map,
        logos_sign=-1,
        logos_confidence=0.2,
        logos_vote_mode="omit",
        logos_min_confidence=0.25,
        fee_rate=0.0,
        deadzone=0.001,
        annual_trading_days=252,
    )
    assert with_coord["metrics"]["n_active_days"] == 0


def test_logos_omit_restores_abstain_when_ms_neutral() -> None:
    rows = _minimal_rows()
    my_map = {str(r["eval_date"]): 0 for r in rows}
    sa_map = {str(r["eval_date"]): 0 for r in rows}
    variant = {
        "id": "logos+myeongni+sasang",
        "lenses": ["logos", "myeongni", "sasang"],
        "use_coordinator": False,
    }
    global_run = _simulate_variant(
        variant=variant,
        rows=rows,
        btc_prior={},
        myeongni_map=my_map,
        sasang_map=sa_map,
        logos_sign=-1,
        logos_confidence=0.2,
        logos_vote_mode="global",
        logos_min_confidence=0.25,
        fee_rate=0.0,
        deadzone=0.001,
        annual_trading_days=252,
    )
    omit_run = _simulate_variant(
        variant=variant,
        rows=rows,
        btc_prior={},
        myeongni_map=my_map,
        sasang_map=sa_map,
        logos_sign=-1,
        logos_confidence=0.2,
        logos_vote_mode="omit",
        logos_min_confidence=0.25,
        fee_rate=0.0,
        deadzone=0.001,
        annual_trading_days=252,
    )
    assert global_run["metrics"]["n_active_days"] == len(rows)
    assert omit_run["metrics"]["n_active_days"] == 0


def test_sidecar_fixture_logos_sign_is_scalar(tmp_path: Path) -> None:
    sidecar = {
        "lens_globals_for_sidecar": {
            "logos": {"direction_score": -0.1, "confidence": 0.2},
        },
        "per_date_features": [
            {
                "eval_date": "2026-04-10",
                "dated_source_snapshots_asof_eval_date": {
                    "myeongni_16_state_jsonl": {"snapshot": {"mapping_target": "neutral"}},
                    "sasang_dynamics_jsonl": {"snapshot": {"mapping_target": "neutral"}},
                },
            }
        ],
    }
    p = tmp_path / "sidecar.json"
    p.write_text(json.dumps(sidecar), encoding="utf-8")
    doc = json.loads(p.read_text(encoding="utf-8"))
    _my, _sa, lg, conf = _extract_lens_maps(doc)
    assert lg == -1
    assert conf == 0.2
