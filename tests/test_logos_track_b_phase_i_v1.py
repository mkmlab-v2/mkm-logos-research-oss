from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_integration_closure_builds() -> None:
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
    assert doc.get("schema") == "logos_track_b_integration_closure_v1"
    assert doc.get("gates", {}).get("graphrag_organic_42_42") is True


def test_phase_i_chain_exit0() -> None:
    cp = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts/run_logos_track_b_phase_i_v1.py"),
            "--skip-phase-h",
            "--skip-phase-f",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout

    registry = json.loads(
        (
            _ROOT / "docs/final/artifacts/logos_reasoning_pattern_registry_v1_latest.json"
        ).read_text(encoding="utf-8")
    )
    assert len(registry.get("patterns") or []) >= 5

    appendix = (
        _ROOT / "reports/external_validation_ms_evidence_pack_v1_latest/ms_b2b_logos_logic_verifier_appendix_v1.md"
    ).read_text(encoding="utf-8")
    assert "graphrag_seed_organic" in appendix

    phase_i = json.loads((_ROOT / "reports/logos_track_b_phase_i_v1_latest.json").read_text(encoding="utf-8"))
    assert phase_i.get("ok") is True
