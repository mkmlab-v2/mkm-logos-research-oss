from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_mkm_append_governance_audit_log_v1_dry_run():
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/mkm_append_governance_audit_log_v1.py"),
            "--mission-id",
            "test_mission",
            "--stage",
            "test_stage",
            "--decision",
            "test_decision",
            "--evidence-path",
            "scripts/log_agent_decision.py",
            "--actor",
            "pytest",
            "--note",
            '{"k":"v"}',
            "--dry-run",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    line = r.stdout.strip().splitlines()[-1]
    doc = json.loads(line)
    assert doc["mission_id"] == "test_mission"
    assert doc["decision"] == "test_decision"


def test_mkm_append_governance_audit_log_v1_skip():
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/mkm_append_governance_audit_log_v1.py"),
            "--skip",
            "--mission-id",
            "x",
            "--stage",
            "x",
            "--decision",
            "x",
            "--evidence-path",
            "x",
            "--actor",
            "x",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0
