# -*- coding: utf-8 -*-
"""Smoke: fallback reconcile patch from jsonl (B-track)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_run_logos_4d_fallback_reconcile_smoke() -> None:
    script = ROOT / "scripts" / "run_logos_4d_fallback_reconcile_from_jsonl_v1.py"
    patch = ROOT / "reports" / "tmp_logos_4pipeline_4d_fallback_patch_smoke.jsonl"
    status = ROOT / "reports" / "tmp_logos_4d_fallback_reencode_status_smoke.json"
    pending = ROOT / "reports" / "tmp_logos_4d_pending_encoder_smoke.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(script),
            "--patch-out",
            str(patch),
            "--status-out",
            str(status),
            "--pending-out",
            str(pending),
            "--max-rows",
            "50",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(status.read_text(encoding="utf-8-sig"))
    assert doc.get("schema") == "logos_4d_fallback_reencode_status_v1"
    assert doc["fact_lock"]["full_pipeline_mutated"] is False
    patched = int(doc["counts"]["patched_from_jsonl"])
    if patched == 0:
        pytest.skip("no jsonl-vs-pipeline fallback reconcile rows — smoke N/A")
    assert patched >= 40
    assert len(patch.read_text(encoding="utf-8").strip().splitlines()) >= 40
