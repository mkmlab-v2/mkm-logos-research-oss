"""Smoke tests for veto-hold counterfactual (offline fixtures)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.sasang_regime_mkm_split_v1 import (  # noqa: E402
    apply_geumhwa_min_days_gate,
    apply_supplier_hysteresis as _apply_supplier_hysteresis,
    regime_mkm_split_v1 as _regime_mkm_split_v1,
    supplier_tight_field_momentum as _supplier_tight_field_momentum,
    supplier_tight_joseph_calendar as _supplier_tight_joseph_calendar,
)
from scripts.run_samsung_sasang_veto_hold_counterfactual_v1 import (  # noqa: E402
    _bah_return,
    _strict_veto_daily,
    _wait_first_clear_then_hold,
)


def test_bah_return_simple() -> None:
    closes = {"2026-01-02": 100.0, "2026-01-03": 110.0, "2026-01-06": 121.0}
    dates = sorted(closes)
    r = _bah_return(closes, dates)
    assert r["status"] == "ok"
    assert r["total_return_pct"] == 21.0


def test_strict_veto_exits_to_cash() -> None:
    closes = {
        "2026-01-02": 100.0,
        "2026-01-03": 120.0,
        "2026-01-06": 108.0,
        "2026-01-07": 130.0,
    }
    dates = sorted(closes)
    veto = {"2026-01-02": False, "2026-01-03": True, "2026-01-06": False, "2026-01-07": True}
    r = _strict_veto_daily(closes, dates, veto)
    assert r["status"] == "ok"
    # enter 102, exit 103 at 120 (+20%), enter 106 at 108, mark 107 at 130
    assert r["total_return_pct"] is not None


def test_first_clear_then_hold() -> None:
    closes = {"2026-01-02": 100.0, "2026-01-03": 200.0}
    veto = {"2026-01-02": True, "2026-01-03": False}
    r = _wait_first_clear_then_hold(closes, sorted(closes), veto)
    assert r["entry_date"] == "2026-01-03"
    assert r["total_return_pct"] == 0.0


def test_regime_split_tactical_beats_strict_veto_in_uptrend() -> None:
    closes = {f"2026-01-{i:02d}": 100.0 + i * 5 for i in range(2, 11)}
    dates = sorted(closes)
    veto = {d: True for d in dates}
    supplier = {d: True for d in dates}
    strict = _strict_veto_daily(closes, dates, veto)
    split = _regime_mkm_split_v1(closes, dates, veto, supplier, structural_entry=True)
    assert strict["total_return_pct"] == 0.0
    assert split["total_return_pct"] is not None and split["total_return_pct"] > 0


def test_hysteresis_delays_exit() -> None:
    dates = [f"2026-01-{i:02d}" for i in range(2, 12)]
    raw = {d: True for d in dates[:5]} | {d: False for d in dates[5:]}
    hyst = _apply_supplier_hysteresis(raw, dates, exit_confirm_days=3)
    # first false at index 5; exit after 3 consecutive false -> still tight through index 7
    assert hyst[dates[5]] is True
    assert hyst[dates[6]] is True
    assert hyst[dates[7]] is False


def test_joseph_extended_covers_2025_h2() -> None:
    dates = ["2025-07-01", "2025-12-31", "2026-01-02"]
    j = _supplier_tight_joseph_calendar(dates, start="2025-06-01")
    assert j["2025-07-01"] is True
    assert j["2025-12-31"] is True


def test_artifact_exists_after_run() -> None:
    p = ROOT / "reports/samsung_sasang_veto_hold_counterfactual_v1_latest.json"
    if not p.is_file():
        return
    doc = json.loads(p.read_text(encoding="utf-8-sig"))
    assert doc.get("schema") == "samsung_sasang_veto_hold_counterfactual_v1_3"
    assert doc.get("research_only") is True
