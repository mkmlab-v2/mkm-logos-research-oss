# -*- coding: utf-8 -*-
"""Smoke: 4pipeline vs jsonl 4D cross audit (B-track)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_audit_logos_4pipeline_jsonl_cross_smoke() -> None:
    script = ROOT / "scripts" / "audit_logos_4pipeline_jsonl_4d_cross_v1.py"
    out = ROOT / "reports" / "tmp_logos_4pipeline_jsonl_cross_smoke.json"
    cp = subprocess.run(
        [sys.executable, str(script), "--out-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    assert doc.get("schema") == "logos_4pipeline_jsonl_4d_cross_audit_v1"
    assert doc["coverage"]["intersection_compared"] >= 30000
    assert doc["duplicate_stats"]["pipeline4_unified_v2"]["fallback_025_cluster_size"] > 1000
    assert len(doc.get("graphrag_seed_cross_check") or []) >= 10
