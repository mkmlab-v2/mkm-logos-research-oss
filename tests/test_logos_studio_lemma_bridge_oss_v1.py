"""Logos Studio lemma neighbor bridge — OSS fixture-scale tests."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts/check_logos_studio_lemma_bridge_gate_v1.py"
SYNTH = ROOT / "scripts/synthesize_logos_studio_lemma_bridge_answer_v1.py"
BUILD_INDEX = ROOT / "scripts/build_logos_studio_lemma_neighbor_index_v1.py"


def test_build_lemma_neighbor_index_fixture_scale():
    proc = subprocess.run([sys.executable, str(BUILD_INDEX)], cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(proc.stdout)
    assert doc["ok"] is True
    assert doc["verse_count"] >= 5


def test_lemma_bridge_gate_exit0():
    proc = subprocess.run([sys.executable, str(GATE)], cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(proc.stdout)
    assert doc["ok"] is True


def test_lemma_bridge_psalm_fixture_chain():
    payload = {
        "query": "소망과 인내 시편",
        "path": {"verse_refs": ["Ps.23.1", "Ps.23.3", "Ps.23.4"]},
    }
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
    assert "[HYPO]" in doc["answer_ko"]
