"""Smoke: hybrid B2B commercialization pipeline SSOT builder."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build_hybrid_b2b_commercialization_pipeline_v1.py"
OUT_JSON = ROOT / "docs/final/artifacts/hybrid_b2b_commercialization_pipeline_v1_latest.json"
OUT_MD = ROOT / "docs/final/artifacts/hybrid_b2b_commercialization_pipeline_v1_latest.md"


def test_build_hybrid_b2b_pipeline_exit0_and_lane_split() -> None:
    proc = subprocess.run(
        [sys.executable, str(BUILDER)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert OUT_JSON.is_file()
    assert OUT_MD.is_file()

    doc = json.loads(OUT_JSON.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "hybrid_b2b_commercialization_pipeline_v1"
    lanes = doc["lanes"]
    assert "compression_api" in lanes
    assert "edge_sku_coord" in lanes

    comp_stages = {s.get("stage") for s in lanes["compression_api"]["stages"]}
    edge_stages = {s.get("stage") for s in lanes["edge_sku_coord"]["stages"]}
    assert "3A" in comp_stages
    assert "3B" in edge_stages
    assert "3A" not in edge_stages

    free = doc["github_funnel"]["free_tier_viral"]
    assert free["status"] == "HYPO"

    raw_saving = (
        lanes["compression_api"]["stages"][1].get("customer_measured_raw_saving") or ""
    )
    assert "20." in raw_saving or raw_saving == "—", raw_saving

    proto = doc["unlock_protocol"]
    assert proto["name"] == "infra_smoke_open_bench_binding_check"
    assert "paid_revenue" in proto["not_this"]

    md = OUT_MD.read_text(encoding="utf-8")
    assert "[HYPO]" in md
    assert "3A" in md and "3B" in md
    assert "FAIL-COMP-004" in md
