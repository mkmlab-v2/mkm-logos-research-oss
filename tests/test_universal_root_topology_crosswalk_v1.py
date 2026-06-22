"""Universal Root topology crosswalk v1 — build + gate smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SPEC = REPO / "docs/final/artifacts/UNIVERSAL_ROOT_TOPOLOGY_CROSSWALK_SPEC_V1.json"
BUILDER = REPO / "scripts/build_universal_root_topology_crosswalk_v1.py"
CHECKER = REPO / "scripts/check_universal_root_topology_crosswalk_v1.py"
REPORT = REPO / "reports/universal_root_topology_crosswalk_v1_latest.json"
GATE = REPO / "reports/universal_root_topology_crosswalk_gate_v1_latest.json"


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True)


def test_topology_spec_exists():
    assert SPEC.is_file()
    doc = json.loads(SPEC.read_text(encoding="utf-8"))
    assert doc["schema"] == "universal_root_topology_crosswalk_spec_v1"
    assert doc["send_gate"] == "HOLD"
    assert "lexicon_plane_41k" in doc["walls"]
    assert "topology_plane_31k" in doc["walls"]


def test_build_and_gate_smoke():
    r = _run([sys.executable, str(BUILDER)])
    assert r.returncode == 0, r.stderr
    assert REPORT.is_file()
    doc = json.loads(REPORT.read_text(encoding="utf-8"))
    assert doc["schema"] == "universal_root_topology_crosswalk_v1"
    assert doc["lexicon_plane"]["plane"] == "lexicon_41k"
    assert doc["topology_plane"]["plane"] == "topology_31k"
    assert doc["wall_divergence"]["plane_separation_reported"] is True
    assert doc["wall_divergence"]["collapsed_combined_score"] is None

    g = _run([sys.executable, str(CHECKER)])
    assert GATE.is_file()
    gate_doc = json.loads(GATE.read_text(encoding="utf-8"))
    assert gate_doc["send_gate"] == "HOLD"
    assert g.returncode == (0 if gate_doc["gate_ok"] else 1)
