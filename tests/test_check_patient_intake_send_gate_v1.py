"""Patient intake send gate — internal PoC lane."""

from __future__ import annotations

import json
from pathlib import Path

from scripts import check_patient_intake_send_gate_v1 as mod


def test_confirm_internal_poc_flips_gate(tmp_path: Path) -> None:
    gate = tmp_path / "gate.json"
    gate.write_text(
        json.dumps(
            {
                "schema": "patient_intake_send_gate_v1",
                "send_gate": "HOLD",
                "ready_for_external_send": False,
                "ready_internal_poc": False,
                "checklist": {
                    "public_facing_v17_reviewed": False,
                    "intake_routes_unified": True,
                    "no_google_form_external": True,
                    "no_constitution_certainty_patient_copy": True,
                    "commander_internal_poc_ack": False,
                },
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    doc = json.loads(gate.read_text(encoding="utf-8"))
    updated = mod.confirm_internal_poc(doc)
    assert updated["send_gate"] == "READY_INTERNAL_POC"
    assert updated["ready_internal_poc"] is True
    assert updated["ready_for_external_send"] is False
    assert updated["checklist"]["commander_internal_poc_ack"] is True
