"""FinOps L1 official closeout promotion (commander ack required)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL = ROOT / "docs/final/artifacts/finops_wire_domain_v1_closeout_official_v1_latest.json"


def test_promote_requires_eval_ok():
    cp = subprocess.run(
        [
            sys.executable,
            "scripts/promote_finops_wire_domain_v1_closeout_official_v1.py",
            "--commander-ack",
            "--note",
            "pytest promotion",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert cp.returncode == 0, cp.stderr[-800:]
    doc = json.loads(OFFICIAL.read_text(encoding="utf-8"))
    assert doc.get("approval_status") == "APPROVED_COMMANDER"
    assert doc.get("lane") == "L1_official"
    assert doc.get("research_only") is True
    assert "legal_before_external_send" in (doc.get("remaining_human_gates") or [])
