# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_manifest_loads():
    from scripts.market_psych_sasang_axis_v2 import load_manifest

    m = load_manifest()
    assert m["schema"] == "market_psych_to_sasang_axis_manifest_v2"
    assert set(m["axes"]) == {"TY", "SY", "TE", "SE"}


def test_map_row_deterministic():
    from scripts.market_psych_sasang_axis_v2 import load_manifest, map_row_to_sasang

    row = {
        "timestamp_utc": "2026-06-01T00:00:00Z",
        "fear_score": "0.6",
        "greed_score": "0.3",
        "panic_ratio": "0.5",
        "fomo_index": "0.2",
        "volatility_score": "0.4",
        "dispersion_score": "0.3",
        "ret_1d": "-0.01",
        "ret_5d": "-0.03",
        "ret_20d": "-0.05",
        "range_pct": "0.02",
        "vol_ratio": "1.1",
        "drawdown_20d": "-0.08",
        "rsi_14_norm": "0.42",
        "momentum_20_60": "-0.02",
        "trend_strength": "0.2",
    }
    m = load_manifest()
    a = map_row_to_sasang(row, manifest=m)
    b = map_row_to_sasang(row, manifest=m)
    assert a == b
    assert abs(sum(a["axis_normalized"].values()) - 1.0) < 1e-5
    assert "heat_proxy" in a["machine_readables"]
    assert a["byungjeung"]["byungjeung_state"] in ("calm", "watch", "stress", "crisis")


def test_forbidden_field_rejected():
    from scripts.market_psych_sasang_axis_v2 import load_manifest, validate_psych_csv_fields

    m = load_manifest()
    with pytest.raises(ValueError, match="forbidden"):
        validate_psych_csv_fields(["timestamp_utc", "news_headline"], m)


def test_v2_builder_script_exists():
    p = ROOT / "scripts" / "build_market_psychology_kospi_from_yfinance_v2.py"
    assert p.is_file()


def test_v2_lens_bridge_upstream_and_payload():
    import importlib.util

    from scripts.market_psych_sasang_axis_v2 import map_row_to_sasang

    row = {
        "timestamp_utc": "2026-06-01T00:00:00Z",
        "fear_score": "0.5",
        "greed_score": "0.5",
        "panic_ratio": "0.4",
        "fomo_index": "0.3",
        "volatility_score": "0.4",
        "dispersion_score": "0.3",
        "ret_5d": "0.05",
        "ret_20d": "0.1",
        "range_pct": "0.02",
        "vol_ratio": "1.0",
        "drawdown_20d": "-0.02",
        "rsi_14_norm": "0.55",
        "momentum_20_60": "0.03",
        "trend_strength": "0.3",
    }
    mapping = map_row_to_sasang(row)
    bridge_path = ROOT / "scripts" / "market_psych_v2_lens_bridge_v1.py"
    spec = importlib.util.spec_from_file_location("bridge", bridge_path)
    assert spec and spec.loader
    bridge = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bridge)
    upstream = bridge.sasang_upstream_stub_from_v2_mapping(mapping, eval_date="2026-06-01")
    assert upstream["engine_id"] == "market_psych_v2_lens_bridge_v1"
    mr = upstream["sasang_stream_outputs"]["machine_readables"]
    assert "heat_proxy" in mr and "volatility_rarefaction_proxy" in mr

    engine_path = ROOT / "scripts" / "market_sasang_lens_engine_v1.py"
    es = importlib.util.spec_from_file_location("engine", engine_path)
    assert es and es.loader
    engine = importlib.util.module_from_spec(es)
    es.loader.exec_module(engine)
    pol_path = ROOT / "data" / "market_sasang" / "market_sasang_lens_policy_v1.json"
    policy = engine.load_policy(pol_path)
    out = engine.build_market_sasang_lens_payload(
        sasang_lens_doc=upstream,
        policy=policy,
        policy_path=str(pol_path),
        source_input_path="test://v2",
    )
    assert out["schema"] == "market_sasang_lens_v1"
    assert sum(out["state_vector_sasang_softmax"].values()) == pytest.approx(1.0, abs=1e-5)
