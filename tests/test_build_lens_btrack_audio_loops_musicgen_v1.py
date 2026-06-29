"""build_lens_btrack_audio_loops_musicgen_v1.py dry-run contract."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_lens_btrack_audio_loops_musicgen_v1.py"


def test_musicgen_bake_dry_run_twelve_clips() -> None:
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--dry-run", "--max-pairs", "12"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    report = ROOT / "reports/track_c_audio_hook_samples_v1/lens_btrack_audio_musicgen_bake_report_v1_latest.json"
    assert report.is_file()
    doc = json.loads(report.read_text(encoding="utf-8"))
    assert doc["schema"] == "lens_btrack_audio_musicgen_bake_report_v1"
    assert len(doc["clips"]) == 12
