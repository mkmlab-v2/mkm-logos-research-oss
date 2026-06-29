"""BigSet ingest — conflict_surface schema + citation_lock gate wiring."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHAIN = ROOT / "scripts/run_bigset_ingest_spike_chain_v1.py"
CITATION_CHECK = ROOT / "scripts/check_bigset_tier0_citation_lock_v1.py"
FIXTURE_FAIL_CSV = ROOT / "tests/fixtures/bigset/sample_tier0_low_citation_lock_v1.csv"


def test_bigset_ingest_spike_chain_exit_zero():
    proc = subprocess.run(
        [sys.executable, str(CHAIN), "--skip-bridge"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_citation_lock_gate_passes_fixture():
    csv_path = ROOT / "docs/research/raw/bigset_benei_haelohim_cross_refs_tier0_v1.csv"
    proc = subprocess.run(
        [sys.executable, str(CITATION_CHECK), "--csv", str(csv_path), "--offline"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    art = ROOT / "docs/final/artifacts/bigset_tier0_citation_lock_v1_latest.json"
    doc = json.loads(art.read_text(encoding="utf-8"))
    assert doc.get("gate_ok") is True
    assert doc.get("pass_rate", 0) >= 0.85


def test_timeline_order_gate_passes_fixture_csv():
    tl = ROOT / "scripts/check_bigset_tier0_timeline_order_v1.py"
    csv_path = ROOT / "tests/fixtures/bigset/sample_theology_tier0_rows_v1.csv"
    proc = subprocess.run(
        [sys.executable, str(tl), "--csv", str(csv_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_conflict_surface_has_schools():
    art = ROOT / "docs/final/artifacts/bigset_conflict_surface_v1_latest.json"
    assert art.is_file()
    doc = json.loads(art.read_text(encoding="utf-8"))
    assert doc.get("schema") == "bigset_conflict_surface_v1"
    groups = doc.get("groups") or []
    assert groups
    schools = groups[0].get("schools") or []
    tiers = {s.get("school_tier") for s in schools}
    assert "historical_criticism" in tiers
    assert "judaic_mysticism" in tiers


def test_citation_lock_fails_below_threshold(tmp_path: Path):
    assert FIXTURE_FAIL_CSV.is_file()
    out = tmp_path / "citation_lock.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(CITATION_CHECK),
            "--csv",
            str(FIXTURE_FAIL_CSV),
            "--out",
            str(out),
            "--offline",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("gate_ok") is False
    assert doc.get("promotion_mode") == "shadow_only"
