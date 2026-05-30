"""Smoke: run_magic_orb_question_insight_batch_v1 dry-run."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BATCH = ROOT / "scripts/run_magic_orb_question_insight_batch_v1.py"
FIXTURE = ROOT / "docs/final/fixtures/magic_orb_question_insight_queries_v1.json"


def test_batch_dry_run():
    r = subprocess.run(
        [
            sys.executable,
            str(BATCH),
            "--dry-run",
            "--expand-primary-only",
            "--out-json",
            str(ROOT / "reports/_tmp_batch_dry_run.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0
    out = json.loads(r.stdout.strip().splitlines()[-1])
    assert out["ok"] is True
    assert out["rows"] == len(json.loads(FIXTURE.read_text(encoding="utf-8"))["items"])
