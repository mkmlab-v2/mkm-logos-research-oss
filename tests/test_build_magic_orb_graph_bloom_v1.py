"""Smoke: build_magic_orb_graph_bloom_v1 from router sidecar."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "reports/question_logos_subgraph_router_sidecar_v1_latest.json"
BUILDER = ROOT / "scripts/build_magic_orb_graph_bloom_v1.py"


def _load_builder():
    spec = importlib.util.spec_from_file_location("build_magic_orb_graph_bloom_v1", BUILDER)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_bloom_from_router_has_query_center():
    if not ROUTER.is_file():
        return
    mod = _load_builder()
    router = json.loads(ROUTER.read_text(encoding="utf-8"))
    doc = mod.build_bloom(query=router.get("query", "test"), router=router)
    assert doc["schema"] == "magic_orb_graph_bloom_v1"
    assert doc["nodes"]
    ids = {n["id"] for n in doc["nodes"]}
    assert "query::center" in ids
    assert doc["stats"]["node_count"] == len(doc["nodes"])
    assert doc["stats"]["edge_count"] == len(doc["edges"])
    assert doc["stats"]["node_count"] <= 48


def test_bloom_builder_cli_help():
    import subprocess
    import sys

    r = subprocess.run(
        [sys.executable, str(BUILDER), "--help"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0
    assert "magic_orb_graph_bloom" in r.stdout
