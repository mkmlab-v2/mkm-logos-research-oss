from __future__ import annotations

import base64
import json

import pytest

from scripts.core.secure_payload_keyring import (
    EnvTrackKeyResolver,
    ExternalKmsTrackKeyResolver,
)


def _b64_of(ch: bytes) -> str:
    return base64.urlsafe_b64encode(ch * 32).decode("ascii")


def test_env_track_key_resolver_reads_a_b_track(monkeypatch):
    monkeypatch.setenv("MKM_ENVELOPE_A_TRACK_KEY_B64", _b64_of(b"A"))
    monkeypatch.setenv("MKM_ENVELOPE_B_TRACK_KEY_B64", _b64_of(b"B"))
    r = EnvTrackKeyResolver()
    assert r.resolve_key(track="a_track") == b"A" * 32
    assert r.resolve_key(track="b_track") == b"B" * 32


def test_external_resolver_reads_json_key_file(tmp_path, monkeypatch):
    f = tmp_path / "keys.json"
    f.write_text(json.dumps({"a_track": _b64_of(b"C"), "b_track": _b64_of(b"D")}), encoding="utf-8")
    monkeypatch.setenv("MKM_ENVELOPE_EXTERNAL_KEY_FILE", str(f))
    r = ExternalKmsTrackKeyResolver()
    assert r.resolve_key(track="a_track") == b"C" * 32
    assert r.resolve_key(track="b_track") == b"D" * 32


def test_external_resolver_errors_when_unconfigured(monkeypatch):
    monkeypatch.delenv("MKM_ENVELOPE_EXTERNAL_KEY_FILE", raising=False)
    monkeypatch.delenv("MKM_ENVELOPE_EXTERNAL_KEY_CMD", raising=False)
    r = ExternalKmsTrackKeyResolver()
    with pytest.raises(RuntimeError):
        r.resolve_key(track="a_track")
