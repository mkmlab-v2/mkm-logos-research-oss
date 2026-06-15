"""zone_ko_premium_cs template seed extraction from JSONL corpora."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data/compression/fixtures/zone_ko_premium_cs_corpus_extract_fixture_v1.jsonl"
SHARD = ROOT / "codebook/shards/zone_ko_premium_cs_v1.json"
BUILDER = ROOT / "scripts/build_zone_ko_premium_cs_template_catalog_from_corpus_v1.py"
PRODUCTION = ROOT / "codebook/templates/zone_ko_premium_cs_templates_v1.jsonl"


def test_extract_ko_premium_cs_masked_only() -> None:
    from scripts.extract_zone_ko_premium_cs_template_seeds_v1_lib import extract_from_jsonl, load_shard

    shard = load_shard(SHARD)
    result = extract_from_jsonl(FIXTURE, shard=shard, existing_snippets=set(), min_score=1)
    assert result["rows_scanned"] == 5
    assert result["candidates_novel"] == 5
    assert len(result["prospect_rows"]) == 5
    for row in result["prospect_rows"]:
        assert row["shard_id"] == "zone_ko_premium_cs_v1"
        assert "███" in row["snippet"]


def test_extract_skips_production_catalog_snippets() -> None:
    from scripts.compression_ko_premium_cs_deep_pack_v1_lib import load_template_catalog
    from scripts.extract_zone_ko_premium_cs_template_seeds_v1_lib import extract_from_jsonl, load_shard

    existing = {str(r["snippet"]) for r in load_template_catalog(PRODUCTION)}
    shard = load_shard(SHARD)
    result = extract_from_jsonl(FIXTURE, shard=shard, existing_snippets=existing, min_score=1)
    assert result["candidates_skipped_existing"] == 5
    assert result["candidates_novel"] == 0


def test_build_ko_cs_catalog_from_fixture_exit_zero() -> None:
    import tempfile

    prospect_out = Path(tempfile.mkdtemp()) / "prospect.jsonl"
    proc = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--input-jsonl",
            str(FIXTURE),
            "--prospect-out",
            str(prospect_out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(
        (ROOT / "docs/final/artifacts/zone_ko_premium_cs_template_catalog_extract_v1_latest.json").read_text(
            encoding="utf-8"
        )
    )
    assert doc["schema"] == "zone_ko_premium_cs_template_catalog_extract_v1"
    assert doc["wire_family"] == "CS_MASK"
    assert doc["twin_preview"]["exact_restore_pass_count"] == doc["extract_stats"]["candidates_novel"]
