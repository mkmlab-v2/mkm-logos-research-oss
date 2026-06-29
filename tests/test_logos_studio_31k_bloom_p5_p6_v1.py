"""P5/P6 Logos Studio 31k bloom + dynamic subgraph router smoke."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD_BLOOM = ROOT / "scripts/build_logos_studio_31k_bloom_secondary_fetch_v1.py"
BUILD_DYNAMIC = ROOT / "scripts/build_logos_studio_dynamic_subgraph_router_sidecar_v1.py"
ENCODE = ROOT / "scripts/encode_logos_studio_query_graphrag_v1.py"
BLOOM_ART = ROOT / "docs/final/artifacts/logos_studio_31k_bloom_secondary_fetch_v1_latest.json"
DYNAMIC_ART = ROOT / "docs/final/artifacts/logos_studio_dynamic_subgraph_router_v1_latest.json"


def test_build_31k_bloom_secondary_fetch():
    proc = subprocess.run([sys.executable, str(BUILD_BLOOM)], cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(BLOOM_ART.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "logos_studio_31k_bloom_secondary_fetch_v1"
    assert doc["canon_verse_count"] == 31102
    assert doc["chapter_shard_count"] >= 1000


def test_build_dynamic_subgraph_router_sidecar():
    proc = subprocess.run(
        [sys.executable, str(BUILD_DYNAMIC), "--max-presets", "12"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(DYNAMIC_ART.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "logos_studio_dynamic_subgraph_router_v1"
    assert doc["route_count"] >= 10
    assert doc["bloom_index_present"] is True


def test_bloom_chapter_stub_merge_script_smoke():
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/merge_logos_studio_bloom_chapter_stubs_into_graph_slice_v1.py"),
            "--target-canon-pct",
            "35",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = ROOT / "reports/logos_bloom_chapter_stub_merge_v1_latest.json"
    assert report.is_file()
    doc = json.loads(report.read_text(encoding="utf-8-sig"))
    assert doc.get("ok") is True


def test_w2_corpus_batch_expand_smoke():
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/expand_logos_bible_full_corpus_batch_v1.py"),
            "--target-canon-pct",
            "35",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_graphrag_encode_uses_bloom_when_sparse():
    proc = subprocess.run(
        [sys.executable, str(ENCODE), "--query", "욥기 1장 고난"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(proc.stdout)
    assert doc["ok"] is True
    refs = doc["router_path_v1"]["verse_refs"]
    assert refs
