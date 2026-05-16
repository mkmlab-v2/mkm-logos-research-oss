# Keywords: lg fallback two week pipeline

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_fallback_pipeline_json_and_checker() -> None:
    path = ROOT / "docs/final/artifacts/lg_hs_fallback_two_week_pipeline_v1.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc["schema"] == "lg_hs_fallback_two_week_pipeline_v1"
    assert len(doc["two_week_actions"]) >= 5
    assert len(doc["program_candidates"]) >= 3
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_lg_hs_fallback_two_week_pipeline_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
