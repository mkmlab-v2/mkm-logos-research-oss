from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_build_lens_penalty_s1_manual_signoff_worksheet_v1_ready(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    script = repo / "scripts" / "build_lens_penalty_s1_manual_signoff_worksheet_v1.py"

    gate = tmp_path / "gate.json"
    streak = tmp_path / "streak.json"
    packet = tmp_path / "packet.json"
    apply_ck = tmp_path / "apply.json"
    out = tmp_path / "worksheet.json"

    gate.write_text(
        json.dumps({"decision": "GO_REVIEW", "constraints": {"human_review_required": True, "auto_apply_enabled": False}}),
        encoding="utf-8",
    )
    streak.write_text(
        json.dumps({"decision": "READY_FOR_COMMANDER_REVIEW", "snapshot": {"current_go_streak": 2}}),
        encoding="utf-8",
    )
    packet.write_text(
        json.dumps(
            {
                "decision_hint": "READY_FOR_COMMANDER_REVIEW",
                "summary": {"weekly_strict_gap": 0.2, "simulated_strict_gap": -0.3, "flip_candidates": 2},
            }
        ),
        encoding="utf-8",
    )
    apply_ck.write_text(json.dumps({"decision": "HOLD_SHADOW_CONTINUE"}), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(script),
            "--gate-json",
            str(gate),
            "--streak-json",
            str(streak),
            "--packet-json",
            str(packet),
            "--apply-checklist-json",
            str(apply_ck),
            "--out",
            str(out),
        ],
        check=True,
        cwd=repo,
    )

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["schema"] == "lens_penalty_s1_manual_signoff_worksheet_v1"
    assert payload["decision"] == "READY_FOR_COMMANDER_SIGNOFF"
    assert payload["all_green"] is True
