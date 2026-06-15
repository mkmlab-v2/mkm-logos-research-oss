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


def test_merge_plan_dry_run_default() -> None:
    from scripts.merge_zone_f_code_template_prospect_v1_lib import load_catalog_rows, plan_prospect_merge

    production = load_catalog_rows(ROOT / "codebook/templates/zone_f_code_templates_v1.jsonl")
    prospect = load_catalog_rows(ROOT / "codebook/templates/zone_f_code_templates_prospect_v1.jsonl")
    plan = plan_prospect_merge(production_rows=production, prospect_rows=prospect)
    assert plan["merge_count"] == 3
    assert plan["production_after_count"] == len(production) + 3
    ids = [m["new_template_id"] for m in plan["to_merge"]]
    assert ids == ["zf_t17", "zf_t18", "zf_t19"]


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
    prospect_src = ROOT / "codebook/templates/zone_f_code_templates_prospect_v1.jsonl"
    prod = tmp_path / "prod.jsonl"
    prospect = tmp_path / "prospect.jsonl"
    prod.write_text(prod_src.read_text(encoding="utf-8"), encoding="utf-8")
    prospect.write_text(prospect_src.read_text(encoding="utf-8"), encoding="utf-8")
    before = sum(1 for line in prod.read_text(encoding="utf-8").splitlines() if line.strip())
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
