# -*- coding: utf-8 -*-
"""Smoke: logos 4D dedupe audit (B-track)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_audit_logos_verse_4d_dedupe_smoke() -> None:
    script = ROOT / "scripts" / "audit_logos_verse_4d_dedupe_v1.py"
    out = ROOT / "reports" / "tmp_logos_verse_4d_dedupe_audit_smoke.json"
    cp = subprocess.run(
        [sys.executable, str(script), "--out-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    assert doc.get("schema") == "logos_verse_4d_dedupe_audit_v1"
    assert doc.get("research_only") is True
    t = doc["totals"]
    assert t["verse_rows"] >= 30000
    assert t["duplicate_verse_fraction"] > 0.5
    assert len(doc.get("graphrag_seed_audit") or []) >= 10
