"""Smoke: logos bible full coverage audit exits 0 and reports 31k denominator."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "docs/final/artifacts/logos_bible_full_coverage_audit_v1_latest.json"
SCRIPT = ROOT / "scripts/build_logos_bible_full_coverage_audit_v1.py"


def test_build_logos_bible_full_coverage_audit_v1_exit0():
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(AUDIT.read_text(encoding="utf-8-sig"))
    assert doc.get("schema") == "logos_bible_full_coverage_audit_v1"
    assert doc.get("canon", {}).get("denominator") == 31_102
    layers = {row["id"]: row for row in doc.get("layers") or []}
    assert "studio_citation_shard_krv" in layers
    pct = float(layers["studio_citation_shard_krv"]["canon_coverage_pct"])
    assert pct >= 99.0
    meaning_pct = float(layers["bible_meaning_graph_nodes"]["canon_coverage_pct"])
    assert meaning_pct >= 95.0
