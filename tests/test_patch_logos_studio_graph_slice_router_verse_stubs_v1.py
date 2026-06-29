"""Router verse stub patch for Logos Studio graph slice coverage."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_patch_job_preset_unmapped_refs() -> None:
    patch_py = ROOT / "scripts" / "patch_logos_studio_graph_slice_router_verse_stubs_v1.py"
    check_py = ROOT / "scripts" / "check_logos_studio_graph_slice_router_coverage_v1.py"
    proc = subprocess.run([sys.executable, str(patch_py)], cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(proc.stdout.strip().splitlines()[-1])
    assert doc["ok"] is True

    gate = subprocess.run([sys.executable, str(check_py)], cwd=ROOT, capture_output=True, text=True)
    assert gate.returncode == 0, gate.stderr or gate.stdout
    gate_doc = json.loads(gate.stdout.strip())
    assert gate_doc["ok"] is True

    slice_doc = json.loads(
        (ROOT / "docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json").read_text(
            encoding="utf-8-sig",
        ),
    )
    ids = {str(n.get("id")) for n in slice_doc.get("nodes") or []}
    assert "showroom_router_stub_verse::Jer.31.4" in ids
