# @MKM12-METADATA
# Type: Logic
# Purpose: regression guard — B-track daily chain Phase3 leading-sensors hook wiring (grep only).
from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_CHAIN = _ROOT / "scripts" / "run_btrack_daily_hypothesis_chain.ps1"


def test_daily_chain_declares_phase3_leading_sensors_switches() -> None:
    text = _CHAIN.read_text(encoding="utf-8")
    assert "[switch]$IncludePhase3LeadingSensors" in text
    assert "[switch]$SkipPhase3NetworkFetch" in text
    assert "[switch]$StrictPhase3LeadingSensors" in text


def test_daily_chain_runs_join_after_hit_rate_when_phase3_enabled() -> None:
    text = _CHAIN.read_text(encoding="utf-8")
    assert "$IncludePhase3LeadingSensors" in text
    assert "join_btrack_phase3_leading_sensors_score_v1.py" in text
    assert "--score-json $scoreJsonRel --instrument btc" in text
    assert "build_btrack_prophecy_score_insight_sidecar_stub_v1.py" in text
    idx_eval = text.find("eval_prophecy_hit_rate_v1.py --run-mode price --score-json $scoreJsonRel")
    idx_phase3 = text.find("if ($IncludePhase3LeadingSensors)")
    assert idx_eval != -1 and idx_phase3 != -1 and idx_phase3 > idx_eval


def test_daily_chain_skip_phase3_network_fetch_controls_binance_prefetch() -> None:
    text = _CHAIN.read_text(encoding="utf-8")
    assert "$SkipPhase3NetworkFetch" in text
    assert "run_btrack_phase3_leading_sensors_chain_v1.py" in text
    assert "--fetch-binance" in text
    assert "--skip-seed" in text
