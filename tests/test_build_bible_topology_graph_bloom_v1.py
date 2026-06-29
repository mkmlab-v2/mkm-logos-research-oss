"""Phase 0: bible_topology_shard_v1 → magic_orb_graph_bloom_v1."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build_bible_topology_graph_bloom_v1.py"
SHARD = ROOT / "tests/fixtures/bible_topology/sample/sample_topology_synoptic_passion_v1.json"
ARTIFACT = ROOT / "docs/final/artifacts/magic_orb_graph_bloom_bible_topology_passion_v1_latest.json"
MKMLIFE_POC = ROOT / "projects/mkm/mkm-life/public/data/magic_orb_graph_bloom_poc_v1.json"


def _load_builder():
    spec = importlib.util.spec_from_file_location("build_bible_topology_graph_bloom_v1", BUILDER)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_shard_fixture_exists():
    assert SHARD.is_file()


def test_build_bloom_from_shard_caps_and_schema():
    mod = _load_builder()
    shard = json.loads(SHARD.read_text(encoding="utf-8-sig"))
    doc = mod.build_bloom_from_shard(shard)
    assert doc["schema"] == "magic_orb_graph_bloom_v1"
    assert doc["research_only"] is True
    assert doc["non_gating"] is True
    assert doc["source"]["kind"] == "bible_topology_shard_v1"
    assert doc["source"]["slice_id"] == "SYNOPTIC_PASSION_WEEK_v1"
    assert doc["stats"]["node_count"] <= 64
    assert doc["stats"]["edge_count"] <= 72
    assert doc["stats"]["node_count"] >= 20
    assert doc["stats"]["edge_count"] >= 20
    ids = {n["id"] for n in doc["nodes"]}
    assert "query::center" in ids
    for n in doc["nodes"]:
        assert n["kind"] in ("query", "verse")
    for e in doc["edges"]:
        assert e["src"] in ids and e["dst"] in ids
        assert e.get("edge_type") == "parallel"


def test_builder_cli_writes_artifact():
    out = ROOT / "reports/test_bible_topology_graph_bloom_v1_out.json"
    if out.is_file():
        out.unlink()
    proc = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--out-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "magic_orb_graph_bloom_v1"
    out.unlink(missing_ok=True)


def test_chain_promotes_mkmlife_poc_when_run():
    if not ARTIFACT.is_file():
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts/run_bible_topology_graph_bloom_chain_v1.py")],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr + proc.stdout
    assert ARTIFACT.is_file()
    assert MKMLIFE_POC.is_file()
    passion = json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))
    poc = json.loads(MKMLIFE_POC.read_text(encoding="utf-8-sig"))
    assert passion["source"]["slice_id"] == "SYNOPTIC_PASSION_WEEK_v1"
    assert poc["stats"]["edge_count"] == passion["stats"]["edge_count"]
