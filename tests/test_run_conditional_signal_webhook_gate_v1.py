"""Regression tests for Fact-Safe gate in run_conditional_signal_webhook_v1 (no HTTP)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_BT_SCRIPTS = _ROOT / "projects" / "bitcoin-trading" / "scripts"
if str(_BT_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_BT_SCRIPTS))

from run_conditional_signal_webhook_v1 import evaluate_gate  # noqa: E402


def test_active_mode_allows() -> None:
    doc = {
        "expires_at": "2030-01-01T00:00:00+00:00",
        "trinity_governor": {"mode": "ACTIVE_MODE"},
    }
    ok, reason = evaluate_gate(doc, ignore_expiry=False, allow_unknown=False)
    assert ok is True
    assert reason == "go_trinity_ACTIVE_MODE"


def test_locked_mode_blocks() -> None:
    doc = {
        "expires_at": "2030-01-01T00:00:00+00:00",
        "trinity_governor": {"mode": "LOCKED_MODE"},
    }
    ok, reason = evaluate_gate(doc, ignore_expiry=False, allow_unknown=False)
    assert ok is False
    assert reason == "trinity_governor_LOCKED_MODE"


def test_expiry_blocks() -> None:
    doc = {
        "expires_at": "2000-01-01T00:00:00+00:00",
        "trinity_governor": {"mode": "ACTIVE_MODE"},
    }
    ok, reason = evaluate_gate(doc, ignore_expiry=False, allow_unknown=False)
    assert ok is False
    assert reason == "risk_profile_expired"


def test_ignore_expiry_allows_stale_doc() -> None:
    doc = {
        "expires_at": "2000-01-01T00:00:00+00:00",
        "trinity_governor": {"mode": "ACTIVE_MODE"},
    }
    ok, reason = evaluate_gate(doc, ignore_expiry=True, allow_unknown=False)
    assert ok is True
    assert reason == "go_trinity_ACTIVE_MODE"


def test_governance_veto_on_active() -> None:
    doc = {
        "expires_at": "2030-01-01T00:00:00+00:00",
        "trinity_governor": {"mode": "ACTIVE_MODE"},
        "governance_bridge": {"final_action_allowed": False},
    }
    ok, reason = evaluate_gate(doc, ignore_expiry=False, allow_unknown=False)
    assert ok is False
    assert reason == "governance_final_action_denied"


def test_governance_bridge_only_allow() -> None:
    doc = {
        "expires_at": "2030-01-01T00:00:00+00:00",
        "governance_bridge": {"final_action_allowed": True},
    }
    ok, reason = evaluate_gate(doc, ignore_expiry=False, allow_unknown=False)
    assert ok is True
    assert reason == "go_governance_bridge_allow"


def test_unknown_denied_by_default() -> None:
    doc = {"expires_at": "2030-01-01T00:00:00+00:00"}
    ok, reason = evaluate_gate(doc, ignore_expiry=False, allow_unknown=False)
    assert ok is False
    assert reason == "gate_unknown_or_insufficient_signal"


def test_allow_unknown_permits() -> None:
    doc = {"expires_at": "2030-01-01T00:00:00+00:00"}
    ok, reason = evaluate_gate(doc, ignore_expiry=False, allow_unknown=True)
    assert ok is True
    assert reason == "go_allow_unknown"
