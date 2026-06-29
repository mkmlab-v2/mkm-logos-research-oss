# -*- coding: utf-8 -*-
"""Smoke: logos 4D fallback re-encode queue (B-track export only)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_build_logos_4d_fallback_reencode_queue_smoke() -> None:
    script = ROOT / "scripts" / "build_logos_4d_fallback_reencode_queue_v1.py"
    out_j = ROOT / "reports" / "tmp_logos_4d_fallback_reencode_queue_smoke.jsonl"
    out_m = ROOT / "reports" / "tmp_logos_4d_fallback_reencode_queue_smoke.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(script),
            "--out-jsonl",
            str(out_j),
            "--out-meta",
            str(out_m),
            "--max-rows",
            "20",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    assert cp.returncode == 0, cp.stderr
    meta = json.loads(out_m.read_text(encoding="utf-8-sig"))
    assert meta.get("schema") == "logos_4d_fallback_reencode_queue_v1"
    queued = int(meta["counts"]["rows_queued"])
    if queued == 0:
        pytest.skip("no pipeline4 0.25 fallback rows in corpus — queue smoke N/A")
    assert queued == 20
    lines = out_j.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 20
    row = json.loads(lines[0])
    assert row.get("queue_status") == "pending_pipeline4_reencode"
    assert row.get("reason") == "pipeline4_unified_v2_fallback_vector_025"
