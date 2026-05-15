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
            "--promotion-track-mode",
            "dual",
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
            "--promotion-track-mode",
            "dual",
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


def test_btc_only_mode_ignores_dual_leg_panel_gate(tmp_path: Path) -> None:
    ws = Path(__file__).resolve().parents[1]
    lens = tmp_path / "lens5.json"
    inst = tmp_path / "inst5.json"
    lens.write_text(json.dumps(_lens_wf_passing()), encoding="utf-8")
    inst.write_text(json.dumps(_instrument_wf_passing()), encoding="utf-8")
    score_path = tmp_path / "score_btc_only.json"
    score_path.write_text(
        json.dumps(
            {
                "inputs": {"btc_csv": "research/market_data/btc_daily_external_yf.csv"},
                "rows": [
                    {"instrument": "kospi", "eval_date": "2026-01-10", "actual_direction": "bull"},
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
            "--promotion-track-mode",
            "btc_only_crossassist",
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
    assert doc.get("tracks", {}).get("shared", {}).get("all_gates_passed") is True
    assert doc.get("instrument_combo_all_gates_passed") is None
    assert doc.get("combined_all_passed") is True


def test_dual_soft_band_review_when_strict_fails(tmp_path: Path) -> None:
    ws = Path(__file__).resolve().parents[1]
    streak = tmp_path / "streak_sb.json"
    streak.write_text(json.dumps({"schema": "prophecy_promotion_strict_streak_v1", "runs": []}), encoding="utf-8")
    lens = tmp_path / "lens_sb.json"
    inst = tmp_path / "inst_sb.json"
    lw = _lens_wf_passing()
    lw["aggregate"]["mean_test_accuracy"] = 0.50
    iw = _instrument_wf_passing()
    iw["aggregate"]["mean_test_accuracy"] = 0.50
    iw["aggregate"]["fraction_test_beats_always_bull"] = 0.30
    lens.write_text(json.dumps(lw), encoding="utf-8")
    inst.write_text(json.dumps(iw), encoding="utf-8")
    out = tmp_path / "gates_sb.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ws / "scripts" / "eval_prophecy_promotion_gates_v1.py"),
            "--lens-walkforward-json",
            str(lens),
            "--instrument-walkforward-json",
            str(inst),
            "--promotion-track-mode",
            "dual",
            "--skip-shared-gates",
            "--streak-history-json",
            str(streak),
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
    assert doc.get("combined_all_passed") is False
    assert doc.get("lens_soft_passed") is True
    assert doc.get("instrument_soft_passed") is True
    assert doc.get("soft_passed") is True
    assert doc.get("promotion_recommendation") == "soft_band_review"


def test_dual_soft_fails_when_instrument_below_soft_beat_bull(tmp_path: Path) -> None:
    ws = Path(__file__).resolve().parents[1]
    streak = tmp_path / "streak_sb2.json"
    streak.write_text(json.dumps({"schema": "prophecy_promotion_strict_streak_v1", "runs": []}), encoding="utf-8")
    lens = tmp_path / "lens_sb2.json"
    inst = tmp_path / "inst_sb2.json"
    lw = _lens_wf_passing()
    lw["aggregate"]["mean_test_accuracy"] = 0.50
    iw = _instrument_wf_passing()
    iw["aggregate"]["mean_test_accuracy"] = 0.50
    iw["aggregate"]["fraction_test_beats_always_bull"] = 0.10
    lens.write_text(json.dumps(lw), encoding="utf-8")
    inst.write_text(json.dumps(iw), encoding="utf-8")
    out = tmp_path / "gates_sb2.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ws / "scripts" / "eval_prophecy_promotion_gates_v1.py"),
            "--lens-walkforward-json",
            str(lens),
            "--instrument-walkforward-json",
            str(inst),
            "--promotion-track-mode",
            "dual",
            "--skip-shared-gates",
            "--streak-history-json",
            str(streak),
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
    assert doc.get("instrument_soft_passed") is False
    assert doc.get("soft_passed") is False
    assert doc.get("promotion_recommendation") == "defer"
    assert doc.get("outcome_class") == "reject"
    tax = doc.get("gate_taxonomy") or {}
    assert tax.get("schema") == "prophecy_gate_taxonomy_v1"
    assert tax.get("outcome_class") == "reject"


def test_outcome_class_neutral_bucket_on_defer_and_high_neutral(tmp_path: Path) -> None:
    ws = Path(__file__).resolve().parents[1]
    lens = tmp_path / "lens_nb.json"
    inst = tmp_path / "inst_nb.json"
    score = tmp_path / "score_nb.json"
    streak = tmp_path / "streak_nb.json"
    streak.write_text(json.dumps({"schema": "prophecy_promotion_strict_streak_v1", "runs": []}), encoding="utf-8")
    lw = _lens_wf_passing()
    lw["aggregate"]["mean_test_accuracy"] = 0.40
    iw = _instrument_wf_passing()
    iw["aggregate"]["mean_test_accuracy"] = 0.40
    lens.write_text(json.dumps(lw), encoding="utf-8")
    inst.write_text(json.dumps(iw), encoding="utf-8")
    score.write_text(
        json.dumps(
            {
                "rows": [
                    {"predicted_direction": "neutral", "actual_direction": "bull"},
                    {"predicted_direction": "neutral", "actual_direction": "bear"},
                    {"predicted_direction": "bull", "actual_direction": "bull"},
                ],
                "inputs": {"btc_csv": "research/market_data/btc.csv"},
            }
        ),
        encoding="utf-8",
    )
    hypo = tmp_path / "hypo.json"
    hypo.write_text(
        json.dumps({"provenance": {"model": "test", "stub": False}}),
        encoding="utf-8",
    )
    out = tmp_path / "gates_nb.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ws / "scripts" / "eval_prophecy_promotion_gates_v1.py"),
            "--lens-walkforward-json",
            str(lens),
            "--instrument-walkforward-json",
            str(inst),
            "--score-json",
            str(score),
            "--hypothesis-json",
            str(hypo),
            "--promotion-track-mode",
            "dual",
            "--max-neutral-ratio",
            "0.5",
            "--streak-history-json",
            str(streak),
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
    assert doc.get("promotion_recommendation") == "defer"
    assert doc.get("outcome_class") == "neutral_bucket"
