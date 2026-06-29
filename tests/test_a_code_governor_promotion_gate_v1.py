"""RQ-028 P6 governor promotion gate tests."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE_SCRIPT = ROOT / "scripts/check_a_code_governor_promotion_gate_v1.py"
REPLAY = ROOT / "reports/a_code_governor_knob_multiday_replay_v1_latest.json"
THRESHOLDS = ROOT / "experiments/a_code_12ai_v2/specs/a_code_governor_promotion_gate_thresholds_v1.json"


def _load_gate_module():
    spec = importlib.util.spec_from_file_location("a_code_gate", GATE_SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_promotion_gate_watch_continue_on_latest_replay(tmp_path: Path) -> None:
    if not REPLAY.is_file() or not THRESHOLDS.is_file():
        pytest.skip("multiday replay or thresholds missing")
    mod = _load_gate_module()
    replay = json.loads(REPLAY.read_text(encoding="utf-8"))
    thresholds = json.loads(THRESHOLDS.read_text(encoding="utf-8"))
    report = mod.evaluate_gate(replay, thresholds)
    assert report.get("schema") == "a_code_governor_promotion_gate_v1"
    assert report.get("research_only") is True
    assert report.get("track_a_auto_promotion") is False
    assert report["summary"]["decision"] == "WATCH_CONTINUE"
    assert report["summary"]["pass_count"] == report["summary"]["total"]


def test_promotion_gate_cli_writes_json(tmp_path: Path) -> None:
    if not REPLAY.is_file():
        pytest.skip("multiday replay missing")
    out = tmp_path / "gate.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(GATE_SCRIPT),
            "--replay",
            str(REPLAY),
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["summary"]["decision"] in {"WATCH_CONTINUE", "HOLD_RESEARCH"}


def test_evening_telegram_includes_governor_line_when_obs_exists() -> None:
    obs = ROOT / "reports/a_code_governor_knob_evening_observation_v1_latest.json"
    if not obs.is_file():
        pytest.skip("evening observation missing")
    from scripts.score_commander_evening_briefing_v1 import build_evening_telegram

    score = {
        "calendar_kst": "2026-06-05",
        "briefing_id": "test",
        "market_direction": "flat",
        "market_return_pct": 0.0,
        "multi_asset": {"kospi": {}, "btc": {}, "nasdaq": {}},
        "summary": {"soft_hit_rate": None, "aligned": 0, "partial": 0, "reject": 0, "nasdaq_pending": 0},
        "prediction_scores": [],
    }
    text = build_evening_telegram(score, include_a_code_governor=True)
    assert "A-code S2" in text
