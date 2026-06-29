"""P13 resonance_cap floor — SSOT may be >96 after P14; read-only floor gate."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SLICE_ART = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bloom_slice_v1_latest.json"
SLICE_PUBLIC = (
    ROOT / "projects/mkm/mkm-life/public/data/logos_cosmic_anchor_graph_bloom_slice_v1.json"
)


@pytest.fixture(scope="module")
def p13_res_chain() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_logos_resonance_cap_p13_chain_v1.py",
            "--skip-pytest",
            "--skip-cdn-purge",
            "--skip-deploy",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_resonance_cap_at_least_ninety_six(p13_res_chain: None) -> None:
    for path in (SLICE_ART, SLICE_PUBLIC):
        doc = json.loads(path.read_text(encoding="utf-8"))
        cap = int(doc.get("resonance_cap") or 0)
        top_n = len(doc.get("resonance_edges_top") or [])
        assert cap >= 96
        assert top_n >= 96


def test_narrative_still_two_hundred(p13_res_chain: None) -> None:
    doc = json.loads(SLICE_PUBLIC.read_text(encoding="utf-8"))
    assert len(doc.get("narrative_path_samples") or []) >= 200
