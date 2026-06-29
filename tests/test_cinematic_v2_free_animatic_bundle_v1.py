from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUNDLE_SCRIPT = ROOT / "scripts/cinematic/run_cinematic_v2_free_animatic_bundle_v1.py"
REPORT = ROOT / "docs/final/artifacts/cinematic_v2_free_animatic_bundle_v1_latest.json"
MASTER = ROOT / "docs/final/artifacts/cinematic_v2_workspace/deliverables/cinematic_v2_free_master_latest.mp4"
WORKSPACE = ROOT / "docs/final/artifacts/cinematic_v2_workspace"


def test_cinematic_v2_free_animatic_bundle_all_shots():
    proc = subprocess.run(
        [sys.executable, str(BUNDLE_SCRIPT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=600,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert REPORT.is_file()
    doc = json.loads(REPORT.read_text(encoding="utf-8"))
    assert doc["schema"] == "cinematic_v2_free_animatic_bundle_v1"
    assert doc["shot_count"] == 8
    assert doc["shots_ok"] == 8
    assert doc["veo_api_called"] is False
    assert MASTER.is_file() and MASTER.stat().st_size > 50_000
    for i in range(1, 9):
        clip = WORKSPACE / "shots" / f"shot_{i:02d}" / "clip.mp4"
        assert clip.is_file() and clip.stat().st_size > 10_000, clip
