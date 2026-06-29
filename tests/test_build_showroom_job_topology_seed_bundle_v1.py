"""Job topology seed bundle builder tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build_showroom_job_topology_seed_bundle_v1.py"
JOB_SLICE = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
    / "showroom_logos_job_reading_pack_slice_v1.json"
)
CORE = ROOT / "scripts/core/showroom_job_topology_seed_v1.py"


def test_core_paths_exist() -> None:
    assert BUILDER.is_file()
    assert CORE.is_file()
    assert JOB_SLICE.is_file()


def test_build_job_seed_bundle_has_five_stages(tmp_path: Path) -> None:
    out = tmp_path / "bundle.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--job-slice-json",
            str(JOB_SLICE),
            "--out-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "showroom_job_topology_seed_bundle_v1"
    assert doc["stage_count"] == 5
    assert doc["verse_ref_count"] >= 10
    assert any(n.get("kind") == "stage" for n in doc["nodes"])
    assert any(n.get("kind") == "verse" and str(n.get("ref", "")).startswith("Job.") for n in doc["nodes"])
    assert any(e.get("edge_type") == "narrative_path" for e in doc["edges"])


def test_slice_includes_job_spine(tmp_path: Path) -> None:
    bundle_out = tmp_path / "bundle.json"
    subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--job-slice-json",
            str(JOB_SLICE),
            "--out-json",
            str(bundle_out),
        ],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    slice_out = tmp_path / "slice.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_showroom_meaning_topology_graph_slice_v1.py"),
            "--job-seed-bundle",
            str(bundle_out),
            "--max-nodes",
            "320",
            "--out-json",
            str(slice_out),
            "--no-mirror-artifact",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(slice_out.read_text(encoding="utf-8"))
    ids = {n["id"] for n in doc["nodes"]}
    assert any(i.startswith("stage::job::") for i in ids)
    assert any(i.startswith("showroom_job_verse::Job.") for i in ids)
    assert doc["selection"].get("job_seed_bundle")
