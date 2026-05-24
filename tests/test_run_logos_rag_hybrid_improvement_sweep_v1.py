"""Smoke tests for hybrid improvement sweep script."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_logos_rag_hybrid_improvement_sweep_v1.py"
GOLD = ROOT / "docs/final/artifacts/logos_semantic_query_gold_human_v1.json"
SQLITE = ROOT / "reports/constitution/btrack_pilot/logos_vector_index_ann_lite_st_u_v1.sqlite"


def test_hybrid_sweep_script_exists():
    assert SCRIPT.is_file()


def test_hybrid_sweep_runs_when_index_present(tmp_path: Path):
    if not GOLD.is_file() or not SQLITE.is_file():
        return
    out = tmp_path / "hybrid_sweep.json"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--output-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert proc.returncode == 0, proc.stderr[-800:]
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "comp_logos_rag_hybrid_improvement_sweep_v1"
    assert doc["winner"]["variant"]
    assert len(doc["variants"]) >= 5
