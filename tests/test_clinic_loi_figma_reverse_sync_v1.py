"""Clinic LOI Figma reverse-sync auto pipeline."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts/check_clinic_loi_figma_reverse_sync_gate_v1.py"
MAP = ROOT / "docs/final/artifacts/clinic_loi_figma_token_map_v1.json"
STUDIO = ROOT / "reports/clinic_loi_figma_tokens_studio_export_v1.json"
SCREENSHOT = ROOT / "reports/clinic_loi_figma_reference_screenshot_v1.png"


def test_figma_reverse_sync_auto_exit_zero():
    proc = subprocess.run(
        [sys.executable, str(GATE)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    out = ROOT / "reports/clinic_loi_figma_reverse_sync_gate_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    assert doc["decision"] == "PASS"
    assert STUDIO.is_file()
    assert SCREENSHOT.is_file()


def test_token_map_matches_dtcg():
    map_doc = json.loads(MAP.read_text(encoding="utf-8-sig"))
    dtcg = json.loads(
        (ROOT / "reports/clinic_km_mmp_landing_tokens_v2.dtcg.json").read_text(encoding="utf-8-sig")
    )
    resolved = dtcg["css_variables_resolved"]
    for row in map_doc["variables"]:
        assert resolved[row["css_var"]] == row["value"]
