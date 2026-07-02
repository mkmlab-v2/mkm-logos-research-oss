"""Long-tail GraphRAG Hit@k eval smoke."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_logos_ask_longtail_graphrag_eval_v1.py"
OUT = ROOT / "reports/logos_ask_longtail_graphrag_eval_v1_latest.json"


def test_longtail_graphrag_eval_runs():
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(OUT.read_text(encoding="utf-8-sig"))
    assert doc.get("schema") == "logos_ask_longtail_graphrag_eval_v1"
    assert doc.get("research_only") is True
    assert len(doc.get("rows") or []) >= 4
    agg = doc.get("aggregate") or {}
    assert "mean_hit_at_3" in agg
    assert "graphrag" in agg["mean_hit_at_3"]
