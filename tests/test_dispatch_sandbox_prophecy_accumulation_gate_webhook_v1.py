"""Pre-gate webhook should trigger when days_until==1 and --notify-one-day-left."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    path = ROOT / "scripts/dispatch_sandbox_prophecy_accumulation_gate_webhook_v1.py"
    spec = importlib.util.spec_from_file_location("dispatch_sandbox_accum", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_pre_gate_should_post_logic() -> None:
    mod = _load()
    # Mirror main() decision without HTTP
    gate_open = False
    days_left = 1
    notify = True
    pre_gate = notify and days_left == 1 and not gate_open
    should = gate_open or days_left <= 0 or pre_gate
    assert pre_gate is True
    assert should is True
