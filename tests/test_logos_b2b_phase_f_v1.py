from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_xref_subgraph_builds() -> None:
    cp = subprocess.run(
        [sys.executable, str(_ROOT / "scripts/build_logos_themed_xref_subgraph_v1.py"), "--min-votes", "50"],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(
        (_ROOT / "reports/logos_themed_xref_subgraph_v1_latest.json").read_text(encoding="utf-8")
    )
    assert doc.get("total_edges", 0) >= 20


def test_phase_f_chain_exit0() -> None:
    cp = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts/run_logos_b2b_phase_f_v1.py"),
            "--skip-phase-e",
            "--xref-min-votes",
            "50",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout

    enrich = json.loads(
        (_ROOT / "reports/logos_themed_xref_router_enrichment_v1_latest.json").read_text(encoding="utf-8")
    )
    assert len(enrich.get("results") or []) == 2

    john_router = json.loads(
        (
            _ROOT / "docs/final/artifacts/logos_subgraph_graphrag_router_john_1_logos_latest.json"
        ).read_text(encoding="utf-8")
    )
    assert john_router.get("xref_enrichment", {}).get("neighbor_count", 0) >= 1

    appendix = _ROOT / "reports/external_validation_ms_evidence_pack_v1_latest/ms_b2b_logos_logic_verifier_appendix_v1.md"
    assert appendix.is_file()
    body = appendix.read_text(encoding="utf-8")
    assert "Goal Verifier" in body and "PROMOTE" in body or "promoted" in body.lower()
