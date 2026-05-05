from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "promote_logos_symbolic_with_human_approval_v1.py"


def test_promote_requires_no_duplicate_approval(tmp_path: Path) -> None:
    gate = tmp_path / "gate.json"
    gate.write_text(
        json.dumps(
            {
                "schema": "logos_symbolic_event_promotion_gate_v1",
                "decision": "GO_RESEARCH_PROMOTION_CANDIDATE",
                "all_pass": True,
                "metrics_snapshot": {"n_evaluated": 42},
            }
        ),
        encoding="utf-8",
    )
    approval_json = tmp_path / "approval.json"
    approval_md = tmp_path / "approval.md"
    candidate_json = tmp_path / "candidate.json"
    candidate_md = tmp_path / "candidate.md"

    first = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--approver",
            "tester",
            "--gate-json",
            str(gate),
            "--approval-json",
            str(approval_json),
            "--approval-md",
            str(approval_md),
            "--candidate-json",
            str(candidate_json),
            "--candidate-md",
            str(candidate_md),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert first.returncode == 0, first.stdout + first.stderr

    second = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--approver",
            "tester",
            "--gate-json",
            str(gate),
            "--approval-json",
            str(approval_json),
            "--approval-md",
            str(approval_md),
            "--candidate-json",
            str(candidate_json),
            "--candidate-md",
            str(candidate_md),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert second.returncode != 0
    assert "already applied" in (second.stdout + second.stderr)

