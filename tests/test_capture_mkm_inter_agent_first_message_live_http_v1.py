"""Live HTTP evidence capture smoke."""

from __future__ import annotations

from scripts.capture_mkm_inter_agent_first_message_live_http_v1 import capture


def test_capture_roundtrip_ok() -> None:
    doc = capture()
    rt = doc.get("machine_roundtrip") or {}
    assert rt.get("expand_equals_stub_reconstructed") is True
    assert rt.get("token_in") is not None
