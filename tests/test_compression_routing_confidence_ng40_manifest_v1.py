"""Smoke for compression-is-routing ng40 manifest."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
OUT = ROOT / "reports/_test_compression_routing_confidence_ng40_manifest_v1.json"


def test_routing_confidence_manifest_exit_0() -> None:
    if not ACTIVE.is_file():
        return
    proc = subprocess.run(
        [
            PY,
            "scripts/build_compression_routing_confidence_ng40_manifest_v1.py",
            "--output",
            str(OUT.relative_to(ROOT)).replace("\\", "/"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "compression_routing_confidence_ng40_manifest_v1"
    assert doc["annotation_only"] is True
    assert len(doc["per_case"]) == 40
    assert "zone_b_timing" in doc["per_shard"] or len(doc["per_shard"]) >= 1
