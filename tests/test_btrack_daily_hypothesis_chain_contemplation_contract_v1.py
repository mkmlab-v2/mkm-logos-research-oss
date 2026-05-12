# @MKM12-METADATA
# Type: Logic
# Purpose: regression guard — B-track daily chain contemplation Gemini skip wiring.
from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_CHAIN = _ROOT / "scripts" / "run_btrack_daily_hypothesis_chain.ps1"
_REGISTER = _ROOT / "scripts" / "Register-BTrackDailyHypothesisTask.ps1"


def test_daily_chain_declares_skip_prophecy_contemplation_gemini_and_passes_flag() -> None:
    text = _CHAIN.read_text(encoding="utf-8")
    assert "[switch]$SkipProphecyContemplationGemini" in text
    assert "run_btrack_prophecy_contemplation_v1.py" in text
    assert "--skip-gemini-reflect" in text
    assert "$SkipProphecyContemplationGemini" in text


def test_register_btrack_task_supports_skip_prophecy_contemplation_gemini() -> None:
    text = _REGISTER.read_text(encoding="utf-8")
    assert "[switch]$SkipProphecyContemplationGemini" in text
    assert '+= " -SkipProphecyContemplationGemini"' in text
