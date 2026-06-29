"""RQ-028 commander profile path resolver tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RESOLVER = ROOT / "scripts/a_code_commander_profile_resolve_v1.py"
EXAMPLE = ROOT / "docs/final/artifacts/commander_profile_v1.example.json"


def _load_resolver():
    import importlib.util

    spec = importlib.util.spec_from_file_location("a_code_profile_resolve", RESOLVER)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_resolve_falls_back_to_example_when_no_local(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    if not EXAMPLE.is_file():
        pytest.skip("commander profile example missing")
    monkeypatch.delenv("MKM_COMMANDER_PROFILE_JSON", raising=False)
    mod = _load_resolver()
    monkeypatch.setattr(mod, "LOCAL_PROFILE", tmp_path / "missing_local.json")
    path, source = mod.resolve_commander_profile_path()
    assert source == "example"
    assert path.resolve() == EXAMPLE.resolve()


def test_resolve_prefers_local_when_present() -> None:
    mod = _load_resolver()
    if not mod.LOCAL_PROFILE.is_file():
        pytest.skip("local commander profile not on disk")
    path, source = mod.resolve_commander_profile_path()
    assert source == "local"
    assert path.resolve() == mod.LOCAL_PROFILE.resolve()


def test_resolve_explicit_profile(tmp_path: Path) -> None:
    if not EXAMPLE.is_file():
        pytest.skip("commander profile example missing")
    mod = _load_resolver()
    path, source = mod.resolve_commander_profile_path(EXAMPLE)
    assert source == "explicit"
    assert path.resolve() == EXAMPLE.resolve()


def test_resolve_env_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    if not EXAMPLE.is_file():
        pytest.skip("commander profile example missing")
    monkeypatch.setenv("MKM_COMMANDER_PROFILE_JSON", str(EXAMPLE))
    mod = _load_resolver()
    path, source = mod.resolve_commander_profile_path()
    assert source == "env"
    assert path.resolve() == EXAMPLE.resolve()
