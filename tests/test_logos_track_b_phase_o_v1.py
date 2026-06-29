from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_psi_extraction() -> None:
    cp = subprocess.run(
        [sys.executable, str(_ROOT / "scripts/build_logos_psi_logic_extraction_v1.py")],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads((_ROOT / "reports/logos_psi_logic_extraction_v1_latest.json").read_text(encoding="utf-8"))
    assert len(doc["logic_graph"]["nodes"]) >= 4
    assert doc.get("structure_transplant_only") is True


def test_phase_o_full() -> None:
    cp = subprocess.run(
        [sys.executable, str(_ROOT / "scripts/run_logos_track_b_phase_o_v1.py")],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    phase_o = json.loads((_ROOT / "reports/logos_track_b_phase_o_v1_latest.json").read_text(encoding="utf-8"))
    assert phase_o.get("ok") is True
    assert int(phase_o.get("ledger_records") or 0) >= 2
    digest = _ROOT / "reports/logos_phase_o_digest_v1_latest.md"
    assert digest.is_file()
    assert "Phase O" in digest.read_text(encoding="utf-8")
    ledger = json.loads((_ROOT / "reports/logos_track_b_research_v1_latest.json").read_text(encoding="utf-8"))
    assert ledger.get("schema") == "logos_track_b_research_v1"


def test_hot_reload_completion() -> None:
    cp = subprocess.run(
        [sys.executable, str(_ROOT / "scripts/run_logos_track_b_hot_reload_v1.py")],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    hot = json.loads((_ROOT / "reports/logos_track_b_hot_reload_v1_latest.json").read_text(encoding="utf-8"))
    assert hot.get("completion_pass") is True
    assert float(hot.get("final_completion_score") or 0) >= 90.0
    completion = json.loads(
        (_ROOT / "reports/logos_phase_o_completion_gate_v1_latest.json").read_text(encoding="utf-8")
    )
    assert completion.get("completion_pass") is True
    chain = json.loads(
        (_ROOT / "reports/logos_b2b_deterministic_chain_v1_latest.json").read_text(encoding="utf-8")
    )
    assert (chain.get("summary") or {}).get("beta_resolved") is True
