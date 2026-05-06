from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_one_plus_three_warning_critical_gate_v1.py"
POLICY = ROOT / "docs" / "final" / "artifacts" / "one_plus_three_threshold_policy_v1.json"


def _run(metrics: dict, tmp_path: Path) -> dict:
    metrics_path = tmp_path / "metrics.json"
    output_path = tmp_path / "decision.json"
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--metrics-json",
            str(metrics_path),
            "--policy-json",
            str(POLICY),
            "--output",
            str(output_path),
        ],
        check=True,
        cwd=ROOT,
    )
    return json.loads(output_path.read_text(encoding="utf-8"))


def test_gate_ok(tmp_path: Path) -> None:
    out = _run(
        {
            "schema": "one_plus_three_window_metrics_v1",
            "window_7d_metrics": {"warning_signal_count": 0, "degradation_ratio": 0.01, "hold_event_count": 0},
            "window_14d_metrics": {"critical_violation_count": 0, "core_failure_count": 0, "degradation_ratio": 0.05},
            "latest_gate_state": {"gate_level": "ok"},
            "emergency_stop": False,
        },
        tmp_path,
    )
    assert out["gate_level"] == "ok"


def test_gate_warning(tmp_path: Path) -> None:
    out = _run(
        {
            "schema": "one_plus_three_window_metrics_v1",
            "window_7d_metrics": {"warning_signal_count": 2, "degradation_ratio": 0.03, "hold_event_count": 0},
            "window_14d_metrics": {"critical_violation_count": 0, "core_failure_count": 0, "degradation_ratio": 0.04},
            "latest_gate_state": {"gate_level": "ok"},
            "emergency_stop": False,
        },
        tmp_path,
    )
    assert out["gate_level"] == "warning"
    assert "warning_signal_count_7d_threshold" in out["reason_codes"]


def test_gate_critical(tmp_path: Path) -> None:
    out = _run(
        {
            "schema": "one_plus_three_window_metrics_v1",
            "window_7d_metrics": {"warning_signal_count": 1, "degradation_ratio": 0.05, "hold_event_count": 0},
            "window_14d_metrics": {"critical_violation_count": 1, "core_failure_count": 0, "degradation_ratio": 0.06},
            "latest_gate_state": {"gate_level": "warning"},
            "emergency_stop": False,
        },
        tmp_path,
    )
    assert out["gate_level"] == "critical"
    assert "critical_violation_count_14d_threshold" in out["reason_codes"]
