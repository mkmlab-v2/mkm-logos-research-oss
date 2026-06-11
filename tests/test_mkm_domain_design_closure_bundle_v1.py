"""Closure report schema smoke for mkm_domain_design_closure_v1."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "mkm_domain_design_closure_v1_latest.json"
BUNDLE = ROOT / "scripts" / "Invoke-MkmDomainDesignClosureBundle_v1.ps1"


def test_closure_bundle_script_exists():
    assert BUNDLE.is_file()


def test_closure_report_schema_when_present():
    if not REPORT.is_file():
        return
    doc = json.loads(REPORT.read_text(encoding="utf-8-sig"))
    assert doc.get("schema") == "mkm_domain_design_closure_v1"
    assert isinstance(doc.get("steps"), list)
    assert "closure_ok" in doc
    assert doc.get("personadiary_lane") == "preview_only_hypo_b_track"
