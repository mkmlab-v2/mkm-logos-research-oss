"""Contract tests for Sasang dynamics B-track JSONL (stdlib validation only)."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SCR = _ROOT / "scripts" / "sasang_dynamics_regime_mapping_ledger.py"


def _load_validate():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "sasang_dynamics_regime_mapping_ledger", _SCR
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load_validate()


def test_sample_jsonl_validates() -> None:
    path = _ROOT / "data" / "sasang" / "sasang_dynamics_regime_mapping_v1.sample.jsonl"
    n = mod.validate_jsonl_file(path)
    assert n == 6


def test_btc_anchor_smoke_jsonl_validates() -> None:
    path = _ROOT / "data" / "sasang" / "sasang_dynamics_regime_mapping_v1.btc_anchor_smoke.jsonl"
    n = mod.validate_jsonl_file(path)
    assert n == 3


def test_missing_required_fails() -> None:
    bad = {"ts_utc": "2026-01-01T00:00:00+00:00"}
    errs = mod.validate_sasang_record(bad)
    assert any("missing required key" in e for e in errs)


def test_autobind_must_be_true() -> None:
    base = {
        "ts_utc": "2026-01-01T00:00:00+00:00",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "stub": "x",
        "a_track_autobind_forbidden": False,
        "machine_readables": {
            "heat_proxy": 0.5,
            "cold_proxy": 0.5,
            "volatility_rarefaction_proxy": 0.0,
        },
    }
    errs = mod.validate_sasang_record(base)
    assert any("a_track_autobind_forbidden must be true" in e for e in errs)


def test_proxy_range() -> None:
    base = {
        "ts_utc": "2026-01-01T00:00:00+00:00",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "stub": "x",
        "a_track_autobind_forbidden": True,
        "machine_readables": {
            "heat_proxy": 1.5,
            "cold_proxy": 0.5,
            "volatility_rarefaction_proxy": 0.0,
        },
    }
    errs = mod.validate_sasang_record(base)
    assert any("heat_proxy" in e and "[0, 1]" in e for e in errs)
