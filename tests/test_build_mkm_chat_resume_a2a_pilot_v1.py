"""tp01 chat resume A2A pilot smoke."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.build_mkm_chat_resume_a2a_pilot_v1 import build_pilot_document
from scripts.mkm_a2a_compress_pilot_lib_v1 import compress_plaintext_v2

ROOT = Path(__file__).resolve().parents[1]


def test_build_pilot_document_schema():
    doc = build_pilot_document(
        ROOT,
        top_n=3,
        include_slice=False,
        slice_max_chars=1200,
        lane=None,
        routing_profile="track_a_promoted",
    )
    assert doc["schema"] == "mkm_chat_resume_a2a_pilot_v1"
    assert doc["target_point_id"] == "tp01_cursor_ops_resume_handoff"
    assert doc["status"] == "PILOT"
    assert "compress_result" in doc
    assert "inject_payload" in doc


def test_compress_skips_below_min_tokens():
    from fastapi.testclient import TestClient

    from scripts.compression_token_api_v2_stub import app

    client = TestClient(app)
    row = compress_plaintext_v2(client, "short text", min_tokens=32)
    assert row["decision"] == "skipped_below_min_tokens"
    assert row["token_in"] < 32


def test_compress_applies_at_low_threshold():
    from fastapi.testclient import TestClient

    from scripts.compression_token_api_v2_stub import app

    dense = (
        "WATCH regime macro fragility elevated recommend REDUCE exposure BTC gate clears "
        "Prophecy lane B-track dual-leg KOSPI divergence hold new longs review KST ops memory"
    )
    client = TestClient(app)
    row = compress_plaintext_v2(client, dense, min_tokens=8)
    assert row["decision"] == "compressed"
    assert row["http_status"] == 200
    assert row.get("content_fingerprint")
    expand = row.get("expand_packet_only") or {}
    assert expand.get("http_status") == 200
    assert expand.get("expand_equals_stub_reconstructed") is True


def test_emit_script_writes_json(tmp_path, monkeypatch):
    out = tmp_path / "pilot.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "build_mkm_chat_resume_a2a_pilot_v1.py",
            "--out",
            str(out),
        ],
    )
    from scripts.build_mkm_chat_resume_a2a_pilot_v1 import main

    assert main() == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload.get("schema") == "mkm_chat_resume_a2a_pilot_v1"
