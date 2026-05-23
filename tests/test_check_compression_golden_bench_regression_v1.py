"""Golden bench regression gate (shard / ultra re-eval)."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.check_compression_golden_bench_regression_v1 import _load, _metric


def test_metric_reads_active_report_shape(tmp_path: Path) -> None:
    report = {
        "compression_metrics": {
            "case_count": 40,
            "global_token_saving_rate": 0.475,
            "avg_reconstruction_fidelity_jaccard": 0.89,
            "sensitive_violation_count": 0,
        }
    }
    p = tmp_path / "active.json"
    p.write_text(json.dumps(report), encoding="utf-8")
    doc = _load(p)
    assert _metric(doc, "global_token_saving_rate") == 0.475
    assert _metric(doc, "case_count") == 40


def test_regression_script_exit_zero_on_good_report(tmp_path: Path, monkeypatch) -> None:
    import scripts.check_compression_golden_bench_regression_v1 as mod

    report = {
        "compression_metrics": {
            "case_count": 40,
            "global_token_saving_rate": 0.475,
            "avg_reconstruction_fidelity_jaccard": 0.89,
            "sensitive_violation_count": 0,
        }
    }
    active = tmp_path / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
    active.write_text(json.dumps(report), encoding="utf-8")
    out = tmp_path / "reg.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "check",
            "--active-report",
            str(active),
            "--out-json",
            str(out),
        ],
    )
    assert mod.main() == 0
    assert json.loads(out.read_text(encoding="utf-8"))["regression_ok"] is True
