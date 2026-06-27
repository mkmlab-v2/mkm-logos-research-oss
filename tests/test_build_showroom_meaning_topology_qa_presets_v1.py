"""Smoke tests for showroom meaning topology Q&A presets builder."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_showroom_meaning_topology_qa_presets_v1.py"
SLICE = ROOT / "docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json"
JOB_SLICE = ROOT / "docs/final/artifacts/showroom_logos_job_reading_pack_slice_v1_latest.json"


def test_build_presets_from_slice(tmp_path: Path) -> None:
    out = tmp_path / "presets.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--slice-json",
            str(SLICE),
            "--out-mvp",
            str(out),
            "--out-artifact",
            str(tmp_path / "mirror.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema_version"] == "showroom_meaning_topology_qa_presets_v1"
    assert len(doc["presets"]) >= 3
    assert doc["disclaimer"]["no_trade_signals"] is True
    first = doc["presets"][0]
    assert "highlight_node_ids" in first and len(first["highlight_node_ids"]) > 0


def test_build_presets_merge_job_reading_pack(tmp_path: Path) -> None:
    if not JOB_SLICE.is_file():
        return
    out = tmp_path / "presets.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--slice-json",
            str(SLICE),
            "--job-reading-pack-json",
            str(JOB_SLICE),
            "--out-mvp",
            str(out),
            "--out-artifact",
            str(tmp_path / "mirror.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    job_presets = [p for p in doc["presets"] if p.get("job_reading_pack_url")]
    assert len(job_presets) > 0
    assert all("public_showroom_logos_job_reading_pack_v1.html" in p["job_reading_pack_url"] for p in job_presets)
