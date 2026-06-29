# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_fabba_sidecar_row_numeric_encoding() -> None:
    from scripts.btrack_ohlcv_feature_lut_lib_v1 import fabba_sidecar_row_to_numeric_features

    row = {
        "fabba_ngram_pred": "bull",
        "fabba_ngram_confidence": 0.75,
        "fabba_last_slope": 0.0012,
        "fabba_last_slope_pred": "bear",
        "non_gating": True,
    }
    num = fabba_sidecar_row_to_numeric_features(row)
    assert num["fabba_ngram_pred_code"] == 1.0
    assert num["fabba_last_slope_pred_code"] == -1.0
    assert num["fabba_ngram_confidence"] == 0.75


def test_merge_preserves_base_features() -> None:
    from scripts.btrack_ohlcv_feature_lut_lib_v1 import merge_fabba_sidecar_into_lut_document

    base = {
        "schema": "btrack_ohlcv_feature_lut_v1",
        "intersection_dates": ["2026-01-02"],
        "features_by_instrument": {
            "kospi": {"2026-01-02": {"ret_1": 0.01, "ret_3": 0.02}},
            "btc": {"2026-01-02": {"ret_1": -0.01, "ret_3": -0.02}},
        },
        "stats": {},
    }
    sidecar = {
        "kospi": {
            "2026-01-02": {
                "fabba_ngram_pred": "neutral",
                "fabba_ngram_confidence": 0.5,
                "fabba_last_slope": 0.0,
                "fabba_last_slope_pred": "neutral",
            }
        },
        "btc": {},
    }
    merged = merge_fabba_sidecar_into_lut_document(
        base,
        sidecar_by_instrument=sidecar,
        sidecar_params={"tol": 0.03},
        generated_at_utc="2026-06-22T00:00:00Z",
    )
    k = merged["features_by_instrument"]["kospi"]["2026-01-02"]
    assert k["ret_1"] == 0.01
    assert k["ret_3"] == 0.02
    assert k["fabba_ngram_pred_code"] == 0.0
    assert merged["schema"] == "btrack_ohlcv_feature_lut_with_fabba_sidecar_v1"
    assert merged["non_gating"] is True


def test_build_merged_lut_cli_smoke(tmp_path: Path) -> None:
    kospi = ROOT / "research/market_data/kospi_daily_external_yf.csv"
    btc = ROOT / "research/market_data/btc_daily_external_yf.csv"
    if not kospi.is_file() or not btc.is_file():
        pytest.skip("ohlcv csv missing")

    out = tmp_path / "merged_lut.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_btrack_ohlcv_feature_lut_with_fabba_sidecar_v1.py"),
            "--kospi-csv",
            str(kospi),
            "--btc-csv",
            str(btc),
            "--last-n-intersection",
            "90",
            "--output",
            str(out),
            "--bridge-output",
            str(tmp_path / "bridge.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "btrack_ohlcv_feature_lut_with_fabba_sidecar_v1"
    assert doc["sidecar_params"]["tol"] == 0.03
    assert doc["sidecar_params"]["ngram_size"] == 2
    assert doc["stats"]["n_sidecar_feature_rows_merged"] >= 80
    sample = next(iter(doc["features_by_instrument"]["kospi"].values()))
    assert "ret_1" in sample
    assert "fabba_ngram_pred_code" in sample
    assert "fabba_ngram_confidence" in sample


def test_ablation_smoke_cli(tmp_path: Path) -> None:
    score = ROOT / "reports/btrack_prophecy_score_recommended_eval_chain_v1_latest.json"
    merged = ROOT / "reports/btrack_ohlcv_feature_lut_with_fabba_sidecar_v1_latest.json"
    if not score.is_file() or not merged.is_file():
        pytest.skip("score or merged lut missing")
    out = tmp_path / "ablation.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_prophecy_fabba_lut_wf_ablation_smoke_v1.py"),
            "--score-json",
            str(score),
            "--merged-lut",
            str(merged),
            "--n-folds",
            "4",
            "--output",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "prophecy_fabba_lut_wf_ablation_smoke_v1"
    assert doc["feature_parity"]["base_vs_merged_stripped_ok"] is True
    assert doc["wf_variants"]["base_lut_maps"]["n_folds_scored"] >= 1
