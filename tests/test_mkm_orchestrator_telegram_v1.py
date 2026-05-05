"""Unit tests for MKM-Orchestrator Telegram helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_tg():
    root = Path(__file__).resolve().parents[1]
    p = root / "scripts" / "mkm_orchestrator_telegram_v1.py"
    spec = importlib.util.spec_from_file_location("mkm_orchestrator_telegram_v1", p)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_parse_go_command():
    tg = _load_tg()
    assert tg.parse_go_command("GO my-task-001") == "my-task-001"
    assert tg.parse_go_command("go my-task-001") == "my-task-001"
    assert tg.parse_go_command("GO") is None
    assert tg.parse_go_command(" NOPE foo ") is None
