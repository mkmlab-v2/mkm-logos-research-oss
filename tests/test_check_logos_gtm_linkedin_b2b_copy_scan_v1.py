"""Smoke: Logos GTM LinkedIn/B2B copy guardrail scan."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_copy_scan_passes_on_sealed_artifact() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/check_logos_gtm_linkedin_b2b_copy_scan_v1.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    report = json.loads((ROOT / "reports/logos_gtm_linkedin_b2b_copy_scan_v1_latest.json").read_text(encoding="utf-8"))
    assert report["scan_ok"] is True
    assert report["ready_for_external_send"] is False
