"""Batch extract and gated merge for zone_f_code template catalogs."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data/compression/fixtures/zone_f_code_corpus_extract_fixture_v1.jsonl"
BATCH_RUNNER = ROOT / "scripts/run_zone_f_code_template_catalog_batch_extract_v1.py"
MERGE_SCRIPT = ROOT / "scripts/merge_zone_f_code_template_prospect_to_catalog_v1.py"
MERGE_LIB = ROOT / "scripts/merge_zone_f_code_template_prospect_v1_lib.py"


def test_batch_extract_fixture_manifest_smoke(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"input_jsonl": ["data/compression/fixtures/zone_f_code_corpus_extract_fixture_v1.jsonl"]}),
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
    assert doc["schema"] == "zone_f_code_template_catalog_batch_extract_v1"
    assert doc["aggregate_stats"]["prospect_count"] == 3


def test_merge_plan_skips_already_merged_contrib_prospects() -> None:
    from scripts.merge_zone_f_code_template_prospect_v1_lib import load_catalog_rows, plan_prospect_merge

    catalog_path = ROOT / "codebook/templates/zone_f_code_templates_v1.jsonl"
    production = load_catalog_rows(catalog_path)
    assert len(production) == 22
    # Simulate re-extracted contrib seeds (zf_t20–22) after production merge; repo prospect may be empty.
    contrib_ids = {"zf_t20", "zf_t21", "zf_t22"}
    prospect = [
        {
            "template_id": f"prospect_{row['template_id']}",
            "shard_id": row.get("shard_id"),
            "language": row.get("language"),
            "snippet": row.get("snippet"),
            "must_keep_terms": row.get("must_keep_terms") or [],
            "source_row_id": row.get("source_row_id"),
        }
        for row in production
        if str(row.get("template_id") or "") in contrib_ids
    ]
    assert len(prospect) == 3
    plan = plan_prospect_merge(production_rows=production, prospect_rows=prospect)
    assert plan["merge_count"] == 0
    assert plan["skipped_count"] == 3
    assert plan["production_after_count"] == 22


def test_merge_requires_reviewer_when_approved(tmp_path: Path) -> None:
    prod = tmp_path / "prod.jsonl"
    prospect = tmp_path / "prospect.jsonl"
    prospect.write_text(
        (ROOT / "codebook/templates/zone_f_code_templates_prospect_v1.jsonl").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    prod.write_text('{"template_id":"zf_t01","shard_id":"zone_f_code","language":"python","snippet":"x","must_keep_terms":["api"]}\n', encoding="utf-8")
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
    prod_src = ROOT / "codebook/templates/zone_f_code_templates_v1.jsonl"
    prod = tmp_path / "prod.jsonl"
    prospect = tmp_path / "prospect.jsonl"
    pre_merge_lines = [line for line in prod_src.read_text(encoding="utf-8").splitlines() if line.strip()][:16]
    prod.write_text("\n".join(pre_merge_lines) + "\n", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"input_jsonl": ["data/compression/fixtures/zone_f_code_corpus_extract_fixture_v1.jsonl"]}),
        encoding="utf-8",
    )
    batch_report = tmp_path / "batch.json"
    proc_batch = subprocess.run(
        [
            sys.executable,
            str(BATCH_RUNNER),
            "--manifest",
            str(manifest),
            "--catalog",
            str(prod),
            "--prospect-out",
            str(prospect),
            "--report-out",
            str(batch_report),
            "--artifact-out",
            str(tmp_path / "batch_art.json"),
            "--write-prospect",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc_batch.returncode == 0, proc_batch.stderr or proc_batch.stdout
    before = len(pre_merge_lines)
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
    assert after == before + 3
    doc = json.loads((tmp_path / "merge.json").read_text(encoding="utf-8"))
    assert doc["applied"] is True
    assert doc["reviewer"] == "commander_test"
