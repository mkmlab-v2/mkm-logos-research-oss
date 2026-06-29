"""B2B off-the-shelf SKU spec + PoC --sku wiring (research_only)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/final/artifacts/compression_b2b_off_the_shelf_shard_sku_v1.json"


def test_sku_spec_lists_four_skus_with_b2b_paths() -> None:
    doc = json.loads(SPEC.read_text(encoding="utf-8"))
    skus = doc["skus"]
    assert len(skus) == 4
    for row in skus:
        assert row.get("b2b_shard_path")
        p = ROOT / row["b2b_shard_path"]
        assert p.is_file(), row["external_sku"]
        shard = json.loads(p.read_text(encoding="utf-8"))
        assert shard.get("research_only") is True
        assert shard.get("hypothesis_tier") == "B"


def test_resolve_external_sku_med() -> None:
    from scripts.compression_b2b_off_the_shelf_shard_sku_v1_lib import (
        build_sku_context,
        resolve_external_sku,
        load_sku_spec,
    )

    spec = load_sku_spec(SPEC)
    row = resolve_external_sku(spec, "MKM-MED-G1")
    assert row["legacy_shard_path"] == "codebook/shards/zone_g_health.json"
    assert row["b2b_shard_path"] == "codebook/shards/b2b/zone_g_health_b2b_v1.json"

    ctx = build_sku_context(
        workspace_root=ROOT,
        spec_path=SPEC,
        external_sku="MKM-MED-G1",
        shard_json_override=None,
    )
    assert ctx["external_sku"] == "MKM-MED-G1"
    assert ctx["b2b_shard_id"] == "zone_g_health_b2b_v1"
    assert ctx["routing_wiring"] == "metadata_only_v1"


def test_poc_unknown_sku_exit_2() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_customer_compression_stateless_poc_v1.py"),
            "--input-jsonl",
            str(ROOT / "data/compression/stateless_poc_golden40_public_safe_v1.jsonl"),
            "--sku",
            "MKM-NOPE-XX",
            "--max-cases",
            "1",
            "--out-json",
            str(ROOT / "reports/tmp_customer_poc_unknown_sku_v1.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2


@pytest.mark.parametrize("external_sku", ["MKM-SCM-A1", "MKM-CHAT-D1", "MKM-FIN-E1", "MKM-MED-G1"])
def test_poc_sku_metadata_smoke(external_sku: str, tmp_path: Path) -> None:
    out = tmp_path / f"poc_{external_sku}.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_customer_compression_stateless_poc_v1.py"),
            "--input-jsonl",
            str(ROOT / "data/compression/stateless_poc_golden40_public_safe_v1.jsonl"),
            "--sku",
            external_sku,
            "--max-cases",
            "2",
            "--relax-pass-gate",
            "--out-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["sku_context"]["external_sku"] == external_sku
    assert doc["sku_context"]["routing_wiring"] == "forced_shard_id_v1"
    assert doc["case_count"] >= 1
    first = doc["cases"][0]
    assert first.get("router_shard_id") == doc["sku_context"]["b2b_shard_id"]
