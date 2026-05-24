"""Wire envelope schema validation."""

from __future__ import annotations


def test_example_fixture_validates():
    from scripts.validate_mkm_inter_agent_wire_envelope_v1 import EXAMPLE, validate_doc
    import json

    doc = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    out = validate_doc(doc)
    assert out.get("ok")


def test_live_turn_envelope_validates():
    from scripts.validate_mkm_inter_agent_wire_envelope_v1 import probe_live_envelope

    out = probe_live_envelope()
    assert out.get("ok")
