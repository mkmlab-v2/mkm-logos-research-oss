"""Offline gate: embed allowlist presets merge into router sidecar."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MERGE = ROOT / "scripts" / "merge_logos_studio_embed_router_sidecar_v1.py"
SIDECAR = ROOT / "docs/final/artifacts/showroom_meaning_topology_qa_router_sidecar_v1_latest.json"
PRESETS = ROOT / "docs/final/artifacts/showroom_meaning_topology_qa_presets_v1_latest.json"

ALLOWLIST = (
    "job_job_suffering_reason",
    "isaiah_youtube_spine_v1",
    "bigset_topic_nephilim",
    "topic_ezra_1_anchor",
)


def test_merge_embed_router_sidecar_allowlist_present() -> None:
    proc = subprocess.run([sys.executable, str(MERGE)], cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr or proc.stdout
    sidecar = json.loads(SIDECAR.read_text(encoding="utf-8-sig"))
    presets_doc = json.loads(PRESETS.read_text(encoding="utf-8-sig"))
    preset_ids = {str(p.get("id")) for p in presets_doc.get("presets") or []}
    for pid in ALLOWLIST:
        assert pid in preset_ids, f"missing preset {pid}"
        block = (sidecar.get("presets") or {}).get(pid)
        assert block, f"missing sidecar {pid}"
        rp = block.get("router_path_v1") or {}
        assert rp.get("verse_refs") or rp.get("node_ids"), f"empty router path {pid}"
