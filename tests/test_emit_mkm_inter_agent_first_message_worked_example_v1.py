"""emit_mkm_inter_agent_first_message_worked_example_v1 contract smoke."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.emit_mkm_inter_agent_first_message_worked_example_v1 import capture

ROOT = Path(__file__).resolve().parents[1]


def test_capture_schema_and_machine_roundtrip():
    doc = capture()
    assert doc.get("schema") == "mkm_inter_agent_first_message_worked_example_v1"
    assert doc.get("classification") == "INTERNAL_ONLY"
    rt = doc.get("expand_packet_only", {}).get("machine_roundtrip", {})
    assert rt.get("expand_equals_stub_reconstructed") is True
    assert rt.get("original_text_on_expand_request") is False


def test_emit_script_writes_json(tmp_path, monkeypatch):
    out = tmp_path / "worked.json"
    monkeypatch.setattr(
        "scripts.emit_mkm_inter_agent_first_message_worked_example_v1.DEFAULT_OUT_JSON",
        out,
    )
    from scripts.emit_mkm_inter_agent_first_message_worked_example_v1 import main

    assert main() == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload.get("schema") == "mkm_inter_agent_first_message_worked_example_v1"
