# @MKM12-METADATA
# Type: Logic
# Purpose: Validate ultra compression KPI summary contract.
# Keywords: ultra-compression, kpi, summary, hydration-mix

from __future__ import annotations

import json
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_SUMMARY = _ROOT / "reports" / "constitution" / "btrack_pilot" / "ultra_compression_kpi_summary_latest.json"


def _load(path: Path) -> dict:
    assert path.is_file(), f"missing artifact: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def test_ultra_compression_kpi_summary_contract() -> None:
    d = _load(_SUMMARY)
    assert d.get("schema") == "ultra_compression_kpi_summary_v1"
    decision = d.get("decision", {})
    assert decision.get("go_no_go") in {"GO", "NO_GO"}
    assert decision.get("rollout_policy") in {"global_default", "domain_variable_cap"}
    active = d.get("active_kpi", {})
    assert 0.0 <= float(active.get("global_token_saving_rate", -1)) <= 1.0
    assert 0.0 <= float(active.get("avg_reconstruction_fidelity_jaccard", -1)) <= 1.0
    assert 0.0 <= float(active.get("avg_sensitive_integrity", -1)) <= 1.0
    assert active.get("bench_saving_floor_min") == 0.47
    assert isinstance(active.get("bench_saving_floor_ok"), bool)
    lit = d.get("literal_kpi")
    if lit is not None and isinstance(lit, dict):
        assert 0.0 <= float(lit.get("global_token_saving_rate") or 0.0) <= 1.0
        assert 0.0 <= float(lit.get("avg_reconstruction_fidelity_jaccard") or 0.0) <= 1.0
        assert 0.0 <= float(lit.get("avg_sensitive_integrity") or 0.0) <= 1.0
    ultra = d.get("ultra_literal_kpi")
    if ultra is not None and isinstance(ultra, dict):
        assert 0.0 <= float(ultra.get("global_token_saving_rate") or 0.0) <= 1.0
        assert 0.0 <= float(ultra.get("avg_reconstruction_fidelity_jaccard") or 0.0) <= 1.0
        assert 0.0 <= float(ultra.get("avg_sensitive_integrity") or 0.0) <= 1.0
    perf = d.get("performance", {})
    assert float(perf.get("bench_total_elapsed_ms", -1)) >= 0.0
    assert int(perf.get("round2_full_grid_count", 0)) >= int(perf.get("round2_evaluated_count", 0)) >= 0
    hyd = d.get("api_hydration_mix", {})
    assert int(hyd.get("total_examples", 0)) >= 0
    live_ratio = float(hyd.get("live_ratio", -1))
    assert 0.0 <= live_ratio <= 1.0
