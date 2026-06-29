# -*- coding: utf-8 -*-
"""Smoke: GraphRAG router seed retrieval audit."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_logos_topic_graphrag_seed_retrieval_v1.py"


def test_graphrag_seed_retrieval_smoke() -> None:
    out = ROOT / "reports/tmp_graphrag_seed_retrieval_smoke.json"
    cp = subprocess.run(
        [sys.executable, str(SCRIPT), "--out-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    assert doc.get("schema") == "logos_topic_graphrag_seed_retrieval_v1"
    assert doc.get("research_only") is True
    summary = doc.get("summary") or {}
    assert summary.get("topics") == 6
