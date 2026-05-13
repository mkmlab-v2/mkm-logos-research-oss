"""Contract: Check-ProphecyPanel24hAlerts.ps1 webhook routing (ALERT_1/3 vs ALERT_2-only)."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "Check-ProphecyPanel24hAlerts.ps1"


def test_panel_script_declares_include_alert2_and_default_routing() -> None:
    text = _SCRIPT.read_text(encoding="utf-8")
    assert "[switch]$IncludeAlert2InWebhook" in text
    assert "performance_and_structural_only" in text
    assert "only ALERT_2 failed" in text
    assert '$webhookPost = (-not $a1Pass) -or (-not $a3Pass)' in text
