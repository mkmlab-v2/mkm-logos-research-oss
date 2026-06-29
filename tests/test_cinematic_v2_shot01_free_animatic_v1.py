from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/cinematic/run_cinematic_v2_shot01_free_animatic_v1.py"
CLIP = ROOT / "docs/final/artifacts/cinematic_v2_workspace/shots/shot_01/clip.mp4"


def test_cinematic_v2_shot01_free_animatic_chain():
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert CLIP.is_file() and CLIP.stat().st_size > 10_000
    tail = proc.stdout.strip().splitlines()[-1]
    doc = json.loads(tail)
    assert doc.get("ok") is True
    assert doc.get("shots_ok") == 1
