"""Smoke: en_tech semantic GPU PoC script imports and dry path."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_run_en_tech_semantic_gpu_poc_v1_max1() -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_en_tech_semantic_gpu_poc_v1.py"),
            "--max-cases",
            "1",
            "--skip-gpu-semantic",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert r.returncode == 0, r.stderr[-2000:]
    out = ROOT / "reports/constitution/btrack_pilot/comp_en_tech_semantic_gpu_poc_local_v1_latest.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    assert doc.get("schema") == "comp_en_tech_semantic_gpu_poc_local_v1"
    assert doc.get("research_only") is True
    assert doc.get("track_a_active_written") is False
    assert len(doc.get("per_case") or []) == 1
