from __future__ import annotations

from pathlib import Path


def test_run_truthfulqa_repro_bundle_script_present() -> None:
    p = Path("scripts/Run-TruthfulQAReproBundleV1.ps1")
    text = p.read_text(encoding="utf-8")
    assert "run_truthfulqa_ab_benchmark_v1.py" in text
    assert "check_truthfulqa_ab_gate_v1.py" in text
    assert "RunGeneration" in text
    assert "truthfulqa_mc_evalset_latest.jsonl" in text
    assert "truthfulqa_ab_gate_latest.json" in text
