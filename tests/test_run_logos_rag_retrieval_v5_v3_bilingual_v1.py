"""Smoke tests for R5 v3 bilingual retrieval eval."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_logos_rag_retrieval_v5_v3_bilingual_v1.py"
V3 = ROOT / "docs/final/artifacts/logos_semantic_query_set_v3.json"
V4 = ROOT / "docs/final/artifacts/logos_semantic_query_set_v4_ko_en_v1.json"
SQLITE = ROOT / "reports/constitution/btrack_pilot/logos_vector_index_ann_lite_st_u_v1.sqlite"


def test_v5_script_exists():
    assert SCRIPT.is_file()


def test_v5_ko_map_covers_v3():
    v3 = json.loads(V3.read_text(encoding="utf-8-sig"))
    v4 = json.loads(V4.read_text(encoding="utf-8-sig"))
    en_v3 = set(v3["queries"])
    en_v4 = {it["query_en"] for it in v4["items"]}
    assert en_v3 <= en_v4


def test_v5_runs_when_index_present(tmp_path: Path):
    if not V3.is_file() or not V4.is_file() or not SQLITE.is_file():
        return
    out = tmp_path / "v5.json"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--output-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert proc.returncode == 0, proc.stderr[-800:]
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "comp_logos_rag_retrieval_v5_v3_bilingual_v1"
    h = doc["headline"]
    assert isinstance(h["v3_en_improved_mean_top1_cosine"], (int, float))
    assert isinstance(h["v3_ko_gloss_improved_mean_top1_cosine"], (int, float))
    assert float(h["v3_ko_gloss_improved_mean_top1_cosine"]) > float(
        h["v3_en_improved_mean_top1_cosine"]
    )
