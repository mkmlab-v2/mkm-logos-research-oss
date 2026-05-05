from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "enforce_agct_sasang_holdout_runtime_guard_v1.py"


def test_guard_disables_runtime_on_holdout_fail(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime.json"
    runtime.write_text(
        json.dumps(
            {
                "schema": "agct_sasang_size_overlay_runtime_stub_v1",
                "runtime_stub": {
                    "enabled": True,
                    "status": "READY_FOR_SHADOW",
                    "multipliers": {"low_risk": 0.95, "neutral": 0.85, "high_risk": 0.7},
                },
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    holdout = tmp_path / "holdout.json"
    holdout.write_text(
        json.dumps(
            {
                "schema": "agct_sasang_holdout_eval_v1",
                "split": {"holdout_n": 5},
                "results": {
                    "holdout_accuracy_under_train_mapping": 0.30,
                    "generalization_gap": 0.60,
                    "holdout_accuracy_permutation_p_value": 0.80,
                },
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--runtime-stub-json",
            str(runtime),
            "--holdout-eval-json",
            str(holdout),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(runtime.read_text(encoding="utf-8"))
    assert doc["runtime_stub"]["enabled"] is False
    assert doc["runtime_stub"]["status"] == "HOLD_BY_GENERALIZATION_GUARD"
    assert doc["holdout_runtime_guard_v1"]["guard_pass"] is False
    assert doc["holdout_runtime_guard_v1"]["checks"]["holdout_sample_size_gate"] is False


def test_guard_preserves_enabled_when_holdout_pass(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime.json"
    runtime.write_text(
        json.dumps(
            {
                "schema": "agct_sasang_size_overlay_runtime_stub_v1",
                "runtime_stub": {
                    "enabled": True,
                    "status": "READY_FOR_SHADOW",
                    "multipliers": {"low_risk": 0.95, "neutral": 0.85, "high_risk": 0.7},
                },
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    holdout = tmp_path / "holdout.json"
    holdout.write_text(
        json.dumps(
            {
                "schema": "agct_sasang_holdout_eval_v1",
                "split": {"holdout_n": 60},
                "results": {
                    "holdout_accuracy_under_train_mapping": 1.0,
                    "generalization_gap": 0.0,
                    "holdout_accuracy_permutation_p_value": 0.05,
                },
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--runtime-stub-json",
            str(runtime),
            "--holdout-eval-json",
            str(holdout),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(runtime.read_text(encoding="utf-8"))
    assert doc["runtime_stub"]["enabled"] is True
    assert doc["holdout_runtime_guard_v1"]["guard_pass"] is True
    assert doc["holdout_runtime_guard_v1"]["checks"]["holdout_sample_size_gate"] is True
