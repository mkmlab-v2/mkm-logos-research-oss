from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_build_lens_penalty_s1_promotion_review_packet_v1(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    script = repo / "scripts" / "build_lens_penalty_s1_promotion_review_packet_v1.py"

    weekly = tmp_path / "weekly.json"
    fail_reason = tmp_path / "fail_reason.json"
    sweep = tmp_path / "sweep.json"
    comparator = tmp_path / "comparator.json"
    gate = tmp_path / "gate.json"
    streak = tmp_path / "streak.json"
    out = tmp_path / "packet.json"

    weekly.write_text(json.dumps({"summary": {"strict_gap": 0.1}}), encoding="utf-8")
    fail_reason.write_text(json.dumps({"summary": {"top_reason_code": "DIRECTION_MISMATCH"}}), encoding="utf-8")
    sweep.write_text(json.dumps({"summary": {"flip_candidates": 2}}), encoding="utf-8")
    comparator.write_text(json.dumps({"summary": {"simulated_strict_gap": -0.2, "flip_candidates": 2}}), encoding="utf-8")
    gate.write_text(json.dumps({"decision": "GO_REVIEW"}), encoding="utf-8")
    streak.write_text(json.dumps({"decision": "READY_FOR_COMMANDER_REVIEW", "snapshot": {"current_go_streak": 3}}), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(script),
            "--weekly-json",
            str(weekly),
            "--fail-reason-json",
            str(fail_reason),
            "--sweep-json",
            str(sweep),
            "--comparator-json",
            str(comparator),
            "--gate-json",
            str(gate),
            "--streak-json",
            str(streak),
            "--out",
            str(out),
        ],
        check=True,
        cwd=repo,
    )

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["decision_hint"] == "READY_FOR_COMMANDER_REVIEW"
    assert payload["summary"]["streak_go_days"] == 3
