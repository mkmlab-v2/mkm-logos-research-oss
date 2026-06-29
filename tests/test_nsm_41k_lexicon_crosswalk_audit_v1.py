"""NSM 100-pair ↔ 41k lexicon crosswalk audit (B-track)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
AUDIT = REPO / "scripts/run_nsm_41k_lexicon_crosswalk_audit_v1.py"
FIXTURE = REPO / "tests/fixtures/nsm_41k_lexicon_crosswalk_100_v1.json"
REPORT = REPO / "reports/nsm_41k_lexicon_crosswalk_audit_v1_latest.json"
CATALOG = REPO / "scripts/nsm_41k_crosswalk_catalog_v1.py"


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True)


def test_catalog_has_100_pairs():
    spec = {}
    exec(CATALOG.read_text(encoding="utf-8"), spec)
    assert len(spec["NSM_CROSSWALK_100"]) == 100


def test_export_fixture_and_audit_smoke(tmp_path: Path):
    fixture = tmp_path / "crosswalk_100.json"
    out = tmp_path / "audit.json"
    r = _run([sys.executable, str(AUDIT), "--export-fixture", "--fixture", str(fixture)])
    assert r.returncode == 0, r.stderr
    doc = json.loads(fixture.read_text(encoding="utf-8"))
    assert doc["schema"] == "nsm_41k_lexicon_crosswalk_100_v1"
    assert doc["pair_count"] == 100

    r2 = _run(
        [
            sys.executable,
            str(AUDIT),
            "--fixture",
            str(fixture),
            "--out",
            str(out),
            "--expected-pairs",
            "100",
        ]
    )
    assert r2.returncode in (0, 1)
    audit = json.loads(out.read_text(encoding="utf-8"))
    assert audit["schema"] == "nsm_41k_lexicon_crosswalk_audit_v1"
    assert audit["baseline"]["pair_count"] == 100
    assert "english_only_distortion_rate" in audit["baseline"]


def test_build_500_fixture_smoke(tmp_path: Path):
    fixture = tmp_path / "crosswalk_500.json"
    out = tmp_path / "audit_500.json"
    r = _run([sys.executable, "scripts/build_nsm_41k_crosswalk_500_fixture_v1.py", "--out", str(fixture)])
    assert r.returncode == 0, r.stderr
    doc = json.loads(fixture.read_text(encoding="utf-8"))
    assert doc["schema"] == "nsm_41k_lexicon_crosswalk_500_v1"
    assert doc["pair_count"] == 500

    r2 = _run(
        [
            sys.executable,
            str(AUDIT),
            "--fixture",
            str(fixture),
            "--out",
            str(out),
            "--expected-pairs",
            "500",
        ]
    )
    assert r2.returncode in (0, 1)
    audit = json.loads(out.read_text(encoding="utf-8"))
    assert audit["baseline"]["pair_count"] == 500


@pytest.mark.skipif(not (REPO / "reports/constitution/btrack_pilot").exists(), reason="btrack_pilot missing")
def test_default_fixture_audit_latest():
    _run([sys.executable, str(AUDIT), "--export-fixture"])
    r = _run([sys.executable, str(AUDIT)])
    assert r.returncode in (0, 1)
    assert REPORT.is_file()
