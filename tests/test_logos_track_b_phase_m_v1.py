from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_integration_closure_phase_l_gates() -> None:
    cp = subprocess.run(
        [sys.executable, str(_ROOT / "scripts/build_logos_track_b_integration_closure_v1.py")],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(
        (_ROOT / "reports/logos_track_b_integration_closure_v1_latest.json").read_text(encoding="utf-8")
    )
    gates = doc.get("gates") or {}
    assert gates.get("graphrag_organic_42_42") is True
    assert gates.get("llm_citation_valid_dan") is True
    assert gates.get("llm_citation_valid_john") is True


def test_phase_m_chain_exit0() -> None:
    cp = subprocess.run(
        [sys.executable, str(_ROOT / "scripts/run_logos_track_b_phase_m_v1.py")],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    phase_m = json.loads((_ROOT / "reports/logos_track_b_phase_m_v1_latest.json").read_text(encoding="utf-8"))
    assert phase_m.get("ok") is True
    manifest = json.loads(
        (_ROOT / "reports/external_validation_ms_evidence_pack_v1_latest/manifest.json").read_text(encoding="utf-8")
    )
    bundle = manifest.get("track_b_logos_bundle") or {}
    assert len(bundle.get("files") or []) >= 8
