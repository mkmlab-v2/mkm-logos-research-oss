"""zone_h_en_business template catalog coverage eval."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data/compression/fixtures/zone_h_en_business_corpus_extract_fixture_v1.jsonl"
EXPAND = ROOT / "data/compression/fixtures/zone_h_en_business_corpus_expand_v1.jsonl"
CATALOG = ROOT / "codebook/templates/zone_h_en_business_templates_v1.jsonl"
COVERAGE_RUNNER = ROOT / "scripts/run_zone_h_en_business_template_catalog_coverage_v1.py"
PIPELINE = ROOT / "scripts/run_zone_h_en_business_template_catalog_pipeline_v1.py"


def test_coverage_fixture_full_match() -> None:
    from scripts.zone_h_en_business_template_catalog_coverage_v1_lib import evaluate_corpus_snippet_coverage

    shard = __import__(
        "scripts.extract_zone_h_en_business_template_seeds_v1_lib",
        fromlist=["load_shard"],
    ).load_shard(ROOT / "codebook/shards/zone_h_en_business_v1.json")
    from scripts.compression_en_business_deep_pack_v1_lib import load_template_catalog

    rows = load_template_catalog(CATALOG)
    row = evaluate_corpus_snippet_coverage(
        FIXTURE,
        shard=shard,
        catalog_rows=rows,
    )
    assert row["snippet_candidates_total"] == 4
    assert row["wire_match_count"] == 4
    assert row["wire_match_rate"] == 1.0


def test_coverage_expand_full_match() -> None:
    from scripts.zone_h_en_business_template_catalog_coverage_v1_lib import evaluate_corpus_snippet_coverage

    shard = __import__(
        "scripts.extract_zone_h_en_business_template_seeds_v1_lib",
        fromlist=["load_shard"],
    ).load_shard(ROOT / "codebook/shards/zone_h_en_business_v1.json")
    from scripts.compression_en_business_deep_pack_v1_lib import load_template_catalog

    rows = load_template_catalog(CATALOG)
    row = evaluate_corpus_snippet_coverage(
        EXPAND,
        shard=shard,
        catalog_rows=rows,
    )
    assert row["snippet_candidates_total"] == 5
    assert row["wire_match_rate"] == 1.0


def test_coverage_runner_smoke() -> None:
    proc = subprocess.run(
        [sys.executable, str(COVERAGE_RUNNER)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(
        (ROOT / "docs/final/artifacts/zone_h_en_business_template_catalog_coverage_v1_latest.json").read_text(
            encoding="utf-8"
        )
    )
    assert doc["schema"] == "zone_h_en_business_template_catalog_coverage_v1"
    assert doc["aggregate"]["full_wire_match"] is True


def test_pipeline_dry_run_smoke() -> None:
    proc = subprocess.run(
        [sys.executable, str(PIPELINE)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
