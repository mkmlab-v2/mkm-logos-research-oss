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


def _lens_wf_passing() -> dict:
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


def _instrument_wf_passing() -> dict:
    return {
        "schema": "prophecy_instrument_combo_walkforward_v1",
        "aggregate": {
            "mean_test_accuracy": 0.61,
            "stdev_test_accuracy": 0.06,
            "min_test_accuracy": 0.54,
            "max_test_accuracy": 0.67,
            "fraction_test_beats_always_bull": 0.75,
        },
        "folds": [{"fold_index": 0}, {"fold_index": 1}, {"fold_index": 2}, {"fold_index": 3}],
        "inputs": {},
    }


def test_promotion_gates_all_pass_skip_shared(tmp_path: Path) -> None:
    ws = Path(__file__).resolve().parents[1]
    lens = tmp_path / "lens.json"
    inst = tmp_path / "inst.json"
    lens.write_text(json.dumps(_lens_wf_passing()), encoding="utf-8")
    inst.write_text(json.dumps(_instrument_wf_passing()), encoding="utf-8")
    out = tmp_path / "gates.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ws / "scripts" / "eval_prophecy_promotion_gates_v1.py"),
            "--lens-walkforward-json",
            str(lens),
            "--instrument-walkforward-json",
            str(inst),
            "--skip-shared-gates",
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
    assert doc.get("combined_all_passed") is True
    assert doc.get("tracks", {}).get("per_date_lens", {}).get("all_gates_passed") is True
    assert doc.get("tracks", {}).get("instrument_combo", {}).get("all_gates_passed") is True


def test_promotion_gates_walkforward_json_alias(tmp_path: Path) -> None:
    ws = Path(__file__).resolve().parents[1]
    lens = tmp_path / "lens2.json"
    inst = tmp_path / "inst2.json"
    lens.write_text(json.dumps(_lens_wf_passing()), encoding="utf-8")
    inst.write_text(json.dumps(_instrument_wf_passing()), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(ws / "scripts" / "eval_prophecy_promotion_gates_v1.py"),
            "--walkforward-json",
            str(lens),
            "--instrument-walkforward-json",
            str(inst),
            "--skip-shared-gates",
            "--stdout-only",
        ],
        cwd=str(ws),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout


def test_promotion_gates_fail_on_gate_exit_code(tmp_path: Path) -> None:
    ws = Path(__file__).resolve().parents[1]
    wf = _lens_wf_passing()
    wf["aggregate"]["mean_test_accuracy"] = 0.3
    lens = tmp_path / "lens3.json"
    inst = tmp_path / "inst3.json"
    lens.write_text(json.dumps(wf), encoding="utf-8")
    inst.write_text(json.dumps(_instrument_wf_passing()), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(ws / "scripts" / "eval_prophecy_promotion_gates_v1.py"),
            "--lens-walkforward-json",
            str(lens),
            "--instrument-walkforward-json",
            str(inst),
            "--skip-shared-gates",
            "--stdout-only",
            "--fail-on-gate",
        ],
        cwd=str(ws),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1


def test_shared_gates_detect_incomplete_panel(tmp_path: Path) -> None:
    ws = Path(__file__).resolve().parents[1]
    lens = tmp_path / "lens4.json"
    inst = tmp_path / "inst4.json"
    lens.write_text(json.dumps(_lens_wf_passing()), encoding="utf-8")
    inst.write_text(json.dumps(_instrument_wf_passing()), encoding="utf-8")
    score_path = tmp_path / "score.json"
    score_path.write_text(
        json.dumps(
            {
                "inputs": {"btc_csv": "research/market_data/btc_daily_external_yf.csv"},
                "rows": [
                    {
                        "instrument": "kospi",
                        "eval_date": "2026-01-10",
                        "actual_direction": "bull",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(ws / "scripts" / "eval_prophecy_promotion_gates_v1.py"),
            "--lens-walkforward-json",
            str(lens),
            "--instrument-walkforward-json",
            str(inst),
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
    assert doc.get("combined_all_passed") is False
    assert doc.get("tracks", {}).get("shared", {}).get("all_gates_passed") is False
