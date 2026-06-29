"""Weekly baseline recorder smoke tests."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "scripts/record_agent_handoff_governance_weekly_baseline_v1.py"
BENCH = ROOT / "reports/mkm_ops_memory_index_token_bench_v1_latest.json"


def test_dry_run_builds_row():
    assert BENCH.is_file(), "run bench first"
    r = subprocess.run(
        [sys.executable, str(RECORD), "--dry-run", "--lane", "infra", "--ops-memory-exit-code", "0"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr or r.stdout
    row = json.loads(r.stdout)
    assert row["schema"] == "agent_handoff_governance_weekly_baseline_v1"
    assert row["inject_off_tokens"] is not None
