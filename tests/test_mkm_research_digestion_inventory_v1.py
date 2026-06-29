"""Smoke tests for research digestion inventory (B-track)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_mkm_research_digestion_inventory_v1.py"
OUT = ROOT / "reports/mkm_research_digestion_inventory_v1_latest.json"


def test_build_inventory_exit_zero():
    cp = subprocess.run(
        [sys.executable, str(SCRIPT), "--json"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(OUT.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "mkm_research_digestion_inventory_v1"
    assert doc["summary"]["lit_review_count"] >= 30
    assert "tier_counts" in doc["summary"]
    assert len(doc["priority_queue_top10"]) == 10


def test_compression_nextgen_merged_links_s3():
    doc = json.loads(OUT.read_text(encoding="utf-8-sig"))
    merged = next(
        e
        for e in doc["entries"]
        if e["id"] == "compression_nextgen_latent_indexer_external_dr"
    )
    assert merged["tier"] == "S3"
    assert merged["digested_facts_path"] is not None
