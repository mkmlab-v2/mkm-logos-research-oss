# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def _import_lib():
    sys.path.insert(0, str(_ROOT))
    from scripts import prophecy_fabba_sidecar_lib_v1 as mod

    return mod


def test_apca_pieces_nonempty_on_trend() -> None:
    mod = _import_lib()
    values = [100.0 + i * 0.5 for i in range(40)]
    pieces = mod.apca_pieces(values, tol=0.02)
    assert len(pieces) >= 1
    v0, v1, length = pieces[-1]
    assert length >= 1
    assert v1 >= v0


def test_fabba_sidecar_pred_bull_on_uptrend() -> None:
    mod = _import_lib()
    closes = [100.0 + i for i in range(50)]
    pred = mod.fabba_sidecar_pred(
        closes,
        40,
        lookback=30,
        tol=0.02,
        neutral_bps=2.0,
        backend="apca_stub",
    )
    assert pred == "bull"


def test_blocked_folds_count() -> None:
    mod = _import_lib()
    dates = [f"2026-01-{i:02d}" for i in range(1, 31)]
    folds = mod.blocked_folds(dates, 5)
    assert len(folds) == 4


def test_ngram_lut_clear_and_causal_predict() -> None:
    mod = _import_lib()
    import math

    closes = [100.0 + 5.0 * math.sin(i / 3.0) + i * 0.05 for i in range(60)]
    lut = mod.NgramPatternLut()
    pred_empty, conf_empty = lut.predict(
        closes,
        30,
        lookback=20,
        ngram_size=3,
        tol=0.05,
        backend="apca_stub",
    )
    assert pred_empty == "neutral"
    assert conf_empty == 0.0
    lut.fit(
        closes,
        list(range(25, 50)),
        lookback=20,
        ngram_size=3,
        tol=0.05,
        backend="apca_stub",
        neutral_bps=2.0,
    )
    assert len(lut.lut) > 0
    pred, conf = lut.predict(
        closes,
        52,
        lookback=20,
        ngram_size=3,
        tol=0.05,
        backend="apca_stub",
    )
    assert pred in mod.VALID_DIRECTIONS
    assert 0.0 <= conf <= 1.0
    lut.clear()
    assert len(lut.lut) == 0


def test_neutral_filter_boundary() -> None:
    mod = _import_lib()
    assert mod.actual_direction(0.0003, 2.0) == "bull"
    assert mod.actual_direction(-0.0003, 2.0) == "bear"
    assert mod.actual_direction(0.0001, 2.0) == "neutral"


def test_causal_feature_row_non_gating() -> None:
    mod = _import_lib()
    closes = [100.0 + i * 0.2 for i in range(40)]
    row = mod.build_causal_sidecar_feature_row(
        closes,
        30,
        lookback=15,
        ngram_size=3,
        tol=0.02,
        backend="apca_stub",
        neutral_bps=2.0,
    )
    assert row.get("non_gating") is True
    assert "fabba_ngram_pred" in row
    assert row["fabba_ngram_pred"] in mod.VALID_DIRECTIONS


def test_runner_smoke_kospi_apca_stub(tmp_path: Path) -> None:
    kospi = _ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
    if not kospi.is_file():
        pytest.skip("kospi csv missing")
    out = tmp_path / "fabba_shadow.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "run_prophecy_fabba_sidecar_wf_shadow_v1.py"),
            "--kospi-csv",
            str(kospi),
            "--eval-days",
            "120",
            "--n-folds",
            "4",
            "--neutral-bps-list",
            "5.0",
            "--backend",
            "apca_stub",
            "--output",
            str(out),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "prophecy_fabba_sidecar_wf_shadow_v1"
    assert doc["research_only"] is True
    assert doc["send_gate"] == "HOLD"
    assert doc["track_a_mutated"] is False
    panel = doc["panels"][0]
    assert panel["instrument_id"] == "kospi"
    assert panel["status"] == "ok"
    run = panel["neutral_bps_runs"][0]
    arms = {a["arm_id"]: a for a in run["arms"]}
    assert "fabba_sidecar_last_slope" in arms
    assert "fabba_sidecar_ngram_lut" in arms
    assert arms["fabba_sidecar_last_slope"]["total_n_evaluated"] >= 1
    assert arms["fabba_sidecar_ngram_lut"]["total_n_evaluated"] >= 1


def test_feature_lut_builder_smoke(tmp_path: Path) -> None:
    kospi = _ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
    if not kospi.is_file():
        pytest.skip("kospi csv missing")
    out = tmp_path / "fabba_lut.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "build_prophecy_fabba_sidecar_feature_lut_v1.py"),
            "--kospi-csv",
            str(kospi),
            "--eval-days",
            "90",
            "--backend",
            "apca_stub",
            "--output",
            str(out),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "prophecy_fabba_sidecar_feature_lut_bundle_v1"
    assert doc["non_gating"] is True
    inst = doc["instruments"][0]
    assert inst["schema"] == "prophecy_fabba_sidecar_feature_lut_v1"
    assert inst["stats"]["n_feature_rows"] >= 20
    sample_date = next(iter(inst["features_by_date"]))
    assert inst["features_by_date"][sample_date]["non_gating"] is True


def test_dual_leg_runner_smoke(tmp_path: Path) -> None:
    kospi = _ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
    btc = _ROOT / "research" / "market_data" / "btc_daily_external_yf.csv"
    if not kospi.is_file() or not btc.is_file():
        pytest.skip("market csv missing")
    out = tmp_path / "dual_leg.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "run_prophecy_fabba_sidecar_dual_leg_wf_v1.py"),
            "--last-n-intersection",
            "90",
            "--n-folds",
            "4",
            "--backend",
            "apca_stub",
            "--output",
            str(out),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "prophecy_fabba_sidecar_dual_leg_wf_v1"
    pooled = {a["arm_id"]: a for a in doc["dual_leg_pooled_arms"]}
    assert "fabba_sidecar_ngram_lut" in pooled
    assert pooled["fabba_sidecar_ngram_lut"]["total_n_evaluated"] >= 1


def test_pool_arms_across_instruments_synthetic() -> None:
    mod = _import_lib()
    per = [
        {
            "instrument_id": "kospi",
            "status": "ok",
            "arms": [
                {
                    "arm_id": "fabba_sidecar_ngram_lut",
                    "pooled_test_directional_hit_rate": 0.6,
                    "total_n_evaluated": 10,
                    "total_price_hits": 6,
                    "pred_distribution": {"bull": 6, "bear": 4, "neutral": 0},
                }
            ],
        },
        {
            "instrument_id": "btc",
            "status": "ok",
            "arms": [
                {
                    "arm_id": "fabba_sidecar_ngram_lut",
                    "pooled_test_directional_hit_rate": 0.5,
                    "total_n_evaluated": 10,
                    "total_price_hits": 5,
                    "pred_distribution": {"bull": 5, "bear": 5, "neutral": 0},
                }
            ],
        },
    ]
    pooled = mod.pool_arms_across_instruments(per)
    arm = next(a for a in pooled if a["arm_id"] == "fabba_sidecar_ngram_lut")
    assert arm["total_n_evaluated"] == 20
    assert arm["total_price_hits"] == 11
    assert arm["pooled_test_directional_hit_rate"] == 0.55


def test_sweep_dual_leg_revalidate_smoke(tmp_path: Path) -> None:
    kospi = _ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
    btc = _ROOT / "research" / "market_data" / "btc_daily_external_yf.csv"
    sweep = _ROOT / "reports" / "prophecy_fabba_sidecar_param_sweep_v1_latest.json"
    if not kospi.is_file() or not btc.is_file() or not sweep.is_file():
        pytest.skip("csv or sweep artifact missing")
    out = tmp_path / "revalidate.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "run_prophecy_fabba_sidecar_sweep_dual_leg_revalidate_v1.py"),
            "--last-n-intersection",
            "90",
            "--n-folds",
            "4",
            "--output",
            str(out),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "prophecy_fabba_sidecar_sweep_dual_leg_revalidate_v1"
    assert "overfit_assessment" in doc
    assert doc["variants"]["default_dual_leg"]["ngram_summary"]["total_n_evaluated"] >= 1
