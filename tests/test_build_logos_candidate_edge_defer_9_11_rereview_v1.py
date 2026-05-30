"""Smoke: defer 9·11 Wave 3 re-review builder."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_logos_candidate_edge_defer_9_11_rereview_v1.py"
OUT_JSON = ROOT / "reports" / "logos_candidate_edge_defer_9_11_rereview_v1_latest.json"


def test_defer_rereview_wave3_smoke() -> None:
    proc = subprocess.run(
        [sys.executable, str(BUILDER), "--decision", "defer_maintained"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert OUT_JSON.is_file()
    doc = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_candidate_edge_defer_9_11_rereview_v1"
    assert doc["wave"] == 3
    assert doc["decision"] == "defer_maintained"
    ranks = {i["queue_rank"] for i in doc["items"]}
    assert ranks == {9, 11}
    for item in doc["items"]:
        assert item["recommendation"] == "defer"
