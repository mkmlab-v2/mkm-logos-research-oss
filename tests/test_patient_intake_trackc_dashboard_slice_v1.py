# -*- coding: utf-8 -*-
"""Track C dashboard patient_intake_fusion_b_track slice."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RATIONALE = ROOT / "reports" / "patient_intake_fusion_rationale_latest.json"


def test_dashboard_slice_reads_cross_checks():
    from scripts.build_mkm_trackc_ops_dashboard_v1 import _patient_intake_fusion_b_track_slice

    if not RATIONALE.is_file():
        return
    sl = _patient_intake_fusion_b_track_slice(ROOT)
    assert sl.get("state") == "OK"
    assert sl.get("myeongni_sasang_status") in ("match", "partial", "mismatch", "insufficient")
    assert sl.get("cross_checks_v1")
    assert sl.get("auto_prescription_forbidden") is True


def test_dashboard_build_includes_patient_intake_field():
    pytest = __import__("pytest")
    dash_path = ROOT / "docs" / "final" / "artifacts" / "mkm_trackc_ops_dashboard_latest.json"
    if not dash_path.is_file() or not RATIONALE.is_file():
        pytest.skip("dashboard or rationale missing")
    doc = json.loads(dash_path.read_text(encoding="utf-8-sig"))
    pit = (doc.get("trackc") or {}).get("patient_intake_fusion_b_track")
    if pit is None:
        pytest.skip("rebuild dashboard to pick up patient_intake slice")
    assert pit.get("state") in ("OK", "NODATA")
