"""A2A fixed multi-scenario dialogue bench smoke."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.build_a2a_dialogue_bench_v1 import build_bench_document

ROOT = Path(__file__).resolve().parents[1]


def test_build_bench_document_schema_and_ok():
    doc = build_bench_document(turns=2, scenarios=("trading",), include_routing_compare=False)
    assert doc["schema"] == "a2a_dialogue_bench_v1"
    assert doc["bench_ok"] is True
    assert len(doc["scenarios"]) == 1
    metrics = doc["scenarios"][0]["trust_packet_mock"]["metrics"]
    assert metrics.get("all_compress_ok") is True
    assert metrics.get("avg_savings_ratio") is not None


def test_full_three_scenario_bench_ok():
    doc = build_bench_document(turns=2, include_routing_compare=True)
    assert doc["bench_ok"] is True
    assert doc["kpi_headline"]["scenario_count"] == 3
    assert doc["routing_compare"]["health"]["compare_ok"] is True
    assert doc["routing_compare"]["trading"]["compare_ok"] is True
    assert doc["routing_compare_trading"]["recommended_routing_profile"] == "track_a_promoted"
    assert doc["kpi_headline"]["cross_scenario_mean_mock_avg_savings"] is not None
    trading = next(s for s in doc["scenarios"] if s["scenario"] == "trading")
    assert trading["trust_packet_mock"]["metrics"].get("zero_savings_turns", 99) == 0


def test_trading_scenario_meets_compress_floor():
    doc = build_bench_document(turns=4, scenarios=("trading",), include_routing_compare=False)
    metrics = doc["scenarios"][0]["trust_packet_mock"]["metrics"]
    assert metrics.get("zero_savings_turns") == 0
    assert float(metrics.get("avg_savings_ratio") or 0) >= 0.35


def test_emit_script_writes_json(tmp_path, monkeypatch):
    out = tmp_path / "bench.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "build_a2a_dialogue_bench_v1.py",
            "--turns",
            "2",
            "--scenario",
            "lexicon_dense",
            "--skip-routing-compare",
            "--out",
            str(out),
        ],
    )
    from scripts.build_a2a_dialogue_bench_v1 import main

    assert main() == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload.get("schema") == "a2a_dialogue_bench_v1"
    assert payload.get("bench_ok") is True
