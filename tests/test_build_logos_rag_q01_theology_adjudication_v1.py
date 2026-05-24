"""q01 theology adjudication report builder."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build_logos_rag_q01_theology_adjudication_v1.py"
GOLD = ROOT / "docs/final/artifacts/logos_semantic_query_gold_human_v1.json"


def test_q01_theology_report_builds() -> None:
    if not GOLD.is_file():
        return
    cp = subprocess.run(
        [sys.executable, str(BUILDER)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    out = ROOT / "docs/final/artifacts/logos_rag_q01_theology_adjudication_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_rag_q01_theology_adjudication_v1"
    assert doc["query_id"] == "q01"
