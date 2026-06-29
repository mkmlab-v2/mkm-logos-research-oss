"""Unit tests for personadiary android emulator smoke validator."""
from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "run_personadiary_android_emulator_smoke_v1.py"
    spec = importlib.util.spec_from_file_location("personadiary_android_emulator_smoke", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_validate_run_report_ok(tmp_path):
    mod = _load_module()
    shot = tmp_path / "shot.png"
    shot.write_bytes(b"\x89PNG" + b"x" * 2000)
    run = {
        "schema": "personadiary_android_emulator_run_v1",
        "package": mod.PKG,
        "pid": "1234",
        "webview_ok": True,
        "research_only": True,
        "hypothesis_tier": "B",
        "ok": True,
    }
    ok, errors, _band = mod.validate_run_report(run, shot_path=shot)
    assert ok is True
    assert errors == []


def test_validate_run_report_missing_webview(tmp_path):
    mod = _load_module()
    shot = tmp_path / "shot.png"
    shot.write_bytes(b"\x89PNG" + b"x" * 2000)
    run = {
        "schema": "personadiary_android_emulator_run_v1",
        "package": mod.PKG,
        "pid": "1234",
        "webview_ok": False,
        "research_only": True,
        "hypothesis_tier": "B",
        "ok": False,
    }
    ok, errors, _band = mod.validate_run_report(run, shot_path=shot)
    assert ok is False
    assert "webview_not_foreground" in errors
