# -*- coding: utf-8 -*-
"""Smoke: seed-neighbor retrieval audit on bridge v2 overlay."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_logos_4d_seed_neighbor_retrieval_v1.py"
OVERLAY = ROOT / "reports/logos_verse_4d_bridge_v2_overlay_v1_latest.jsonl"


def test_seed_neighbor_audit_smoke() -> None:
    if not OVERLAY.is_file():
        return
    out = ROOT / "reports/tmp_logos_seed_neighbor_smoke.json"
    cp = subprocess.run(
        [sys.executable, str(SCRIPT), "--out-json", str(out), "--top-k", "8"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    assert doc.get("schema") == "logos_4d_seed_neighbor_retrieval_v1"
    assert doc.get("research_only") is True
    assert len(doc.get("topics") or []) == 6
