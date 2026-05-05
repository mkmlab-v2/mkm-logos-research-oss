# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.8, K:0.3, M:0.5}
# Balance: 88
# Purpose: Validate falsification gate decision contracts.
# Keywords: pytest, gate, correlation, hold
from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_survivor_crash_falsification_gate_v1.py"


def _write_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_gate_returns_hold_when_thresholds_fail(tmp_path: Path) -> None:
    backtest = tmp_path / "backtest.json"
    out = tmp_path / "gate.json"
    _write_json(
        backtest,
        {
            "analysis": {
                "kospi": {"best_abs_corr_row": {"return_corr": 0.12, "return_n": 1000}, "best_return_corr_permutation_pvalue": 0.2},
                "btc": {"best_abs_corr_row": {"return_corr": 0.02, "return_n": 800}, "best_return_corr_permutation_pvalue": 0.7},
            }
        },
    )
    proc = subprocess.run(
        ["py", str(SCRIPT), "--backtest-json", str(backtest), "--output", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    gate = json.loads(out.read_text(encoding="utf-8-sig"))
    assert gate["result"]["decision"] == "HOLD_RESEARCH_ONLY"


def test_gate_can_pass_in_crash_objective_mode(tmp_path: Path) -> None:
    backtest = tmp_path / "backtest.json"
    out = tmp_path / "gate_crash.json"
    _write_json(
        backtest,
        {
            "analysis": {
                "kospi": {
                    "best_abs_corr_row": {
                        "return_corr": 0.01,
                        "return_n": 1000,
                        "crash_flag_corr": 0.2,
                        "crash_flag_n": 1000,
                    },
                    "best_return_corr_permutation_pvalue": 0.01,
                },
                "btc": {"best_abs_corr_row": {"return_corr": 0.01, "return_n": 1000}, "best_return_corr_permutation_pvalue": 0.9},
            }
        },
    )
    proc = subprocess.run(
        [
            "py",
            str(SCRIPT),
            "--backtest-json",
            str(backtest),
            "--output",
            str(out),
            "--objective-mode",
            "crash",
            "--min-abs-corr",
            "0.15",
            "--max-pvalue",
            "0.05",
            "--min-n",
            "250",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    gate = json.loads(out.read_text(encoding="utf-8-sig"))
    assert gate["result"]["decision"] == "GO_RESEARCH_SIGNAL_CANDIDATE"

