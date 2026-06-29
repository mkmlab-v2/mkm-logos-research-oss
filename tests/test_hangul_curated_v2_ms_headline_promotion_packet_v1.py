"""MS headline promotion packet — v2 ACTIVE prerequisites."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ms_headline_packet_builds_or_aborts_cleanly():
    proc = subprocess.run(
        [sys.executable, "scripts/build_hangul_curated_v2_ms_headline_promotion_packet_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode in (0, 2)
    out = ROOT / "reports/hangul_curated_v2_ms_headline_promotion_packet_v1_latest.json"
    if proc.returncode == 0:
        doc = json.loads(out.read_text(encoding="utf-8"))
        assert doc.get("promotion_ready") is True
        assert doc.get("proposed_ms_lane_headline", {}).get("global_token_saving_rate") is not None


def test_ms_headline_apply_dry_run_when_signoff_approved():
    signoff = ROOT / "docs/final/artifacts/hangul_curated_v2_ms_headline_promotion_signoff_v1_latest.json"
    if not signoff.is_file():
        return
    if not json.loads(signoff.read_text(encoding="utf-8")).get("approved"):
        return
    proc = subprocess.run(
        [sys.executable, "scripts/apply_hangul_curated_v2_ms_headline_signoff_v1.py", "--dry-run"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
