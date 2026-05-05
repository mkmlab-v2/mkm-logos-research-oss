"""Smoke tests for prophecy proxy streak gate (UTC calendar-day increment)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture()
def streak_script(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import scripts.check_prophecy_proxy_streak_gate_v1 as mod

    monkeypatch.setattr(mod, "ROOT", tmp_path)
    monkeypatch.setattr(mod, "DEFAULT_HEALTH", tmp_path / "health.json")
    monkeypatch.setattr(mod, "DEFAULT_STATE", tmp_path / "state.json")
    monkeypatch.setattr(mod, "DEFAULT_RESULT", tmp_path / "result.json")
    return mod


def _write_health(path: Path, operational_path: str) -> None:
    doc = {
        "schema": "prophecy_health_status_v1",
        "hit_rate_eval_summary": {"operational_path": operational_path},
    }
    path.write_text(json.dumps(doc), encoding="utf-8")


def test_resets_on_price(streak_script, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    state = tmp_path / "state.json"
    state.write_text(
        json.dumps(
            {
                "schema": "prophecy_proxy_streak_state_v1",
                "consecutive_degraded_days": 5,
                "last_increment_calendar_date_utc": "2026-01-01",
            }
        ),
        encoding="utf-8",
    )
    _write_health(tmp_path / "health.json", "price")
    assert streak_script.main([]) == 0
    st = json.loads(state.read_text(encoding="utf-8"))
    assert st["consecutive_degraded_days"] == 0


def test_increments_once_per_proxy_day(streak_script, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    h = tmp_path / "health.json"
    _write_health(h, "proxy")
    monkeypatch.setattr(streak_script, "_utc_date_str", lambda: "2026-05-10")

    assert streak_script.main([]) == 0
    st = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert st["consecutive_degraded_days"] == 1

    assert streak_script.main([]) == 0
    st2 = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert st2["consecutive_degraded_days"] == 1
