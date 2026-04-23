from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_validate_canon_singularity_outputs_v1(tmp_path: Path):
    report = tmp_path / "report.json"
    balanced = tmp_path / "balanced.json"
    summary = tmp_path / "summary.json"

    report.write_text(
        json.dumps(
            {
                "inputs": {"canon_only": True},
                "counts": {"dss_rows": 0, "apocrypha_rows": 0, "canon_rows": 10},
                "top_global_singularities": [{"lane": "canon", "score": 0.5}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    balanced.write_text(
        json.dumps(
            {
                "inputs": {"canon_only": True},
                "counts": {"dss_rows": 0, "apocrypha_rows": 0, "canon_rows": 10},
                "balanced_union_top": [{"lane": "canon", "score": 0.4}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    summary.write_text(
        json.dumps(
            {
                "schema": "original_corpus_regime_singularity_canon_lane_summary_v1",
                "counts": {"canon_rows_in_source_top": 1},
                "top_canon_global": [{"lane": "canon", "score": 0.5}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    cmd = [
        sys.executable,
        "scripts/core/validate_canon_singularity_outputs_v1.py",
        "--report-json",
        str(report),
        "--balanced-json",
        str(balanced),
        "--summary-json",
        str(summary),
        "--expected-canon-rows",
        "10",
        "--output-json",
        str(tmp_path / "gate.json"),
        "--history-jsonl",
        str(tmp_path / "history.jsonl"),
    ]
    cp = subprocess.run(cmd, check=False, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert cp.returncode == 0
    assert "OK: canon singularity outputs validated" in cp.stdout
    gate = json.loads((tmp_path / "gate.json").read_text(encoding="utf-8"))
    assert gate["schema"] == "original_corpus_regime_singularity_canon_quality_gate_v1"
    assert gate["result"] == "pass"
    hist = (tmp_path / "history.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(hist) == 1
    assert json.loads(hist[0])["result"] == "pass"


def test_validate_canon_singularity_outputs_v1_writes_fail_artifact(tmp_path: Path):
    report = tmp_path / "report.json"
    balanced = tmp_path / "balanced.json"
    summary = tmp_path / "summary.json"
    gate_path = tmp_path / "gate_fail.json"

    report.write_text(
        json.dumps(
            {
                "inputs": {"canon_only": True},
                "counts": {"dss_rows": 0, "apocrypha_rows": 0, "canon_rows": 9},
                "top_global_singularities": [{"lane": "canon", "score": 0.5}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    balanced.write_text(
        json.dumps(
            {
                "inputs": {"canon_only": True},
                "counts": {"dss_rows": 0, "apocrypha_rows": 0, "canon_rows": 9},
                "balanced_union_top": [{"lane": "canon", "score": 0.4}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    summary.write_text(
        json.dumps(
            {
                "schema": "original_corpus_regime_singularity_canon_lane_summary_v1",
                "counts": {"canon_rows_in_source_top": 1},
                "top_canon_global": [{"lane": "canon", "score": 0.5}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    cmd = [
        sys.executable,
        "scripts/core/validate_canon_singularity_outputs_v1.py",
        "--report-json",
        str(report),
        "--balanced-json",
        str(balanced),
        "--summary-json",
        str(summary),
        "--expected-canon-rows",
        "10",
        "--output-json",
        str(gate_path),
        "--history-jsonl",
        str(tmp_path / "history_fail.jsonl"),
    ]
    cp = subprocess.run(cmd, check=False, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert cp.returncode == 1
    assert "FAIL:" in cp.stderr
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    assert gate["schema"] == "original_corpus_regime_singularity_canon_quality_gate_v1"
    assert gate["result"] == "fail"
    assert "canon_rows must be 10" in gate["error"]
    hist = (tmp_path / "history_fail.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(hist) == 1
    assert json.loads(hist[0])["result"] == "fail"

