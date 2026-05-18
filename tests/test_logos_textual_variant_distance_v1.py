"""B-track NT textual-variant distance layer — schema + builder smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "docs/final/schemas/logos_textual_variant_distance_v1.schema.json"
SCRIPT = ROOT / "scripts/build_logos_textual_variant_distance_v1.py"
DRIFT_SCRIPT = ROOT / "scripts/build_logos_satellite_orbit_drift_v1.py"
OUT = ROOT / "docs/final/artifacts/logos_textual_variant_distance_v1_latest.json"
DRIFT_OUT = ROOT / "docs/final/artifacts/logos_satellite_orbit_drift_v1_latest.json"
POLICY = ROOT / "data/logos/logos_gap_mt_only_policy_v1.jsonl"


@pytest.mark.skipif(not POLICY.is_file(), reason="MT-only policy registry missing")
def test_build_textual_variant_distance_smoke() -> None:
    rc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 0, rc.stderr or rc.stdout
    assert OUT.is_file()
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_textual_variant_distance_v1"
    assert doc["track_wall"]["merge_into_complete_jsonl"] is False
    assert len(doc["entries"]) == doc["canonical_ssot"]["complete_gap_count"]
    assert all(e["testament"] == "NT" for e in doc["entries"])
    allowed = {
        "pending_tr_source",
        "sblgnt_neighbor_proxy",
        "nt_adjacent_lexical_proxy",
        "tr_lexical_present",
        "tr_lexical_with_adjacent_proxy",
    }
    assert all(e["distance"]["status"] in allowed for e in doc["entries"])
    assert doc["aggregate"]["distance_status_counts"]


@pytest.mark.skipif(not SCHEMA.is_file(), reason="schema missing")
def test_textual_variant_distance_schema_loads() -> None:
    doc = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert doc["title"]
    assert doc["properties"]["schema"]["const"] == "logos_textual_variant_distance_v1"


def test_build_satellite_orbit_drift_smoke() -> None:
    rc = subprocess.run(
        [sys.executable, str(DRIFT_SCRIPT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 0, rc.stderr or rc.stdout
    assert DRIFT_OUT.is_file()
    doc = json.loads(DRIFT_OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_satellite_orbit_drift_v1"
    assert doc["canonical_anchor"]["global_medoid_verse_id"]
