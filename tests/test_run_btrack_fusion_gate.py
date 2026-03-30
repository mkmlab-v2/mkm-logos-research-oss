from __future__ import annotations

import json
import sys
from pathlib import Path

from scripts.run_btrack_fusion_gate import main


def test_run_btrack_fusion_gate_generates_report(tmp_path: Path) -> None:
    out = tmp_path / "btrack_fusion_gate_latest.json"
    risk_log = tmp_path / "fusion_gate_risk_log.jsonl"
    evidence_todo = tmp_path / "fusion_gate_evidence_todo_latest.json"
    old = sys.argv
    try:
        sys.argv = [
            "run_btrack_fusion_gate.py",
            "--out",
            str(out),
            "--risk-log",
            str(risk_log),
            "--evidence-todo",
            str(evidence_todo),
            "--min-cee-consensus-rate",
            "0.50",
            "--min-cee-mean-margin",
            "0.0005",
            "--max-cee-risk-band",
            "critical_thin",
        ]
        rc = main()
    finally:
        sys.argv = old
    assert rc == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["schema"] == "btrack_fusion_gate_v1"
    assert payload["decision"] in {"pass", "fail"}
    assert "metrics" in payload
    assert "risk_log_path" in payload
    assert payload["metrics"]["master_atoms_unique"] is not None
    assert payload["metrics"]["master_atoms_lemma_method"] in {"normalized_form_v1", "heuristic_lemma_v2"}
    assert payload["metrics"]["recommended_action"] in {
        "enforce_hard_gate_and_collect_direct_witness",
        "collect_more_evidence",
        "monitor",
        "stable_continue",
    }
    if payload["metrics"]["recommended_action"] in {
        "enforce_hard_gate_and_collect_direct_witness",
        "collect_more_evidence",
    }:
        todo_path = payload.get("evidence_todo_path")
        assert isinstance(todo_path, str) and todo_path
        assert Path(todo_path).is_file()


def test_run_btrack_fusion_gate_fails_on_strict_risk_band(tmp_path: Path) -> None:
    out = tmp_path / "btrack_fusion_gate_latest_strict.json"
    risk_log = tmp_path / "fusion_gate_risk_log.jsonl"
    evidence_todo = tmp_path / "fusion_gate_evidence_todo_latest.json"
    old = sys.argv
    try:
        sys.argv = [
            "run_btrack_fusion_gate.py",
            "--out",
            str(out),
            "--risk-log",
            str(risk_log),
            "--evidence-todo",
            str(evidence_todo),
            "--min-cee-consensus-rate",
            "0.50",
            "--min-cee-mean-margin",
            "0.0005",
            "--min-master-atoms",
            "1",
            "--min-master-hebrew-atoms",
            "1",
            "--min-master-greek-atoms",
            "1",
            "--max-cee-risk-band",
            "medium",
        ]
        rc = main()
    finally:
        sys.argv = old
    assert rc == 1
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["decision"] == "fail"
    assert any("risk band above max" in msg for msg in payload.get("failures", []))


def test_run_btrack_fusion_gate_enforces_thin_streak(tmp_path: Path) -> None:
    out = tmp_path / "btrack_fusion_gate_latest_streak.json"
    risk_log = tmp_path / "fusion_gate_risk_log.jsonl"
    evidence_todo = tmp_path / "fusion_gate_evidence_todo_latest.json"
    # Preload 9 thin-margin entries to force a 10th-alert on this run.
    with risk_log.open("w", encoding="utf-8") as f:
        for _ in range(9):
            f.write(json.dumps({"cee_mean_lambda_margin": 0.0009}) + "\n")

    old = sys.argv
    try:
        sys.argv = [
            "run_btrack_fusion_gate.py",
            "--out",
            str(out),
            "--risk-log",
            str(risk_log),
            "--evidence-todo",
            str(evidence_todo),
            "--min-cee-consensus-rate",
            "0.50",
            "--min-cee-mean-margin",
            "0.0005",
            "--min-master-atoms",
            "1",
            "--min-master-hebrew-atoms",
            "1",
            "--min-master-greek-atoms",
            "1",
            "--max-cee-risk-band",
            "critical_thin",
            "--thin-margin-threshold",
            "0.01",
            "--thin-margin-streak-limit",
            "10",
            "--enforce-thin-margin-streak",
        ]
        rc = main()
    finally:
        sys.argv = old

    assert rc == 1
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["decision"] == "fail"
    assert payload["metrics"]["cee_thin_margin_streak_alert"] is True
    assert payload["metrics"]["recommended_action"] == "enforce_hard_gate_and_collect_direct_witness"
    assert any("thin-margin streak limit reached" in msg for msg in payload.get("failures", []))
