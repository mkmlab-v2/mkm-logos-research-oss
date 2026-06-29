# Keywords: deep_fetch, ltm_graph, handoff_envelope, route_bench

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RESOLVER = ROOT / "scripts/resolve_deep_fetch_from_handoff_v1.py"
BENCH = ROOT / "scripts/bench_mkm_ltm_route_accuracy_v1.py"
ENVELOPE = ROOT / "docs/final/artifacts/mkm_cursor_deep_handoff_envelope_v1_latest.json"


def test_resolve_deep_fetch_exit0():
    proc = subprocess.run(
        [sys.executable, str(RESOLVER), "--lane", "infra"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    out = ROOT / "reports/mkm_deep_fetch_resolve_smoke_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "mkm_deep_fetch_resolve_v1"
    assert doc["graph_axis"] == "A_ltm"
    assert 1 <= len(doc["paths"]) <= 3


def test_resolve_denies_phi_by_default():
    from scripts.resolve_deep_fetch_from_handoff_v1 import resolve_deep_fetch

    graph = {
        "concepts": {
            "ltm_graph_self_meta": {
                "primary_coordinate": {"file_path": "scripts/build_mkm_long_term_memory_graph_v1.py"}
            }
        }
    }
    envelope = {
        "graph_axis": "A_ltm",
        "lane": "infra",
        "ltm_concept_ids": [],
        "deep_fetch_next": [
            "reports/lee_bomi_clinic_kakao_postpartum_care_v1.md",
            "reports/mkm_meta_cognition_shallow_deep_roadmap_v1_latest.json",
        ],
    }
    doc = resolve_deep_fetch(envelope, graph, max_paths=3)
    paths = doc["paths"]
    assert "lee_bomi" not in " ".join(paths)
    assert any("mkm_meta_cognition_shallow_deep_roadmap" in p for p in paths)


def test_route_bench_lane_hit_gate():
    proc = subprocess.run(
        [sys.executable, str(BENCH)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    bench = json.loads(
        (ROOT / "reports/mkm_ltm_route_accuracy_bench_v1_latest.json").read_text(encoding="utf-8")
    )
    lane_rate = bench["aggregate"]["lane_hit_rate"]
    assert lane_rate is not None and lane_rate >= 0.85


def test_resolve_lane_top1_hint_cases():
    from mkm_long_term_memory_graph_lib_v1 import load_graph, resolve_lane_from_graph

    graph = load_graph(ROOT / "storage/meta/mkm_long_term_memory_graph_v1.json")
    assert resolve_lane_from_graph(graph, "12ai router librarian sentinel parallel cap") == "infra"
    assert resolve_lane_from_graph(graph, "web_ops nebius regime gate no_gpu_spinup") == "web_ops"
