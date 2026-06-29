from __future__ import annotations

import json
from pathlib import Path

from scripts import check_a_codeai_open_bench_binding_v1 as mod


def _payload(send_gate: str) -> str:
    doc = {
        "schema": "a_codeai_public_bench_landing_payload_v1",
        "send_gate": send_gate,
        "sections": {"public_skus": [{"id": "a"}, {"id": "b"}, {"id": "c"}]},
    }
    return json.dumps(doc)


def test_bench_payload_hold_ok(monkeypatch):
    monkeypatch.setattr(mod, "_legal_send_open", lambda: False)
    ok, details = mod._check_bench_payload(_payload("HOLD"))
    assert ok is True
    assert details["send_gate_ok"] is True


def test_bench_payload_open_requires_legal_signoff(monkeypatch):
    monkeypatch.setattr(mod, "_legal_send_open", lambda: False)
    ok, _ = mod._check_bench_payload(_payload("OPEN"))
    assert ok is False

    monkeypatch.setattr(mod, "_legal_send_open", lambda: True)
    ok, details = mod._check_bench_payload(_payload("OPEN"))
    assert ok is True
    assert details["send_gate"] == "OPEN"


def test_legal_send_open_reads_signoff(tmp_path: Path, monkeypatch):
    signoff = tmp_path / "signoff.json"
    signoff.write_text(
        json.dumps({"send_gate": "OPEN", "ready_for_external_send": True}),
        encoding="utf-8",
    )
    monkeypatch.setattr(mod, "LEGAL_SIGNOFF", signoff)
    assert mod._legal_send_open() is True
