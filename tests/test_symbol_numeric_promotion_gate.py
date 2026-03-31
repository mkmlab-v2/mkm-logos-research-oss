from __future__ import annotations

import json
import sys
from pathlib import Path

from scripts import build_symbol_numeric_promotion_candidates as promotion_builder
from scripts import run_btrack_symbol_lane_gate_and_lock as lane_bundle


def test_build_numeric_promotion_candidates_requires_approval(tmp_path: Path) -> None:
    input_json = tmp_path / "symbol_numeric_injection_latest.json"
    output_json = tmp_path / "numeric_promotion_candidates_latest.json"
    input_payload = {
        "schema": "symbol_numeric_injection_report_v1",
        "p1_manual_review_queue": [
            {
                "id": "q-1",
                "seed_symbol": "7",
                "candidate": "נשבע",
                "score_tfidf_like": 1.2,
                "source_mix": {"dss": 0, "apocrypha": 1},
            }
        ],
    }
    input_json.write_text(json.dumps(input_payload, ensure_ascii=False), encoding="utf-8")

    old_argv = sys.argv
    try:
        sys.argv = [
            "build_symbol_numeric_promotion_candidates.py",
            "--input-json",
            str(input_json),
            "--out-json",
            str(output_json),
        ]
        rc = promotion_builder.main()
    finally:
        sys.argv = old_argv

    assert rc == 0
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["approval"]["approved"] is False
    assert payload["stats"]["promotion_candidate_count"] == 0

    old_argv = sys.argv
    try:
        sys.argv = [
            "build_symbol_numeric_promotion_candidates.py",
            "--input-json",
            str(input_json),
            "--out-json",
            str(output_json),
            "--approval-flag",
            "approve_numeric_near_miss=true",
        ]
        rc = promotion_builder.main()
    finally:
        sys.argv = old_argv

    assert rc == 0
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["approval"]["approved"] is True
    assert payload["stats"]["promotion_candidate_count"] == 1
    assert payload["promotion_candidates"][0]["seed_symbol"] == "7"


def test_lane_bundle_forwards_numeric_approval_flag(monkeypatch) -> None:
    calls: list[list[str]] = []

    class _Proc:
        returncode = 0

    def _fake_run(cmd, cwd=None):  # type: ignore[no-untyped-def]
        calls.append(list(cmd))
        return _Proc()

    monkeypatch.setattr(lane_bundle.subprocess, "run", _fake_run)

    old_argv = sys.argv
    try:
        sys.argv = [
            "run_btrack_symbol_lane_gate_and_lock.py",
            "--approve-numeric-near-miss",
        ]
        rc = lane_bundle.main()
    finally:
        sys.argv = old_argv

    assert rc == 0
    assert len(calls) == 3
    assert calls[0][1] == "scripts/run_btrack_symbol_lane_gate.py"
    assert "--approve-numeric-near-miss" in calls[0]
