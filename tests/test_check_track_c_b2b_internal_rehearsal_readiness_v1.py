# Keywords: track_c_b2b, internal_rehearsal

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_track_c_b2b_internal_rehearsal_readiness_v1.py"


def test_internal_rehearsal_readiness_gate_runs() -> None:
    out = ROOT / "reports/track_c_b2b_internal_rehearsal_readiness_v1_latest.json"
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--output-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "track_c_b2b_internal_rehearsal_readiness_v1"
    assert doc["ready_for_15min_rehearsal"] is True
    assert doc["ready_for_external_send"] is False


def test_counsel_export_manifest_includes_deck_screenshots() -> None:
    manifest = ROOT / "docs/final/artifacts/track_c_b2b_counsel_export_manifest_v1_latest.json"
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    paths = {row["path"] for row in doc.get("files") or [] if isinstance(row, dict)}
    assert "reports/track_c_showroom_deck_screenshots_v1/topology_radar_v1.png" in paths
    assert doc.get("file_count", 0) >= 19
