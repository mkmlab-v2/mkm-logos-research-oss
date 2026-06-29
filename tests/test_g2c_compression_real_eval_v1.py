"""Smoke test for G2-c compression real-eval (v2 roundtrip)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/g2c_compression_real_eval_v1_latest.json"
SPEC = ROOT / "docs/final/artifacts/g2c_compression_real_eval_spec_v1_latest.json"


def test_g2c_compression_real_eval_spec_exists() -> None:
    assert SPEC.is_file()
    doc = json.loads(SPEC.read_text(encoding="utf-8"))
    assert doc["schema"] == "g2c_compression_real_eval_spec_v1"
    assert doc["eval_mode"] == "v2_compress_expand_roundtrip"
    assert "closed_dictionary_mesh_restore_proxy" in doc.get("forbidden_methods", [])


def test_g2c_compression_real_eval_runs() -> None:
    corpus = ROOT / "data/logos/verse_4pipeline_full_31102.json"
    jsonl = ROOT / "docs/final/artifacts/sasang_routing_sidecar_corpus_31k_v1.jsonl"
    if not corpus.is_file() or not jsonl.is_file():
        return
    cp = subprocess.run(
        [sys.executable, "scripts/run_g2c_compression_real_eval_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "g2c_compression_real_eval_v1"
    assert doc["send_gate"] == "HOLD"
    assert doc["track_a_blocked"] is True
    assert doc["sample_count"] >= 1
    assert doc["arms"]["baseline"]["roundtrip_jaccard_mean"] is not None
