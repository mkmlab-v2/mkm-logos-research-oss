"""Smoke tests for logos external KG ingest manifest v1."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_logos_external_kg_ingest_manifest_v1.py"
OUT = ROOT / "docs/final/artifacts/logos_external_kg_ingest_manifest_v1_latest.json"


def test_build_manifest_exit_0():
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert OUT.is_file()


def test_manifest_schema_fields():
    proc = subprocess.run([sys.executable, str(SCRIPT)], cwd=str(ROOT), check=False)
    assert proc.returncode == 0
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_external_kg_ingest_manifest_v1"
    assert doc["research_only"] is True
    assert doc["send_gate"] == "HOLD"
    assert doc["operational_4d_ssot"] == "gematria_bridge_v1 S-L-K-M"
    sources = doc.get("external_sources") or []
    assert len(sources) >= 5
    ids = {s["source_id"] for s in sources}
    assert "gnosis_kg" in ids
    assert "scriptures_js_gematria" in ids
    assert "open_scripture_intelligence" in ids
    snap = doc.get("local_snapshot") or {}
    assert "lemma_hit_anchors" in snap
    assert "scriptures_js_gematria_lexicon_jsonl_lines" in snap
