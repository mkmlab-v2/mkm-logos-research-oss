"""Fundamental-force pedagogical lexicon + HG-6 primitive report (HYPO)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEXICON = ROOT / "docs/final/artifacts/logos_fundamental_force_lexicon_v1.json"
SCHEMA = ROOT / "docs/final/schemas/logos_fundamental_force_lexicon_v1.schema.json"
REPORT = ROOT / "docs/final/artifacts/logos_fundamental_force_primitive_report_v1_latest.json"
MANIFEST = ROOT / "docs/final/artifacts/logos_cosmic_anchor_batch_v1_manifest_latest.json"


@pytest.fixture(scope="module")
def physics_chain() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/run_logos_physics_alignment_chain_v1.py", "--skip-pytest"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_lexicon_schema_and_guards() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    doc = json.loads(LEXICON.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)
    assert doc["hypothesis_class"] == "HYPO"
    assert doc["pedagogical_isomorphism_only"] is True
    assert doc["kernel_recipe_id"] == "gematria_bridge_v1"
    assert len(doc["entries"]) == 4


def test_primitive_to_force_module() -> None:
    from scripts.core.logos_fundamental_force_lexicon_v1 import (
        force_to_primitive,
        format_force_copy_ko,
        primitive_to_force,
    )

    row = primitive_to_force("harmony")
    assert row is not None
    assert row["force_id"] == "gravity"
    assert force_to_primitive("strong_force") == "pathology"
    assert "[HYPO]" in format_force_copy_ko("survival")


def test_hg6_report_339_anchors(physics_chain: None) -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report["schema"] == "logos_fundamental_force_primitive_report_v1"
    assert report["anchor_count"] == manifest["anchor_count"] == 339
    assert report["materialize_batch"] is False
    assert report["kernel_recipe_id"] == "gematria_bridge_v1"
    summary = report["summary"]
    assert sum(summary["primitive_top1_counts"].values()) == 339
    assert sum(summary["force_top1_counts"].values()) == 339
    assert summary["harmony_top1_share"] <= 0.65
    assert len(report["per_anchor"]) == 339
