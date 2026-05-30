"""Smoke: saturation handoff pack builder."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_logos_candidate_edge_saturation_handoff_v1() -> None:
    cp = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_logos_candidate_edge_saturation_handoff_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads((ROOT / "reports/logos_candidate_edge_saturation_handoff_v1_latest.json").read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_candidate_edge_saturation_handoff_v1"
    assert doc.get("ready_for_external_send") is False
    assert (ROOT / "reports/logos_candidate_edge_saturation_handoff_v1_latest.md").is_file()
