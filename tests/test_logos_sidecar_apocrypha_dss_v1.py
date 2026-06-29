"""Tier 2/3 apocrypha + DSS sidecar ingest (HYPO only)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "data/logos/sidecar_apocrypha_dss_hypo_v1.seed.jsonl"
SIDECAR = ROOT / "data/logos/sidecar_apocrypha_dss_hypo_v1.jsonl"
REPORT = ROOT / "docs/final/artifacts/logos_sidecar_apocrypha_dss_ingest_v1_latest.json"


def test_sidecar_seed_validates() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/ingest_logos_sidecar_apocrypha_dss_hypo_v1.py",
            "--input",
            str(SEED),
            "--dry-run",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_sidecar_ingest_idempotent() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/ingest_logos_sidecar_apocrypha_dss_hypo_v1.py",
            "--input",
            str(SEED),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert SIDECAR.is_file()
    lines = [ln for ln in SIDECAR.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) >= 2
    for line in lines:
        row = json.loads(line)
        assert row["hypothesis_class"] == "HYPO"
        assert row["non_gating"] is True
        assert row["tier"] in ("tier2_apocrypha", "tier3_dss")
    assert REPORT.is_file()
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report["materialize_batch"] is False
    assert report["sidecar_total_count"] >= 2
