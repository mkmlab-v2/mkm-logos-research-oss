# @MKM12-METADATA
# Type: Logic
# Purpose: regression guard — Register-BTrackDailyHypothesisTask Phase3 switch forwarding (grep only).
from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_REGISTER = _ROOT / "scripts" / "Register-BTrackDailyHypothesisTask.ps1"
_VERIFY = _ROOT / "scripts" / "Verify-BTrackDailyHypothesisScheduledTask_v1.ps1"


def test_register_btrack_task_declares_phase3_switches() -> None:
    text = _REGISTER.read_text(encoding="utf-8")
    assert "[switch]$IncludePhase3LeadingSensors" in text
    assert "[switch]$SkipPhase3NetworkFetch" in text


def test_register_btrack_task_forwards_phase3_switches_to_chain_arg_line() -> None:
    text = _REGISTER.read_text(encoding="utf-8")
    assert '+= " -IncludePhase3LeadingSensors"' in text
    assert '+= " -SkipPhase3NetworkFetch"' in text
    idx_include = text.find("if ($IncludePhase3LeadingSensors)")
    idx_skip_fetch = text.find("if ($SkipPhase3NetworkFetch)")
    assert idx_include != -1 and idx_skip_fetch != -1 and idx_skip_fetch > idx_include


def test_verify_btrack_daily_hypothesis_scheduled_task_script_exists() -> None:
    assert _VERIFY.is_file()
    text = _VERIFY.read_text(encoding="utf-8")
    assert "MKM-BTrack-DailyHypothesis-Chain" in text
    assert "arguments_contain_include_phase3_leading_sensors" in text
    assert "arguments_contain_skip_phase3_network_fetch" in text
    assert "arguments_contain_include_market_myeongni_overlay" in text
    assert "research_evaluation_instrument" in text
    assert "next_run_time" in text
    assert "task_exists" in text


def test_register_btrack_task_forwards_market_myeongni_overlay_to_chain_arg_line() -> None:
    text = _REGISTER.read_text(encoding="utf-8")
    assert "[switch]$IncludeMarketMyeongniOverlay" in text
    assert '+= " -IncludeMarketMyeongniOverlay"' in text
