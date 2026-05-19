from __future__ import annotations

import json
from pathlib import Path

from scripts.apply_btrack_phase3_human_approval_v1 import _patch_retirement, _patch_sidecar


def test_patch_sidecar_sets_human_approved(tmp_path: Path) -> None:
    sidecar = tmp_path / "sidecar.json"
    sidecar.write_text(
        json.dumps(
            {
                "schema": "btrack_prophecy_score_insight_sidecar_v1",
                "phase3_merge": {"status": "aux_fields_merged"},
            }
        ),
        encoding="utf-8",
    )
    _patch_sidecar(sidecar, "docs/final/artifacts/btrack_phase3_human_approval_v1_latest.json")
    doc = json.loads(sidecar.read_text(encoding="utf-8"))
    assert doc["human_approval"]["decision"] == "APPROVED"
    assert doc["phase3_merge"]["human_approved"] is True
    assert doc["human_approval"]["prod_score_mutation"] is False


def test_patch_retirement_keeps_shield_retired(tmp_path: Path) -> None:
    path = tmp_path / "retire.json"
    path.write_text(
        json.dumps({"verdict": {"shield_as_direction_gate": "RETIRED", "apply_prod": False}}),
        encoding="utf-8",
    )
    _patch_retirement(path, "docs/final/artifacts/btrack_phase3_human_approval_v1_latest.json", "tester")
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc["verdict"]["shield_as_direction_gate"] == "RETIRED"
    assert doc["verdict"]["human_approved"] is True
    assert doc["verdict"]["apply_prod"] is False
