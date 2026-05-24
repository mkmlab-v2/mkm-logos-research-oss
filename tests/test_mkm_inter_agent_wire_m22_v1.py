"""M22: M3 public copy artifact + health wire-first sidecar dialogue."""

from __future__ import annotations


def test_m3_public_copy_emit():
    from scripts.emit_mkm_inter_agent_m3_public_copy_v1 import emit_public_copy

    doc = emit_public_copy()
    assert doc.get("ok")
    assert doc.get("public_copy", {}).get("ko")
    assert doc.get("avg_exact_restore_rate") is not None


def test_health_wire_sidecar_dialogue_uplift():
    from scripts.capture_mkm_inter_agent_health_wire_sidecar_dialogue_v1 import capture

    doc = capture(turns=3)
    assert doc.get("ok")
    assert doc.get("uplift_avg_atom_id_count", 0) > 0
