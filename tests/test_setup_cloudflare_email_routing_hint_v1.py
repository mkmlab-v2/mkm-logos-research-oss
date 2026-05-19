"""Offline regression for Cloudflare Email Routing setup helper hints (no API calls)."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "setup_cloudflare_email_routing_v1.py"
    spec = importlib.util.spec_from_file_location("setup_cloudflare_email_routing_v1", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_cloudflare_auth_hint_10000() -> None:
    m = _load_module()
    h = m._cloudflare_auth_hint([{"code": 10000, "message": "Authentication error"}])
    assert h is not None
    assert "10000" in h
    assert "sync_required_env_to_user" in h


def test_cloudflare_auth_hint_message_only() -> None:
    m = _load_module()
    h = m._cloudflare_auth_hint([{"code": 9999, "message": "Authentication error"}])
    assert h is not None


def test_cloudflare_auth_hint_none() -> None:
    m = _load_module()
    assert m._cloudflare_auth_hint([]) is None
    assert m._cloudflare_auth_hint([{"code": 9109, "message": "not auth"}]) is None


def test_prepend_auth_hint_inserts_first() -> None:
    m = _load_module()
    manual = ["second"]
    m._prepend_auth_hint(manual, {"errors": [{"code": 10000, "message": "Authentication error"}]})
    assert len(manual) == 2
    assert "10000" in manual[0]
    assert manual[1] == "second"


def test_prepend_auth_hint_noop_when_no_match() -> None:
    m = _load_module()
    manual = ["only"]
    m._prepend_auth_hint(manual, {"errors": [{"code": 7003, "message": "not found"}]})
    assert manual == ["only"]
