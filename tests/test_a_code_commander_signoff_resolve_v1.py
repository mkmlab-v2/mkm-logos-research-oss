"""A-code signoff resolver tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "data/personalization/commander_a_code_signoff_v1.local.json.example"


def _load_resolver():
    path = ROOT / "scripts/a_code_commander_signoff_resolve_v1.py"
    spec = importlib.util.spec_from_file_location("a_code_signoff_resolve", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_resolve_absent_by_default() -> None:
    mod = _load_resolver()
    path, source = mod.resolve_commander_a_code_signoff_path(None)
    if mod.LOCAL_SIGNOFF.is_file():
        assert source == "local"
        assert path is not None
    else:
        assert path is None
        assert source == "absent"


def test_resolve_example_when_allowed() -> None:
    mod = _load_resolver()
    if not EXAMPLE.is_file():
        pytest.skip("example signoff missing")
    path, source = mod.resolve_commander_a_code_signoff_path(None, allow_example=True)
    if mod.LOCAL_SIGNOFF.is_file():
        assert source == "local"
    else:
        assert source == "example"
        assert path == EXAMPLE.resolve()
