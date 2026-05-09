from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def drift_mod():
    path = ROOT / "scripts" / "send_trading_guardian_policy_drift_alert_v1.py"
    spec = importlib.util.spec_from_file_location("tg_policy_drift_alert_v1", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_build_dedup_key_normalizes_case(drift_mod):
    k = drift_mod._build_dedup_key({"baseline_sha256": "Aa", "current_sha256": "Bb"})
    assert k == "aa|bb"


def test_is_in_cooldown_true_when_recent(drift_mod):
    now = datetime.now(timezone.utc)
    state = {
        "dedup_key": "aa|bb",
        "last_sent_at_utc": (now - timedelta(seconds=30)).isoformat(),
    }
    assert drift_mod._is_in_cooldown(state, "aa|bb", cooldown_hours=1.0) is True


def test_is_in_cooldown_false_when_key_differs(drift_mod):
    now = datetime.now(timezone.utc)
    state = {
        "dedup_key": "aa|bb",
        "last_sent_at_utc": (now - timedelta(seconds=30)).isoformat(),
    }
    assert drift_mod._is_in_cooldown(state, "xx|yy", cooldown_hours=1.0) is False


def test_is_in_cooldown_false_when_old(drift_mod):
    now = datetime.now(timezone.utc)
    state = {
        "dedup_key": "aa|bb",
        "last_sent_at_utc": (now - timedelta(hours=2)).isoformat(),
    }
    assert drift_mod._is_in_cooldown(state, "aa|bb", cooldown_hours=1.0) is False
