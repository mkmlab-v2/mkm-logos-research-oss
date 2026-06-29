"""Offline validation for personadiary_android_intent_e2e_v1 report shape."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/run_personadiary_android_intent_e2e_v1.py"


def _load_validator():
    import importlib.util

    spec = importlib.util.spec_from_file_location("pd_android_intent_e2e", VALIDATOR)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def validator():
    return _load_validator()


def test_intent_e2e_report_passes_when_all_probes_ok(validator, tmp_path: Path) -> None:
    shot = tmp_path / "shot.png"
    shot.write_bytes(b"x" * 1200)
    report = {
        "schema": "personadiary_android_intent_e2e_v1",
        "research_only": True,
        "hypothesis_tier": "B",
        "package": "com.mkmlife.personadiary.hypo",
        "ok": True,
        "probes": [
            {"id": "save_moment_note", "ok": True, "pid": "123"},
            {"id": "add_reminder", "ok": True, "pid": "123"},
            {"id": "share_text", "ok": True, "pid": "123"},
        ],
    }
    ok, errors = validator.validate_report(report, shot_path=shot)
    assert ok is True
    assert errors == []


def test_intent_e2e_report_fails_missing_probe(validator, tmp_path: Path) -> None:
    shot = tmp_path / "shot.png"
    shot.write_bytes(b"x" * 1200)
    report = {
        "schema": "personadiary_android_intent_e2e_v1",
        "research_only": True,
        "hypothesis_tier": "B",
        "package": "com.mkmlife.personadiary.hypo",
        "ok": True,
        "probes": [{"id": "save_moment_note", "ok": True, "pid": "123"}],
    }
    ok, errors = validator.validate_report(report, shot_path=shot)
    assert ok is False
    assert any("missing_probe" in e for e in errors)
