"""Offline smoke: Universal Root community GTM weekly routine structure."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/Invoke-UniversalRootCommunityGtmWeeklyRoutine_v1.ps1"
REGISTER = ROOT / "scripts/Register-UniversalRootCommunityGtmWeeklyTask_v1.ps1"
POLL = ROOT / "scripts/poll_universal_root_community_gtm_v1.py"
THREAD_B = ROOT / "scripts/post_universal_root_discussions_thread_b_v1.py"


def test_weekly_runner_wires_poll_and_thread_b():
    text = RUNNER.read_text(encoding="utf-8")
    assert "poll_universal_root_community_gtm_v1.py" in text
    assert "post_universal_root_discussions_thread_b_v1.py" in text
    assert "--acknowledge-send" in text
    assert "blocked_await_external_repro" in text


def test_register_script_exists():
    assert REGISTER.is_file()
    assert "MKM_UniversalRoot_CommunityGtm_Weekly" in REGISTER.read_text(encoding="utf-8")


def test_scheduler_tier4_ssot_registered():
    import json

    stack = json.loads(
        (ROOT / "docs/final/artifacts/mkm_scheduler_solo_core_stack_v1.json").read_text(encoding="utf-8-sig")
    )
    tier4 = stack.get("tier4_solo_intentional_keep") or []
    assert "\\MKM_UniversalRoot_CommunityGtm_Weekly" in tier4


def test_poll_and_thread_b_scripts_present():
    assert POLL.is_file()
    assert THREAD_B.is_file()
    assert "--min-external-repro" in THREAD_B.read_text(encoding="utf-8")
