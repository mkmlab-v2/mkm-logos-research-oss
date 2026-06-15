from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/final/artifacts/compression_deep_pack_tri_vertical_signoff_checklist_v1_latest.json"
BUILDER = ROOT / "scripts/build_compression_deep_pack_tri_vertical_signoff_checklist_v1.py"


def _refresh_child_checklists() -> None:
    steps = [
        [sys.executable, str(ROOT / "scripts/run_zone_f_code_template_catalog_coverage_v1.py")],
        [sys.executable, str(ROOT / "scripts/build_compression_coding_deep_pack_gate_v1.py")],
        [sys.executable, str(ROOT / "scripts/build_compression_coding_deep_pack_signoff_checklist_v1.py")],
        [sys.executable, str(ROOT / "scripts/build_compression_en_business_deep_pack_gate_v1.py")],
        [sys.executable, str(ROOT / "scripts/build_compression_ko_premium_cs_deep_pack_gate_v1.py")],
    ]
    for cmd in steps:
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
        assert proc.returncode == 0, proc.stderr or proc.stdout


def test_build_tri_vertical_signoff_checklist_exit_zero() -> None:
    _refresh_child_checklists()
    proc = subprocess.run(
        [sys.executable, str(BUILDER)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert OUT.is_file()
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "compression_deep_pack_tri_vertical_signoff_checklist_v1"
    assert doc["all_green"] is True
    assert doc["decision"] == "READY_FOR_COMMANDER_SIGNOFF"
    assert doc["checklist"]["wire_families_distinct"] is True
    assert doc["checklist"]["zone_f_coverage_artifact_linked"] is True
    assert doc["checklist"]["zone_f_coverage_coding_corpora_full"] is True
    assert doc["checklist"]["zone_f_catalog_growth_pipeline_linked"] is True
    zf = doc["verticals"]["zone_f_code"]
    assert zf.get("coverage_artifact")
    assert zf.get("pipeline_builder")
    assert float(zf.get("coverage_wire_match_rate") or 0) >= 1.0
    assert set(doc["verticals"].keys()) == {
        "zone_f_code",
        "zone_h_en_business_v1",
        "zone_ko_premium_cs_v1",
    }
    assert doc["send_gate"] == "HOLD"
