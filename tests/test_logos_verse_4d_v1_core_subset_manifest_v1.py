# @MKM12-METADATA
# Type: Logic
# Purpose: logos_verse_4d_v1_core_subset_manifest_v1 freeze regression.
# Keywords: logos, track_b, verse_4d, manifest, v1_core_subset

from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_MANIFEST = _ROOT / "docs/final/artifacts/logos_verse_4d_v1_core_subset_manifest_v1_latest.json"
_CONTRACT = _ROOT / "docs/final/artifacts/LOGOS_VERSE_4D_V1_CONTRACT.json"
_COVERAGE_DIFF = _ROOT / "reports/constitution/btrack_pilot/logos_verse_canon_coverage_diff_v1_latest.json"
_CORPUS_MANIFEST = _ROOT / "docs/final/artifacts/logos_verse_4d_corpus_v1_latest.json"

_REQUIRED_TOP = frozenset(
    {
        "schema",
        "version",
        "subset_id",
        "frozen_at_utc",
        "hypothesis_tier",
        "boundary_ack",
        "counts",
        "input_sha256",
        "coverage_diff",
        "phase_outputs",
        "reproduce",
        "track_wall",
    }
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_manifest_present_and_schema_id() -> None:
    assert _MANIFEST.is_file(), f"missing manifest: {_MANIFEST}"
    doc = _load(_MANIFEST)
    assert doc["schema"] == "logos_verse_4d_v1_core_subset_manifest_v1"
    assert doc["subset_id"] == "v1_core_subset"
    assert doc["hypothesis_tier"] == "B"
    assert doc["boundary_ack"] is True
    missing = _REQUIRED_TOP - set(doc)
    assert not missing, f"missing keys: {sorted(missing)}"


def test_track_wall_not_weakened() -> None:
    doc = _load(_MANIFEST)
    wall = doc["track_wall"]
    assert wall["a_track_auto_promotion"] is False
    assert wall["live_trading_trigger"] is False
    assert wall["ready_for_external_send"] is False
    assert wall.get("compression_apply_gematria_4d_bridge_policy") is False


def test_counts_align_with_coverage_diff_ssot() -> None:
    if not _COVERAGE_DIFF.is_file():
        pytest.skip("coverage diff artifact not present")
    manifest = _load(_MANIFEST)
    diff = _load(_COVERAGE_DIFF)
    for key in ("full_canon_verse_count", "verse_decoded_v2_count", "gap_count"):
        assert manifest["counts"][key] == diff["counts"][key], key
    assert manifest["counts"]["phase1_rows_emitted"] == diff["counts"]["verse_decoded_v2_count"]
    assert manifest["input_sha256"]["verse_decoded_v2_jsonl"] == diff["inputs"]["verse_decoded_v2_sha256"]
    assert manifest["input_sha256"]["full_canon_json"] == diff["inputs"]["full_canon_sha256"]


def test_contract_points_at_same_subset_and_coverage_diff() -> None:
    contract = _load(_CONTRACT)
    assert contract["subset_id"] == "v1_core_subset"
    assert contract["frozen_subset_manifest"].endswith(
        "logos_verse_4d_v1_core_subset_manifest_v1_latest.json"
    )
    cd = contract["coverage_diff"]
    assert cd["artifact_path"] == "reports/constitution/btrack_pilot/logos_verse_canon_coverage_diff_v1_latest.json"
    assert cd["runner"] == "scripts/build_logos_verse_canon_coverage_diff_v1.py"
    assert contract["track_wall"]["ready_for_external_send"] is False


def test_phase1_corpus_manifest_row_count_if_present() -> None:
    if not _CORPUS_MANIFEST.is_file():
        pytest.skip("corpus manifest not present")
    manifest = _load(_MANIFEST)
    corpus = _load(_CORPUS_MANIFEST)
    emitted = corpus["counts"]["rows_emitted"]
    frozen = manifest["counts"]["phase1_rows_emitted"]
    if emitted != frozen:
        # union rebuild (verse_decoded_v2_union) emits full MT 31,102; frozen manifest may stay v1_core_subset 28,741
        assert emitted == 31102 and frozen == 28741
        assert "union" in str(corpus["inputs"].get("primary_jsonl") or "")
    else:
        assert emitted == frozen
        assert (
            manifest["input_sha256"]["verse_decoded_v2_jsonl"]
            == corpus["inputs"]["primary_sha256"]
        )
