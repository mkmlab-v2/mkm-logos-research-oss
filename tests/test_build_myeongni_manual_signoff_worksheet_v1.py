from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_build_myeongni_manual_signoff_worksheet_ready(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    script = repo / "scripts" / "build_myeongni_manual_signoff_worksheet_v1.py"
    schema_path = repo / "docs" / "final" / "artifacts" / "schemas" / "myeongni_manual_signoff_worksheet_v1.schema.json"

    gate = tmp_path / "myeongni_promotion_gate_latest.json"
    lock_doc = tmp_path / "myeongni_manual_promotion_decision_lock_latest.json"
    readiness = tmp_path / "myeongni_commercialization_readiness_packet_latest.json"
    realset_gate = tmp_path / "myeongni_stage2_realset_gate_latest.json"
    shadow_gov = tmp_path / "myeongni_shadow_governance_latest.json"
    out = tmp_path / "myeongni_manual_signoff_worksheet_latest.json"

    _write(
        gate,
        {
            "status": "PASS",
            "decision": "MANUAL_PROMOTION_REVIEW_GO",
            "go_for_manual_signoff": True,
            "policy": {
                "track_b_to_a_auto_bridge": False,
                "live_trigger_auto_enabled": False,
                "human_signoff_required": True,
            },
        },
    )
    _write(lock_doc, {"final_decision": "approved"})
    _write(readiness, {"readiness": "Ready"})
    _write(realset_gate, {"pass": True, "real_count": 65})
    _write(shadow_gov, {"decision": "HUMAN_REVIEW_REQUIRED_FOR_PROMOTION", "blockers": [], "warnings": []})

    subprocess.run(
        [
            sys.executable,
            str(script),
            "--promotion-gate",
            str(gate),
            "--manual-lock",
            str(lock_doc),
            "--readiness",
            str(readiness),
            "--stage2-realset-gate",
            str(realset_gate),
            "--shadow-governance",
            str(shadow_gov),
            "--out",
            str(out),
        ],
        check=True,
        cwd=repo,
    )

    payload = json.loads(out.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(payload, schema)

    assert payload["decision"] == "READY_FOR_COMMANDER_SIGNOFF"
    assert payload["all_green"] is True
    assert payload["failed_checks"] == []
