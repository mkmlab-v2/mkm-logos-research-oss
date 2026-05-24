# @MKM12-METADATA
# Type: Logic
# Purpose: regression guard — B-track daily chain contemplation Gemini skip wiring.
from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_CHAIN = _ROOT / "scripts" / "run_btrack_daily_hypothesis_chain.ps1"
_REGISTER = _ROOT / "scripts" / "Register-BTrackDailyHypothesisTask.ps1"


def test_daily_chain_declares_pathology_te_mapping_steps() -> None:
    text = _CHAIN.read_text(encoding="utf-8")
    assert "[switch]$SkipPathologyTeMapping" in text
    assert "dump_unified_trading_monitor_te_snapshot_v1.py" in text
    assert "export_btrack_transfer_entropy_snapshot_v1.py" in text
    assert "build_sasang_pathology_te_mapping_hypo_v1.py" in text
    assert "build_compression_prophecy_bridge_status_v1.py" in text


def test_daily_chain_declares_skip_prophecy_contemplation_gemini_and_passes_flag() -> None:
    text = _CHAIN.read_text(encoding="utf-8")
    assert "[switch]$SkipProphecyContemplationGemini" in text
    assert "run_btrack_prophecy_contemplation_v1.py" in text
    assert "--skip-gemini-reflect" in text
    assert "$SkipProphecyContemplationGemini" in text


def test_daily_chain_passes_force_dual_leg_panel_with_btc_csv() -> None:
    text = _CHAIN.read_text(encoding="utf-8")
    assert "--force-dual-leg-panel" in text
    assert '$buildArgs += "--force-dual-leg-panel"' in text
    idx_btc = text.find('$buildArgs += @("--btc-csv", $btcResolved)')
    idx_force = text.find('$buildArgs += "--force-dual-leg-panel"')
    assert idx_btc != -1 and idx_force != -1 and idx_force > idx_btc


def test_register_btrack_task_supports_skip_prophecy_contemplation_gemini() -> None:
    text = _REGISTER.read_text(encoding="utf-8")
    assert "[switch]$SkipProphecyContemplationGemini" in text
    assert '+= " -SkipProphecyContemplationGemini"' in text


def test_register_btrack_task_defaults_skip_panel_in_scheduled_chain_args() -> None:
    text = _REGISTER.read_text(encoding="utf-8")
    assert "[switch]$IncludePanel24hAlertsCheck" in text
    assert "if (-not $IncludePanel24hAlertsCheck)" in text
    assert '$argLine += " -SkipPanel24hAlertsCheck"' in text


def test_register_btrack_task_rejects_include_and_skip_panel_together() -> None:
    text = _REGISTER.read_text(encoding="utf-8")
    assert "IncludePanel24hAlertsCheck -and $SkipPanel24hAlertsCheck" in text
