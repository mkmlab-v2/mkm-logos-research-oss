# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.5, K:0.2, M:0.2}
# Balance: 92
# Purpose: Smoke tests for prophecy promotion gates script
# Keywords: pytest, prophecy, gates, promotion
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _wf_passing() -> dict:
    return {
        "schema": "prophecy_per_date_combo_walkforward_v1",
        "aggregate": {
            "mean_test_accuracy": 0.62,
            "stdev_test_accuracy": 0.05,
            "min_test_accuracy": 0.55,
            "max_test_accuracy": 0.68,
            "fraction_test_beats_always_bull": 0.75,
        },
        "folds": [{"fold_index": 0}, {"fold_index": 1}, {"fold_index": 2}, {"fold_index": 3}],
        "inputs": {},
    }


def test_promotion_gates_all_pass_skip_panel(tmp_path: Path) -> None:
    ws = Path(__file__).resolve().parents[1]
    wf_path = tmp_path / "wf.json"
    wf_path.write_text(json.dumps(_wf_passing()), encoding="utf-8")
    out = tmp_path / "gates.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ws / "scripts" / "eval_prophecy_promotion_gates_v1.py"),
            "--walkforward-json",
            str(wf_path),
            "--skip-panel-gate",
            "--output",
            str(out),
        ],
        cwd=str(ws),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "prophecy_promotion_gates_v1"
    assert doc.get("all_gates_passed") is True


def test_promotion_gates_fail_on_gate_exit_code(tmp_path: Path) -> None:
    ws = Path(__file__).resolve().parents[1]
    wf = _wf_passing()
    wf["aggregate"]["mean_test_accuracy"] = 0.3
    wf_path = tmp_path / "wf2.json"
    wf_path.write_text(json.dumps(wf), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(ws / "scripts" / "eval_prophecy_promotion_gates_v1.py"),
            "--walkforward-json",
            str(wf_path),
            "--skip-panel-gate",
            "--stdout-only",
            "--fail-on-gate",
        ],
        cwd=str(ws),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1


def test_panel_dual_leg_gate_detects_missing_btc(tmp_path: Path) -> None:
    ws = Path(__file__).resolve().parents[1]
    wf_path = tmp_path / "wf3.json"
    wf_path.write_text(json.dumps(_wf_passing()), encoding="utf-8")
    score_path = tmp_path / "score.json"
    score_path.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "instrument": "kospi",
                        "eval_date": "2026-01-10",
                        "actual_direction": "bull",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(ws / "scripts" / "eval_prophecy_promotion_gates_v1.py"),
            "--walkforward-json",
            str(wf_path),
            "--score-json",
            str(score_path),
            "--stdout-only",
        ],
        cwd=str(ws),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    doc = json.loads(proc.stdout)
    assert doc.get("all_gates_passed") is False
    panel_gates = [g for g in doc.get("gates", []) if g.get("gate_id") == "panel_kospi_btc_per_date"]
    assert len(panel_gates) == 1
    assert panel_gates[0].get("passed") is False
