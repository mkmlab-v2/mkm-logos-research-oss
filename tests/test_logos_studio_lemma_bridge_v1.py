"""Logos Studio lemma neighbor bridge v1 tests."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts/check_logos_studio_lemma_bridge_gate_v1.py"
SYNTH = ROOT / "scripts/synthesize_logos_studio_lemma_bridge_answer_v1.py"
BUILD_INDEX = ROOT / "scripts/build_logos_studio_lemma_neighbor_index_v1.py"
GRAPHRAG = ROOT / "scripts/encode_logos_studio_query_graphrag_v1.py"


def test_build_lemma_neighbor_index_exit0():
    proc = subprocess.run([sys.executable, str(BUILD_INDEX)], cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(proc.stdout)
    assert doc["ok"] is True
    assert doc["verse_count"] > 1000


def test_lemma_bridge_gate_exit0():
    proc = subprocess.run([sys.executable, str(GATE)], cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(proc.stdout)
    assert doc["ok"] is True


def test_lemma_bridge_graphrag_chain_psalm():
    gproc = subprocess.run(
        [sys.executable, str(GRAPHRAG), "--query", "소망과 인내 시편"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert gproc.returncode == 0, gproc.stdout + gproc.stderr
    graphrag = json.loads(gproc.stdout)
    assert graphrag["ok"] is True
    refs = graphrag.get("router_path_v1", {}).get("verse_refs") or []
    assert len(refs) >= 1
    payload = {"query": "소망과 인내 시편", "path": {"verse_refs": refs}}
    proc = subprocess.run(
        [sys.executable, str(SYNTH), "--stdin-json"],
        cwd=ROOT,
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(proc.stdout)
    assert doc["ok"] is True
    assert doc["neighbor_count"] >= 1
    assert "Lemma 연결" in doc["answer_ko"] or "lemma" in doc["answer_ko"].lower()
