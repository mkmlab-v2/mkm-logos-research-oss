"""FinOps wire bench holdout + corpus inventory contract."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

INVENTORY = ROOT / "reports/finops_wire_corpus_inventory_v1_latest.json"
HOLDOUT = ROOT / "docs/final/artifacts/finops_wire_bench_holdout_v1_latest.json"
BENCH_V0 = ROOT / "reports/finops_wire_bench_v0_latest.json"


def test_finops_inventory_and_holdout_exist_and_primary_trading():
    inv = json.loads(INVENTORY.read_text(encoding="utf-8"))
    hold = json.loads(HOLDOUT.read_text(encoding="utf-8"))
    assert inv.get("ok") is True
    assert hold.get("ok") is True
    assert inv.get("primary_scenario") == "trading"
    assert hold.get("primary_scenario") == "trading"
    assert "trading" in hold.get("holdout_scenarios", [])
    scenarios = {r["scenario"] for r in inv.get("scenarios", [])}
    assert "trading" in scenarios
    primary = [r for r in inv.get("scenarios", []) if r.get("scenario") == "trading"][0]
    assert primary.get("finops_role") == "primary"
    assert primary.get("exists") is True


def test_finops_bench_v0_has_packet_kpi_and_disclaimer():
    bench = json.loads(BENCH_V0.read_text(encoding="utf-8"))
    assert bench.get("ok") is True
    kpis = bench.get("finops_kpis") or {}
    assert kpis.get("packet_roundtrip_ok") is True
    assert "57.9" in str(kpis.get("exact_restore_rate_global_spike", ""))
    assert bench.get("disclaimer_ko")
    assert "무손실" in bench.get("disclaimer_ko", "") or "57.9" in bench.get("disclaimer_ko", "")
