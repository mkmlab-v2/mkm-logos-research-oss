"""B2B training bundle builder smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_bundle_dry_run():
    proc = subprocess.run(
        [sys.executable, "scripts/build_gwangmyeong_baekje_b2b_training_bundle_v1.py", "--dry-run"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(proc.stdout.strip())
    assert doc["ok"] is True
    assert doc["rib55"]["decision"] == "approved_education_internal"


def test_bundle_full_build():
    proc = subprocess.run(
        [sys.executable, "scripts/build_gwangmyeong_baekje_b2b_training_bundle_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    out = ROOT / "docs/final/artifacts/gwangmyeong_baekje_b2b_training_bundle_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["send_gate"] == "HOLD"
    assert doc["barrier_audit_ok"] is True
    spec = json.loads(
        (ROOT / "docs/final/artifacts/gwangmyeong_baekje_b2b_training_spec_v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert spec["education_assets_b2b_only"]["rib55_adjudication_decision"] == "approved_education_internal"
