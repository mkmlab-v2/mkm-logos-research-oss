"""P3 Root Generator v0 — build + chain (B-track)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
BUILD = REPO / "scripts/build_p3_root_candidate_lexicon_v1.py"
CHAIN = REPO / "scripts/run_p3_root_generator_chain_v1.py"
FIXTURE = REPO / "tests/fixtures/p3_root_extension_probe_v1.jsonl"
BUILD_REPORT = REPO / "reports/p3_root_candidate_lexicon_build_v1_latest.json"
BASELINE = REPO / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41658_rows_latest.json"


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True)


@pytest.mark.skipif(not BASELINE.is_file(), reason="41658 baseline export missing")
def test_build_probe_jsonl_only():
    r = _run(
        [
            sys.executable,
            str(BUILD),
            "--slug",
            "pytest_jsonl",
            "--extension-jsonl",
            str(FIXTURE),
        ]
    )
    assert r.returncode == 0, r.stderr
    report = json.loads(BUILD_REPORT.read_text(encoding="utf-8"))
    assert report["candidate_row_count"] > report["baseline_row_count"]
    assert report["rows_added"] >= 3
    candidate = REPO / report["candidate_path"]
    doc = json.loads(candidate.read_text(encoding="utf-8"))
    meta = doc.get("p3_root_generator_meta") or {}
    assert meta.get("profile") == "extension"
    assert meta.get("baseline_row_count") == report["baseline_row_count"]
    base_ids = {e["atom_id"] for e in json.loads(BASELINE.read_text(encoding="utf-8"))["entries"]}
    cand_ids = {e["atom_id"] for e in doc["entries"]}
    assert base_ids.issubset(cand_ids)


@pytest.mark.skipif(not BASELINE.is_file(), reason="41658 baseline export missing")
def test_replacement_logos_seed_build():
    r = _run(
        [
            sys.executable,
            str(BUILD),
            "--profile",
            "replacement",
            "--seed-logos-atoms-from-baseline",
            "--slug",
            "pytest_logos_seed",
            "--extension-jsonl",
            str(FIXTURE),
        ]
    )
    assert r.returncode == 0, r.stderr
    report = json.loads(BUILD_REPORT.read_text(encoding="utf-8"))
    meta = report.get("meta") or {}
    assert meta.get("merge_policy") == "replacement_logos_seed_plus_extensions_v1"
    assert int(meta.get("logos_seed_row_count") or 0) > 1000
    assert report["candidate_row_count"] > report["baseline_row_count"] * 0.2


@pytest.mark.skipif(not BASELINE.is_file(), reason="41658 baseline export missing")
def test_replacement_profile_build():
    r = _run(
        [
            sys.executable,
            str(BUILD),
            "--profile",
            "replacement",
            "--slug",
            "pytest_replacement",
            "--extension-jsonl",
            str(FIXTURE),
        ]
    )
    assert r.returncode == 0, r.stderr
    report = json.loads(BUILD_REPORT.read_text(encoding="utf-8"))
    assert report["candidate_row_count"] < report["baseline_row_count"]
    candidate = REPO / report["candidate_path"]
    doc = json.loads(candidate.read_text(encoding="utf-8"))
    meta = doc.get("p3_root_generator_meta") or {}
    assert meta.get("profile") == "replacement"
    assert meta.get("merge_policy") == "replacement_extensions_only_v1"


@pytest.mark.skipif(not BASELINE.is_file(), reason="41658 baseline export missing")
def test_full_chain_probe():
    r = _run(
        [
            sys.executable,
            str(CHAIN),
            "--slug",
            "pytest_chain",
            "--skip-alias-table",
            "--compression-sample",
            "2",
        ]
    )
    assert r.returncode == 0, r.stderr
