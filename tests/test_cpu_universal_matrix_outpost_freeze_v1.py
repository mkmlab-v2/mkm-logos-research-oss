"""CPU Universal Matrix outpost freeze manifest contract."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = (
    ROOT
    / "reports/constitution/btrack_pilot/baselines/router_tuning_v1/cpu_universal_matrix_literal_hybrid_freeze_manifest_v1.json"
)
POINTER = ROOT / "docs/final/artifacts/CPU_UNIVERSAL_MATRIX_CPU_OUTPOST_FREEZE_POINTER_V1.json"
CLOSURE = ROOT / "reports/constitution/btrack_pilot/comp_universal_matrix_cpu_outpost_closure_v1.json"
FORBIDDEN = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"


def test_freeze_manifest_exists_and_governance() -> None:
    doc = json.loads(MANIFEST.read_text(encoding="utf-8-sig"))
    assert doc.get("research_only") is True
    assert doc.get("governance", {}).get("track_a_active_written") is False
    assert doc.get("governance", {}).get("cap_grid_sweep_default") == "cancelled"
    assert doc["headline_metrics_1103"]["jaccard_floor_gate_0_85_passed"] is False
    for name, digest in doc.get("sha256", {}).items():
        path = MANIFEST.parent / name
        assert path.is_file(), name
        assert len(digest) == 64


def test_pointer_and_closure_align() -> None:
    ptr = json.loads(POINTER.read_text(encoding="utf-8-sig"))
    cl = json.loads(CLOSURE.read_text(encoding="utf-8-sig"))
    assert ptr["ssot_manifest"].endswith("cpu_universal_matrix_literal_hybrid_freeze_manifest_v1.json")
    assert cl["status"] == "cpu_outpost_frozen"
    assert FORBIDDEN.as_posix() in cl["track_a_frozen"]["path"] or cl["track_a_frozen"]["path"].endswith(
        "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
    )
