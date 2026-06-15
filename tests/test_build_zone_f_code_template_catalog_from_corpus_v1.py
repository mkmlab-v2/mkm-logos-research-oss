"""zone_f_code template seed extraction from customer JSONL corpora."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data/compression/fixtures/zone_f_code_corpus_extract_fixture_v1.jsonl"
SHARD = ROOT / "codebook/shards/zone_f_code.json"
CATALOG = ROOT / "codebook/templates/zone_f_code_templates_v1.jsonl"
BUILDER = ROOT / "scripts/build_zone_f_code_template_catalog_from_corpus_v1.py"


def test_extract_fenced_and_snippet_fields() -> None:
    from scripts.extract_zone_f_code_template_seeds_v1_lib import (
        extract_from_jsonl,
        load_zone_f_code_shard,
    )

    shard = load_zone_f_code_shard(SHARD)
    result = extract_from_jsonl(FIXTURE, shard=shard, existing_snippets=set(), min_score=2)
    assert result["rows_scanned"] == 5
    assert result["candidates_deduped"] == 3
    assert result["candidates_novel"] == 3
    ids = [r["template_id"] for r in result["prospect_rows"]]
    assert ids == ["zf_p001", "zf_p002", "zf_p003"]


def test_filter_existing_catalog_snippets() -> None:
    from scripts.compression_coding_deep_pack_v1_lib import load_template_catalog
    from scripts.extract_zone_f_code_template_seeds_v1_lib import (
        extract_from_jsonl,
        load_zone_f_code_shard,
    )

    existing = {str(r["snippet"]) for r in load_template_catalog(CATALOG)}
    shard = load_zone_f_code_shard(SHARD)
    result = extract_from_jsonl(FIXTURE, shard=shard, existing_snippets=existing, min_score=2)
    assert result["candidates_novel"] >= 1
    for row in result["prospect_rows"]:
        assert row["snippet"] not in existing


def test_build_catalog_from_corpus_fixture_smoke(tmp_path: Path) -> None:
    import subprocess
    import sys

    report = tmp_path / "extract_report.json"
    prospect = tmp_path / "prospect.jsonl"
    proc = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--input-jsonl",
            str(FIXTURE),
            "--write-prospect",
            "--report-out",
            str(report),
            "--artifact-out",
            str(tmp_path / "artifact.json"),
            "--prospect-out",
            str(prospect),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(report.read_text(encoding="utf-8"))
    assert doc["schema"] == "zone_f_code_template_catalog_extract_v1"
    assert doc["merge_policy"] == "prospect_only_no_auto_merge"
    assert doc["extract_stats"]["candidates_novel"] == 3
    assert doc["twin_preview"]["exact_restore_pass_count"] == 3
    assert prospect.is_file()
    rows = [json.loads(line) for line in prospect.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 3
    assert all(r.get("prospect") is True for r in rows)
