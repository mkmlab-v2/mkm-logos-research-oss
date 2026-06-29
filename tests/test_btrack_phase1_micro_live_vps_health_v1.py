"""Tests for VPS health probe (offline / mocked)."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT))

from scripts.build_btrack_phase1_micro_live_vps_health_v1 import probe_vps


def test_probe_vps_healthy_mock() -> None:
    state = {
        "engine": "aroon_v1",
        "btrack_micro_live_overlay": {"active": True, "side_hint": "SELL", "eval_date": "2026-05-29"},
        "btrack_micro_live_guard": {"active": True, "entries_today": 0},
    }
    engine = {
        "status": "READY_FOR_ENGINE_SUBMIT",
        "btrack_signal": {"side_hint": "SELL", "eval_date": "2026-05-29"},
    }

    def fake_ssh(host: str, cmd: str, *, timeout: int = 45):
        if cmd.startswith("pm2 pid"):
            return 0, "2044798", ""
        if "btrack_overlay=" in cmd:
            return 0, "btrack_overlay=True hint=SELL", ""
        if "trading_state.json" in cmd:
            return 0, json.dumps(state), ""
        if "btc_limited_live_engine_input" in cmd:
            return 0, json.dumps(engine), ""
        return 1, "", "unknown"

    local_engine = engine.copy()
    with patch("scripts.build_btrack_phase1_micro_live_vps_health_v1._ssh", side_effect=fake_ssh), patch(
        "scripts.build_btrack_phase1_micro_live_vps_health_v1._load_local_engine_handoff",
        return_value=local_engine,
    ):
        doc = probe_vps(vps_host="test", dest_root="/opt/x", pm2_app="bitcoin-live-small-24h")
    assert doc["vps_micro_live_healthy"] is True
    assert doc["pm2_status"] == "online"
    assert doc["operating_mode"]["label"] == "verified_current_drift_observed"
    assert doc["drift_observation"]["drift_detected"] is False
