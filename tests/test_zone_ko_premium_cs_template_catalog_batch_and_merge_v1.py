"""Batch extract and gated merge for zone_ko_premium_cs template catalogs."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data/compression/fixtures/zone_ko_premium_cs_corpus_extract_fixture_v1.jsonl"
BATCH_RUNNER = ROOT / "scripts/run_zone_ko_premium_cs_template_catalog_batch_extract_v1.py"
MERGE_SCRIPT = ROOT / "scripts/merge_zone_ko_premium_cs_template_prospect_to_catalog_v1.py"
PROSPECT = ROOT / "codebook/templates/zone_ko_premium_cs_templates_prospect_v1.jsonl"


def test_merge_plan_skips_missing_mask_token() -> None:
    from scripts.merge_zone_ko_premium_cs_template_prospect_v1_lib import plan_prospect_merge

    production = [{"template_id": "kcs_t001", "snippet": "주문 ███ 환불", "must_keep_terms": ["███"]}]
    prospect = [
        {"template_id": "kcs_p001", "snippet": "주문 ███ 환불", "must_keep_terms": ["███"]},
        {"template_id": "kcs_p002", "snippet": "마스크 없는 문장입니다.", "must_keep_terms": []},
    ]
    plan = plan_prospect_merge(production_rows=production, prospect_rows=prospect)
    assert plan["merge_count"] == 0
    assert plan["skipped_count"] == 2


def test_merge_requires_reviewer_when_approved(tmp_path: Path) -> None:
    prod = tmp_path / "prod.jsonl"
    prospect = tmp_path / "prospect.jsonl"
    prospect.write_text(
        '{"template_id":"kcs_p001","shard_id":"zone_ko_premium_cs_v1","language":"ko",'
        '"snippet":"신규 ███ 환불 문의입니다.","must_keep_terms":["███"]}\n',
        encoding="utf-8",
    )
    prod.write_text(
        '{"template_id":"kcs_t001","shard_id":"zone_ko_premium_cs_v1","language":"ko",'
        '"snippet":"기존 ███","must_keep_terms":["███"]}\n',
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


def test_merge_apply_on_tmp_catalog(tmp_path: Path) -> None:
    prod = tmp_path / "prod.jsonl"
    prospect = tmp_path / "prospect.jsonl"
    prod.write_text(
        '{"template_id":"kcs_t001","shard_id":"zone_ko_premium_cs_v1","language":"ko",'
        '"snippet":"기존 ███","must_keep_terms":["███"]}\n',
        encoding="utf-8",
    )
    prospect.write_text(
        '{"template_id":"kcs_p001","shard_id":"zone_ko_premium_cs_v1","language":"ko",'
        '"snippet":"신규 ███ 환불 문의입니다.","must_keep_terms":["환불","███"]}\n',
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
            "--reviewer",
            "commander_test",
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
    assert proc.returncode == 0, proc.stderr or proc.stdout
    after = sum(1 for line in prod.read_text(encoding="utf-8").splitlines() if line.strip())
    assert after == 2
    doc = json.loads((tmp_path / "merge.json").read_text(encoding="utf-8"))
    assert doc["applied"] is True
    assert doc["new_template_ids"] == ["kcs_t002"]


def test_batch_extract_fixture_manifest_smoke(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"input_jsonl": ["data/compression/fixtures/zone_ko_premium_cs_corpus_extract_fixture_v1.jsonl"]}),
        encoding="utf-8",
    )
    report = tmp_path / "batch_report.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(BATCH_RUNNER),
            "--manifest",
            str(manifest),
            "--catalog",
            str(tmp_path / "empty_catalog.jsonl"),
            "--report-out",
            str(report),
            "--artifact-out",
            str(tmp_path / "artifact.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(report.read_text(encoding="utf-8"))
    assert doc["schema"] == "zone_ko_premium_cs_template_catalog_batch_extract_v1"
    assert doc["aggregate_stats"]["prospect_count"] == 5
