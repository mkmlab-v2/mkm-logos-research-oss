"""check_linkedin_b2b_draft_copy_v1 — draft guard."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "scripts/check_linkedin_b2b_draft_copy_v1.py"
DRAFTS = ROOT / "reports/marketing/linkedin_drafts"


def test_pass_on_existing_draft_if_present():
    candidates = sorted(DRAFTS.glob("*_[DRAFT].md"))
    if not candidates:
        return
    proc = subprocess.run(
        [sys.executable, str(CHECK), str(candidates[0])],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_fail_without_draft_marker(tmp_path):
    bad = tmp_path / "bad.md"
    bad.write_text("Great returns guaranteed for everyone.\n", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(CHECK), str(bad)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1
