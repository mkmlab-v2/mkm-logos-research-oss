# Keywords: aihub_2026_beta_catalog_v1, btrack, jsonschema

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "docs" / "final" / "schemas" / "aihub_2026_beta_catalog_v1.schema.json"
CATALOG = (
    ROOT
    / "projects"
    / "bitcoin-trading"
    / "memory"
    / "v2"
    / "btrack"
    / "raw_feeds"
    / "aihub"
    / "aihub_2026_beta_catalog_v1.json"
)
FIT_REPORT = (
    ROOT
    / "projects"
    / "bitcoin-trading"
    / "memory"
    / "v2"
    / "btrack"
    / "raw_feeds"
    / "aihub"
    / "aihub_cot_fabric_fit_report_v1.json"
)


@pytest.mark.skipif(not SCHEMA.is_file(), reason="schema missing")
def test_catalog_validates_against_schema() -> None:
    try:
        import jsonschema
    except ImportError:
        pytest.skip("jsonschema not installed")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    jsonschema.validate(instance=catalog, schema=schema)
    assert catalog["research_only"] is True
    assert catalog["track_a_active_write"] is False
    assert len(catalog["entries"]) == 5


def test_check_catalog_cli_exit_zero() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_aihub_2026_beta_catalog_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_cot_fit_with_sample_exit_zero() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_aihub_cot_fabric_sample_fit_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert "OK: inspected_rows=" in proc.stdout
    assert "GOLDEN_PREVIEW_OK:" in proc.stdout
    assert "COMPATIBLE:" in proc.stdout


def test_cot_golden_preview_builder_exit_zero() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_aihub_cot_golden_preview_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert "OK: rows=" in proc.stdout


def test_patent_fit_pending_without_sample_exit_zero() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_aihub_patent_drawing_sample_fit_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert "PENDING" in proc.stdout


def test_fit_report_cot_compatible_after_golden_preview() -> None:
    report = json.loads(FIT_REPORT.read_text(encoding="utf-8"))
    assert report["overall_fit"] == "compatible"
    assert report["sample_status"] == "received"
