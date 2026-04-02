"""Unit tests for multilens dual_regime market adapter (no network)."""

from __future__ import annotations

import importlib.util
from datetime import date, timedelta
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SCR = _ROOT / "scripts" / "multilens_dual_regime_market_adapter_v1.py"


def _load():
    spec = importlib.util.spec_from_file_location("multilens_dual_regime_market_adapter_v1", _SCR)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load()


def test_derive_market_entry_fields_bounded() -> None:
    f = mod.derive_market_entry_fields(vol_30d=0.06, ret_7d=-0.05, ret_14d=0.02, fgi_norm=0.2)
    assert 0.0 <= f["psi_score"] <= 1.0
    assert f["bible_risk_score"] == 0.0
    assert f["context_metrics"]["fear_greed_index"] == 0.2
    v = f["vector_4d"]
    for k in ("S", "L", "K", "M"):
        assert 0.12 <= v[k] <= 0.88


def test_vol_30d_and_ret_n() -> None:
    closes = [100.0 + i * 0.1 for i in range(40)]
    assert mod._vol_30d(closes, 35) > 0.0
    assert mod._ret_n(closes, 35, 7) != 0.0


def test_build_entry_for_date_requires_binance_row() -> None:
    pairs = [("2022-01-01", 47000.0), ("2022-01-02", 47100.0)]
    fgi = {"2022-01-02": 0.4}
    ent = mod.build_entry_for_date("2022-01-02", pairs, fgi)
    assert ent["calendar_date"] == "2022-01-02"
    assert ent["context_metrics"]["fear_greed_index"] == 0.4
    assert ent["adapter_meta"]["mapping_version"]


def test_build_payload_with_fetch_monkeypatch(monkeypatch) -> None:
    d0 = date(2021, 10, 1)
    d1 = date(2022, 1, 2)
    pairs = []
    px = 40000.0
    d = d0
    while d <= d1:
        pairs.append((d.isoformat(), px))
        px += 3.0
        d += timedelta(days=1)

    monkeypatch.setattr(mod, "fetch_binance_daily_closes", lambda **kw: pairs)
    monkeypatch.setattr(
        mod,
        "fetch_fgi_normalized_by_date",
        lambda **kw: {k: 0.55 for k in ("2022-01-02",)},
    )
    payload = mod.build_payload(["2022-01-02"], warn=None)
    assert payload["adapter"] == mod.ADAPTER_SCHEMA
    assert len(payload["entries"]) == 1
    assert payload["entries"][0]["calendar_date"] == "2022-01-02"
    assert "psi_score" in payload["entries"][0]
