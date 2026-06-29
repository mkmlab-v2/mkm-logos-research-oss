from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_evolution_loop_runs_exit0() -> None:
    cp = subprocess.run(
        [sys.executable, str(_ROOT / "scripts/run_logos_b2b_proposal_evolution_loop_v1.py")],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout

    loop = json.loads(
        (_ROOT / "reports/logos_b2b_proposal_evolution_loop_v1_latest.json").read_text(encoding="utf-8")
    )
    assert loop.get("ok") is True
    assert loop.get("verdict") == "PROMOTE_CANDIDATE"

    summary = json.loads(
        (
            _ROOT / "docs/final/artifacts/logos_b2b_proposal_master_summary_v1_latest.json"
        ).read_text(encoding="utf-8")
    )
    assert summary.get("promoted") is True
    assert summary.get("promoted_claim_count", 0) >= 4
    assert summary.get("track_a_bridge") is False

    md = (_ROOT / "reports/logos_b2b_proposal_master_summary_v1_latest.md").read_text(encoding="utf-8")
    assert "NON_GATING" in md
    assert "CLAIM-B2B-SCOPE" in md


def test_verifier_rejects_orphan_clause_ref(tmp_path: Path) -> None:
    bad = {
        "schema": "logos_b2b_proposal_logic_artifact_v1",
        "research_only": True,
        "non_gating": True,
        "track_a_bridge": False,
        "logos_reasoning_transplant": {"pedagogical_only": True},
        "proposal_claims": [
            {
                "claim_id": "CLAIM-BAD",
                "labels": ["TRACK_B", "HYPO"],
                "body_ko": "[HYPO] orphan test",
                "clause_refs": ["NOT-A-REAL-REF"],
                "barrier_ids": [],
            }
        ],
    }
    art = tmp_path / "artifact.json"
    art.write_text(json.dumps(bad), encoding="utf-8")
    cp = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts/verify_logos_b2b_proposal_goal_v1.py"),
            "--in",
            str(art),
            "--out",
            str(tmp_path / "verifier_out.json"),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert cp.returncode == 1, cp.stdout
