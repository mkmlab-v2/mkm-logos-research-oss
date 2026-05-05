# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.8, K:0.3, M:0.5}
# Balance: 89
# Purpose: Regression tests for promotion-vs-directional semantic separation checks.
# Keywords: pytest, smoke-check, promotion-gate, logos, semantics
from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_promotion_directional_semantic_separation_v1.py"


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_semantic_separation_allows_go_live_with_logos_directional_false(tmp_path: Path) -> None:
    decision_path = tmp_path / "decision.json"
    summary_path = tmp_path / "summary.json"
    output_path = tmp_path / "out.json"

    _write_json(
        decision_path,
        {"checks_passed": True, "thresholds_passed": True, "final_decision": "GO_LIVE_CANDIDATE"},
    )
    _write_json(
        summary_path,
        {"findings": {"logos_directional_viable_under_current_setup": False}},
    )

    proc = subprocess.run(
        [
            "py",
            str(SCRIPT),
            "--decision-json",
            str(decision_path),
            "--summary-json",
            str(summary_path),
            "--output",
            str(output_path),
            "--strict",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr

    out = json.loads(output_path.read_text(encoding="utf-8-sig"))
    checks = out.get("checks") or {}
    assert checks.get("semantic_separation_ok") is True
    assert checks.get("non_conflation_confirmed") is True


def test_semantic_separation_fails_when_logos_viability_missing_in_strict_mode(tmp_path: Path) -> None:
    decision_path = tmp_path / "decision.json"
    summary_path = tmp_path / "summary.json"
    output_path = tmp_path / "out.json"

    _write_json(
        decision_path,
        {"checks_passed": True, "thresholds_passed": True, "final_decision": "GO_LIVE_CANDIDATE"},
    )
    _write_json(summary_path, {"findings": {}})

    proc = subprocess.run(
        [
            "py",
            str(SCRIPT),
            "--decision-json",
            str(decision_path),
            "--summary-json",
            str(summary_path),
            "--output",
            str(output_path),
            "--strict",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1, proc.stdout + proc.stderr

