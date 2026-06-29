"""Smoke tests for Han Vocology OKF bundle export."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXPORT = ROOT / "scripts" / "export_han_vocology_okf_bundle_v1.py"
BUNDLE = ROOT / "docs/final/artifacts/okf_bundles/han_vocology"
REPORT = ROOT / "docs/final/artifacts/han_vocology_okf_export_v1_latest.json"
KM_VHI = BUNDLE / "instruments" / "km_vhi_v0_1.md"


@pytest.fixture(scope="module")
def okf_export() -> None:
    proc = subprocess.run(
        [sys.executable, str(EXPORT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_okf_bundle_has_required_concepts(okf_export: None) -> None:
    assert KM_VHI.is_file()
    text = KM_VHI.read_text(encoding="utf-8")
    assert "type: Clinical Instrument" in text
    assert "schema: okf_concept_v1" in text
    assert "F1" in text


def test_export_report_ok(okf_export: None) -> None:
    payload = json.loads(REPORT.read_text(encoding="utf-8"))
    assert payload.get("ok") is True
    assert payload.get("concept_count", 0) >= 5
