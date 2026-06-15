"""Batch extract and gated merge for zone_h_en_business template catalogs."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPAND = ROOT / "data/compression/fixtures/zone_h_en_business_corpus_expand_v1.jsonl"
BATCH_RUNNER = ROOT / "scripts/run_zone_h_en_business_template_catalog_batch_extract_v1.py"
MERGE_SCRIPT = ROOT / "scripts/merge_zone_h_en_business_template_prospect_to_catalog_v1.py"


def test_merge_plan_skips_duplicate_snippet() -> None:
    from scripts.merge_zone_h_en_business_template_prospect_v1_lib import plan_prospect_merge

    snippet = "Dear Team, invoice payment contract compliance attached."
    production = [{"template_id": "eb_t001", "snippet": snippet, "must_keep_terms": ["invoice"]}]
    prospect = [
        {"template_id": "eb_p001", "snippet": snippet, "must_keep_terms": ["invoice"]},
        {"template_id": "eb_p002", "snippet": "Unique notice: delivery schedule proposal compliance.", "must_keep_terms": ["compliance"]},
    ]
    plan = plan_prospect_merge(production_rows=production, prospect_rows=prospect)
    assert plan["merge_count"] == 1
    assert plan["skipped_count"] == 1
    assert plan["to_merge"][0]["new_template_id"] == "eb_t002"


def test_merge_requires_reviewer_when_approved(tmp_path: Path) -> None:
    prod = tmp_path / "prod.jsonl"
    prospect = tmp_path / "prospect.jsonl"
    prospect.write_text(
        '{"template_id":"eb_p001","shard_id":"zone_h_en_business_v1","language":"en",'
        '"snippet":"NOTICE: new purchase order payment authorization required.","must_keep_terms":["payment"]}\n',
        encoding="utf-8",
    )
    prod.write_text(
        '{"template_id":"eb_t001","shard_id":"zone_h_en_business_v1","language":"en",'
        '"snippet":"Existing contract compliance invoice.","must_keep_terms":["invoice"]}\n',
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(MERGE_SCRIPT),
            "--catalog",
            str(prod),
            "--prospect",
            str(prospect),
            "--human-approve-merge",
            "--report-out",
            str(tmp_path / "merge.json"),
            "--artifact-out",
            str(tmp_path / "merge_art.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 2


def test_expand_fixture_has_novel_candidates() -> None:
    from scripts.extract_zone_h_en_business_template_seeds_v1_lib import extract_from_jsonl, load_shard

    shard = ROOT / "codebook/shards/zone_h_en_business_v1.json"
    result = extract_from_jsonl(EXPAND, shard=load_shard(shard), existing_snippets=set(), min_score=2)
    assert result["candidates_novel"] >= 4
