from __future__ import annotations

from pathlib import Path


def test_run_fact_lock_bundle_includes_truthfulqa_gate_switches() -> None:
    p = Path("scripts/run_fact_lock_bundle.ps1")
    text = p.read_text(encoding="utf-8")
    assert "IncludeTruthfulQaBenchmarkGate" in text
    assert "StrictTruthfulQaBenchmarkGate" in text
    assert "TruthfulQaEvalMcOnly" in text
    assert "TruthfulQaBenchmarkGateMcOnly" in text
    assert "--strict" in text
    assert "--mc-only" in text
    assert "truthfulqa_ab_benchmark_latest.json" in text
    assert "truthfulqa_generation_ab_benchmark_latest.json" in text
