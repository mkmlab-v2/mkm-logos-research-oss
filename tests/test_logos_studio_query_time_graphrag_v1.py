"""Logos Studio query-time GraphRAG bridge tests."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENCODE = ROOT / "scripts/encode_logos_studio_query_graphrag_v1.py"


def test_graphrag_encode_hope_query():
    proc = subprocess.run(
        [sys.executable, str(ENCODE), "--query", "소망과 인내 시편"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(proc.stdout)
    assert doc["ok"] is True
    assert doc["router_path_v1"]["verse_refs"]
    assert doc["highlight_node_ids"]


def test_graphrag_encode_semiconductor_query():
    proc = subprocess.run(
        [sys.executable, str(ENCODE), "--query", "반도체 유리 정제 은유 lemma 경로"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(proc.stdout)
    assert doc["ok"] is True
    refs = doc["router_path_v1"]["verse_refs"]
    assert any("Job" in r or "Zech" in r or "Dan" in r for r in refs)


def test_studio_page_no_homepage_preset_class():
    page = (ROOT / "projects/no1kmedi/src/app/logos-research/studio/page.tsx").read_text(
        encoding="utf-8"
    )
    assert "preset-stripe-linear" not in page
    assert "logos-research-studio-theme" in page
