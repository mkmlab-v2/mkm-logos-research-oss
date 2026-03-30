"""Minimal FACT-LOCK gates for external lexicon manifest and seed mapping summary."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def test_external_lexicon_manifest_nonempty():
    manifest = REPO / "vault" / "external_lexicon" / "MANIFEST.json"
    if not manifest.is_file():
        pytest.skip("external lexicon staging not present")
    raw = manifest.read_text(encoding="utf-8-sig")
    data = json.loads(raw)
    files = data.get("files") or []
    assert files, "MANIFEST.files must be non-empty"
    assert all("sha256" in f and f.get("sha256") for f in files if isinstance(f, dict)), (
        "each manifest file entry should carry sha256"
    )


def test_external_lexicon_manifest_committed_fixture_shape():
    """CI-safe: does not depend on local vault/ (often gitignored)."""
    fixture = (
        REPO / "tests" / "fixtures" / "external_lexicon" / "MANIFEST.min.json"
    )
    assert fixture.is_file(), "committed manifest fixture must exist"
    data = json.loads(fixture.read_text(encoding="utf-8"))
    assert data.get("schema") == "external_lexicon_manifest_v1"
    files = data.get("files") or []
    assert files, "fixture MANIFEST.files must be non-empty"
    assert all(
        isinstance(f, dict) and f.get("sha256") and len(str(f["sha256"])) == 64
        for f in files
    ), "each file entry needs a 64-char hex sha256"


def test_master_atoms_lexicon_seed_summary_coverage_shape():
    summary_path = (
        REPO / "reports" / "constitution" / "btrack_pilot" / "master_atoms_lexicon_seed_summary_latest.json"
    )
    if not summary_path.is_file():
        pytest.skip("seed summary not generated yet")
    data = json.loads(summary_path.read_text(encoding="utf-8"))
    cov = data.get("coverage") or {}
    g = cov.get("greek") or {}
    h = cov.get("hebrew") or {}
    assert "fraction_of_greek_atoms" in g
    assert "fraction_of_hebrew_atoms" in h


def test_master_atoms_lexicon_coverage_summary_v2_contract_shape():
    """CI-safe: committed fixture matches MASTER_Linguistic_Contract §7.2."""
    fixture = (
        REPO
        / "tests"
        / "fixtures"
        / "lexicon"
        / "master_atoms_lexicon_coverage_summary_v2.min.json"
    )
    assert fixture.is_file(), "coverage summary v2 fixture must exist"
    data = json.loads(fixture.read_text(encoding="utf-8"))
    assert data.get("schema") == "master_atoms_lexicon_coverage_summary_v2"
    assert data.get("generated_at_utc")
    inputs = data.get("inputs") or {}
    assert inputs.get("atoms"), "inputs.atoms required"
    manifest = inputs.get("external_lexicon_manifest") or {}
    assert manifest.get("path") and manifest.get("sha256")
    assert len(str(manifest["sha256"])) == 64
    precedence = data.get("precedence") or []
    assert precedence == [
        "rail_strongs_seed",
        "rail_morphhb",
        "rail_step_audit",
    ]
    by_rail = data.get("by_rail") or {}
    for rid in ("rail_strongs_seed", "rail_morphhb", "rail_step_audit"):
        block = by_rail.get(rid)
        assert isinstance(block, dict), f"by_rail.{rid} must be object"
        assert block.get("rail_id") == rid
        assert "coverage" in block
    assert data.get("corpus_buckets_ref")


def test_master_atoms_corpus_split_summary_v1_contract_shape():
    """CI-safe: matches report_master_atoms_corpus_split output contract."""
    fixture = (
        REPO
        / "tests"
        / "fixtures"
        / "lexicon"
        / "master_atoms_corpus_split_summary_v1.min.json"
    )
    assert fixture.is_file()
    data = json.loads(fixture.read_text(encoding="utf-8"))
    assert data.get("schema") == "master_atoms_corpus_split_summary_v1"
    assert data.get("generated_at_utc")
    inputs = data.get("inputs") or {}
    assert inputs.get("atoms")
    assert inputs.get("source_basename_to_bucket")
    assert isinstance(data.get("atoms_total"), int)
    assert isinstance(data.get("by_bucket_presence"), dict)
    assert isinstance(data.get("by_exclusive_pattern"), dict)
    assert isinstance(data.get("by_lang_exclusive_pattern"), dict)


def test_master_atoms_corpus_split_summary_latest_optional():
    path = (
        REPO
        / "reports"
        / "constitution"
        / "btrack_pilot"
        / "master_atoms_corpus_split_summary_latest.json"
    )
    if not path.is_file():
        pytest.skip("corpus split summary not generated yet")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data.get("schema") == "master_atoms_corpus_split_summary_v1"
    assert data.get("atoms_total", 0) > 0
