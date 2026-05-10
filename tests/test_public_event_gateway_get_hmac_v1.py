"""Unit tests for GET HMAC on public_event_gateway (no HTTP server)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_GATEWAY = _ROOT / "projects" / "bitcoin-trading" / "ops" / "windows-rehearsal" / "jemaai-cloud-mvp" / "public_event_gateway.py"


def _load_gateway():
    spec = importlib.util.spec_from_file_location("public_event_gateway_hmac_test", _GATEWAY)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def gw():
    assert _GATEWAY.is_file()
    return _load_gateway()


def test_build_and_verify_hmac_good(gw):
    secret = "unit-test-secret"
    ts = "1735689600"
    path = "/api/public-events/latest"
    sig = gw.build_public_event_get_hmac_signature(secret, ts, "GET", path)
    headers = {"x-mkm-timestamp": ts, "x-mkm-signature": sig}
    assert gw.verify_public_event_get_hmac(secret, headers, "GET", path, now_ts=int(ts), max_skew_sec=300)


def test_verify_rejects_bad_signature(gw):
    secret = "unit-test-secret"
    ts = "1735689600"
    path = "/api/public-events/latest"
    headers = {"x-mkm-timestamp": ts, "x-mkm-signature": "deadbeef"}
    assert not gw.verify_public_event_get_hmac(secret, headers, "GET", path, now_ts=int(ts), max_skew_sec=300)


def test_verify_rejects_clock_skew(gw):
    secret = "unit-test-secret"
    ts = "1735689600"
    path = "/api/public-events/latest"
    sig = gw.build_public_event_get_hmac_signature(secret, ts, "GET", path)
    headers = {"x-mkm-timestamp": ts, "x-mkm-signature": sig}
    assert not gw.verify_public_event_get_hmac(
        secret, headers, "GET", path, now_ts=int(ts) + 99999, max_skew_sec=300
    )


def test_verify_empty_secret_always_ok(gw):
    headers = {}
    assert gw.verify_public_event_get_hmac("", headers, "GET", "/api/public-events/latest")
