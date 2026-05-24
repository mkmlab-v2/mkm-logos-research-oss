"""Compression enterprise hardening hooks (M1–M2)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from scripts.compression_token_api_stub import app
from scripts.core.compression_hardening_v1 import (
    extract_mask_must_keep,
    gatekeeper_bypass_max_tokens,
    llm_decode_params,
    should_bypass_compression,
)

client = TestClient(app)


def test_llm_decode_params_deterministic():
    p = llm_decode_params()
    assert p["temperature"] == 0.0
    assert p["seed"] == 42
    assert p["do_sample"] is False


def test_mask_extracts_number_and_negation():
    text = "수익률 47.5%는 안 내려가고 not acceptable"
    terms, meta = extract_mask_must_keep(text)
    assert meta["mask_applied"]
    assert len(terms) >= 2


def test_gatekeeper_bypass_short_input():
    assert should_bypass_compression(gatekeeper_bypass_max_tokens() - 1)
    assert not should_bypass_compression(gatekeeper_bypass_max_tokens() + 100)


def test_compress_gatekeeper_bypass_identity():
    short = " ".join(["word"] * 50)
    r = client.post(
        "/v1/compress",
        json={"text": short, "client_request_id": "gk-test"},
    )
    assert r.status_code == 200
    flags = r.json().get("integrity_flags") or {}
    assert flags.get("compression_gatekeeper_bypass") is True
    assert flags.get("metrics_mode") == "identity_gatekeeper_bypass"
    m = r.json().get("compression_metrics") or {}
    assert float(m.get("savings_ratio", -1)) == 0.0


def test_compress_precompress_mask_flag():
    r = client.post(
        "/v1/compress",
        json={"text": "금리 3.5% 인상은 못 받아들인다", "client_request_id": "mask-test"},
    )
    assert r.status_code == 200
    flags = r.json().get("integrity_flags") or {}
    assert flags.get("precompress_mask", {}).get("mask_applied") is True
