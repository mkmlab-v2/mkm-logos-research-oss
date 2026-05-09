from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_build_lens_penalty_apply_mode_checklist_v1_holds_on_high_fail_rate(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    script = repo / "scripts" / "build_lens_penalty_apply_mode_checklist_v1.py"

    daily = tmp_path / "daily.json"
    weekly = tmp_path / "weekly.json"
    state = tmp_path / "state.json"
    policy = tmp_path / "policy.json"
    out = tmp_path / "checklist.json"

    daily.write_text(
        json.dumps(
            {
                "mode": "shadow",
                "applied": False,
                "policy": {"max_daily_penalty": 0.1},
                "summary": {"lenses_evaluated": 3},
                "recommendations": [{"lens_id": "myeongni", "delta": -0.05}],
            }
        ),
        encoding="utf-8",
    )
    weekly.write_text(
        json.dumps({"summary": {"total_events": 30, "overall_fail_rate": 0.8}}),
        encoding="utf-8",
    )
    state.write_text(json.dumps({"schema": "lens_penalty_shadow_state_v1"}), encoding="utf-8")
    policy.write_text(
        json.dumps(
            {
                "schema": "lens_penalty_apply_mode_policy_v1",
                "min_weekly_events": 20,
                "max_weekly_fail_rate": 0.5,
                "human_review_required": True,
                "auto_apply_enabled": False,
            }
        ),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(script),
            "--daily-json",
            str(daily),
            "--weekly-json",
            str(weekly),
            "--state-json",
            str(state),
            "--policy-json",
            str(policy),
            "--out",
            str(out),
        ],
        check=True,
        cwd=repo,
    )

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["schema"] == "lens_penalty_apply_mode_checklist_v1"
    assert payload["decision"] == "HOLD_SHADOW_CONTINUE"
    assert payload["checklist"]["weekly_fail_rate_guard"] is False
    assert payload["thresholds"]["active_profile"] == "default"
    assert payload["thresholds"]["min_weekly_events"] == 20


def test_build_lens_penalty_apply_mode_checklist_v1_uses_warmup_profile(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    script = repo / "scripts" / "build_lens_penalty_apply_mode_checklist_v1.py"

    daily = tmp_path / "daily.json"
    weekly = tmp_path / "weekly.json"
    state = tmp_path / "state.json"
    policy = tmp_path / "policy.json"
    out = tmp_path / "checklist.json"

    daily.write_text(
        json.dumps(
            {
                "mode": "shadow",
                "applied": False,
                "policy": {"max_daily_penalty": 0.1},
                "summary": {"lenses_evaluated": 3},
                "recommendations": [{"lens_id": "myeongni", "delta": -0.05}],
            }
        ),
        encoding="utf-8",
    )
    weekly.write_text(
        json.dumps({"summary": {"total_events": 15, "overall_fail_rate": 0.7}}),
        encoding="utf-8",
    )
    state.write_text(json.dumps({"schema": "lens_penalty_shadow_state_v1"}), encoding="utf-8")
    policy.write_text(
        json.dumps(
            {
                "schema": "lens_penalty_apply_mode_policy_v1",
                "profiles": {
                    "warmup": {"min_weekly_events": 14, "max_weekly_fail_rate": 0.8},
                    "strict": {"min_weekly_events": 21, "max_weekly_fail_rate": 0.45},
                },
                "human_review_required": True,
                "auto_apply_enabled": False,
            }
        ),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(script),
            "--daily-json",
            str(daily),
            "--weekly-json",
            str(weekly),
            "--state-json",
            str(state),
            "--policy-json",
            str(policy),
            "--out",
            str(out),
        ],
        check=True,
        cwd=repo,
    )

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["thresholds"]["active_profile"] == "warmup"
    assert payload["checklist"]["weekly_min_events_guard"] is True
    assert payload["checklist"]["weekly_fail_rate_guard"] is True
