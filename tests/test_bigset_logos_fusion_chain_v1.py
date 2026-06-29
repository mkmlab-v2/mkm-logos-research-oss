"""BigSet + Logos Studio fusion chain — tier_0 HD delegation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FUSION = ROOT / "scripts/run_bigset_logos_fusion_chain_v1.py"
SIDECAR_ART = ROOT / "docs/final/artifacts/bigset_studio_conflict_sidecar_v1_latest.json"
STUDIO_MIRROR = ROOT / "projects/no1kmedi/public/data/logos_studio/bigset_conflict_sidecar_v1.json"


def test_bigset_logos_fusion_chain_exit_zero():
    proc = subprocess.run([sys.executable, str(FUSION)], cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_studio_conflict_sidecar_artifact_and_mirror():
    assert SIDECAR_ART.is_file()
    doc = json.loads(SIDECAR_ART.read_text(encoding="utf-8"))
    assert doc.get("schema") == "bigset_studio_conflict_sidecar_v1"
    assert doc.get("non_gating") is True
    assert doc.get("group_count", 0) >= 1
    assert STUDIO_MIRROR.is_file()
    mirror = json.loads(STUDIO_MIRROR.read_text(encoding="utf-8"))
    assert mirror.get("group_count") == doc.get("group_count")
