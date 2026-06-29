# Keywords: symbolic_energy, imagination_rail, shadow_lane_v2

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_symbolic_energy_slice() -> None:
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_job_prologue_symbolic_energy_slice_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads((ROOT / "docs/final/artifacts/job_prologue_symbolic_energy_v1_latest.json").read_text(encoding="utf-8"))
    assert doc["schema_version"] == "job_prologue_symbolic_energy_v1"
    assert len(doc["high_dim_hypotheses"]) >= 4
    spike = next(h for h in doc["high_dim_hypotheses"] if h["hypothesis_id"] == "H_ENERGY_SPIKE_2_3")
    assert spike["metrics"]["Job.2.3_hebrew_value"] == 10805


def test_imagination_rail_envelope() -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_job_prologue_symbolic_energy_slice_v1.py")],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
    )
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_logos_imagination_rail_envelope_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads((ROOT / "docs/final/artifacts/logos_imagination_rail_envelope_v1_latest.json").read_text(encoding="utf-8"))
    assert doc["schema_version"] == "logos_imagination_rail_envelope_v1"
    assert doc["stats"].get("imagination_path", 0) >= 1
    assert doc["stats"].get("corpus_bound", 0) >= 1


def test_shadow_lane_v2_bundle() -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_research_shadow_lane_v2_bundle_v1.py")],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    doc = json.loads(
        (ROOT / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_research_shadow_lane_v2.json").read_text(
            encoding="utf-8"
        )
    )
    assert doc["schema_version"] == "research_shadow_lane_v2_bundle_v1"
    assert "symbolic_energy" in doc["layers"]
