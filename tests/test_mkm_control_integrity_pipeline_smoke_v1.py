"""Smoke tests for MKM control-integrity aggregate / inference oracle / promotion gate (no GPU)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]

_AGG = _ROOT / "scripts" / "aggregate_mkm_control_integrity_eval_holdout_v1.py"
_INF = _ROOT / "scripts" / "run_mkm_control_integrity_inference_batch_v1.py"
_EVAL = _ROOT / "scripts" / "evaluate_mkm_control_integrity_lora_predictions_v1.py"
_GATE = _ROOT / "scripts" / "check_mkm_control_integrity_promotion_gate_v1.py"
_SPLIT_TEST = _ROOT / "data" / "training" / "mkm_control_integrity_lora_splits_v1" / "test.jsonl"


def _minimal_eval_report(ok: bool = True, rows: int = 10, row_pass: float = 0.8) -> dict:
    return {
        "ok": ok,
        "summary": {
            "rows_total": rows,
            "row_pass_rate": row_pass,
            "must_include_pass_rate": 0.9,
            "coverage_rate": 1.0,
        },
    }


def test_aggregate_holdout_merge_cli_exits_zero(tmp_path: Path) -> None:
    assert _AGG.is_file()
    paths = []
    for i in range(3):
        p = tmp_path / f"eval_{i}.json"
        p.write_text(json.dumps(_minimal_eval_report(), ensure_ascii=False), encoding="utf-8")
        paths.append(p)
    out = tmp_path / "merged_holdout.json"
    cmd = [
        sys.executable,
        str(_AGG),
        "--inputs",
        ",".join(str(p) for p in paths),
        "--profile-label",
        "pytest",
        "--out",
        str(out),
    ]
    proc = subprocess.run(cmd, cwd=str(_ROOT), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "mkm_control_integrity_lora_eval_holdout_suite_v1"
    assert doc.get("ok") is True
    assert doc["summary"]["rows_total"] == 30


@pytest.mark.skipif(not _SPLIT_TEST.is_file(), reason="LoRA split JSONL not present")
def test_inference_oracle_emit_timing(tmp_path: Path) -> None:
    assert _INF.is_file()
    pred = tmp_path / "pred_smoke.jsonl"
    cmd = [
        sys.executable,
        str(_INF),
        "--oracle",
        "--in",
        str(_SPLIT_TEST),
        "--out",
        str(pred),
        "--limit",
        "4",
        "--emit-timing",
    ]
    proc = subprocess.run(cmd, cwd=str(_ROOT), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    timing = tmp_path / "pred_smoke_timing.json"
    assert timing.is_file()
    doc = json.loads(timing.read_text(encoding="utf-8"))
    assert doc.get("schema") == "mkm_control_integrity_inference_timing_v1"
    assert doc["stats_ms"]["count"] == 4


def test_promotion_gate_holdout_only_locked_pass(tmp_path: Path) -> None:
    assert _GATE.is_file()
    holdout = {
        "summary": {"row_pass_rate_weighted": 0.95},
        "by_split": {
            "locked_eval": {"summary": {"row_pass_rate": 0.96}},
        },
    }
    hp = tmp_path / "holdout.json"
    hp.write_text(json.dumps(holdout), encoding="utf-8")
    cmd = [
        sys.executable,
        str(_GATE),
        "--holdout-only",
        "--holdout-report",
        str(hp),
        "--min-locked-eval-pass-rate",
        "0.5",
        "--min-holdout-row-pass-weighted",
        "0.5",
    ]
    proc = subprocess.run(cmd, cwd=str(_ROOT), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr + proc.stdout


def test_promotion_gate_holdout_only_locked_fail(tmp_path: Path) -> None:
    holdout = {
        "summary": {"row_pass_rate_weighted": 0.95},
        "by_split": {
            "locked_eval": {"summary": {"row_pass_rate": 0.2}},
        },
    }
    hp = tmp_path / "holdout.json"
    hp.write_text(json.dumps(holdout), encoding="utf-8")
    cmd = [
        sys.executable,
        str(_GATE),
        "--holdout-only",
        "--holdout-report",
        str(hp),
        "--min-locked-eval-pass-rate",
        "0.5",
    ]
    proc = subprocess.run(cmd, cwd=str(_ROOT), capture_output=True, text=True, check=False)
    assert proc.returncode == 2


def test_evaluate_allow_missing_partial_rows(tmp_path: Path) -> None:
    assert _EVAL.is_file()
    golden = tmp_path / "golden.jsonl"
    golden.write_text(
        '{"sample_id":"x1","split":"test","expected_response":"ok","must_include":["ok"],"must_not_include":[]}\n'
        '{"sample_id":"x2","split":"test","expected_response":"no","must_include":["no"],"must_not_include":[]}\n',
        encoding="utf-8",
    )
    pred = tmp_path / "pred.jsonl"
    pred.write_text('{"id":"x1","prediction":"ok done"}\n', encoding="utf-8")
    out = tmp_path / "report.json"
    cmd = [
        sys.executable,
        str(_EVAL),
        "--golden",
        str(golden),
        "--predictions",
        str(pred),
        "--splits",
        "test",
        "--report-out",
        str(out),
        "--allow-missing-predictions",
    ]
    proc = subprocess.run(cmd, cwd=str(_ROOT), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["summary"]["rows_with_prediction"] == 1
    assert doc["summary"]["subset_scoring"] is True
    assert doc["ok"] is True


def test_evaluate_missing_strict_exits_2(tmp_path: Path) -> None:
    golden = tmp_path / "golden.jsonl"
    golden.write_text(
        '{"sample_id":"x1","split":"test","expected_response":"ok","must_include":["ok"],"must_not_include":[]}\n'
        '{"sample_id":"x2","split":"test","expected_response":"no","must_include":["no"],"must_not_include":[]}\n',
        encoding="utf-8",
    )
    pred = tmp_path / "pred.jsonl"
    pred.write_text('{"id":"x1","prediction":"ok done"}\n', encoding="utf-8")
    out = tmp_path / "report.json"
    cmd = [
        sys.executable,
        str(_EVAL),
        "--golden",
        str(golden),
        "--predictions",
        str(pred),
        "--splits",
        "test",
        "--report-out",
        str(out),
    ]
    proc = subprocess.run(cmd, cwd=str(_ROOT), capture_output=True, text=True, check=False)
    assert proc.returncode == 2
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["ok"] is False
    assert any("missing prediction" in e for e in doc["errors"])


def test_promotion_gate_comparison_missing_exits_1() -> None:
    cmd = [
        sys.executable,
        str(_GATE),
        "--comparison",
        str(_ROOT / "reports" / "nonexistent_comparison_xyz.json"),
    ]
    proc = subprocess.run(cmd, cwd=str(_ROOT), capture_output=True, text=True, check=False)
    assert proc.returncode == 1
