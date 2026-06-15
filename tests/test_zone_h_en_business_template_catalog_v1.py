"""zone_h_en_business template seed extraction from JSONL corpora."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data/compression/fixtures/zone_h_en_business_corpus_extract_fixture_v1.jsonl"
SHARD = ROOT / "codebook/shards/zone_h_en_business_v1.json"
BUILDER = ROOT / "scripts/build_zone_h_en_business_template_catalog_from_corpus_v1.py"
SPEC_BUILDER = ROOT / "scripts/build_compression_en_business_deep_pack_spec_v1.py"


def test_extract_en_business_prose_only() -> None:
    from scripts.extract_zone_h_en_business_template_seeds_v1_lib import (
        extract_from_jsonl,
        load_shard,
    )

    shard = load_shard(SHARD)
    result = extract_from_jsonl(FIXTURE, shard=shard, existing_snippets=set(), min_score=2)
    assert result["rows_scanned"] == 5
    assert result["candidates_deduped"] == 3
    assert result["candidates_novel"] == 3
    ids = [r["template_id"] for r in result["prospect_rows"]]
    assert ids == ["eb_p001", "eb_p002", "eb_p003"]
    for row in result["prospect_rows"]:
        assert row["shard_id"] == "zone_h_en_business_v1"
        assert row["language"] == "en"


def test_biz_mask_wire_twin_roundtrip() -> None:
    from scripts.compression_en_business_deep_pack_v1_lib import (
        measure_template_wire_twin,
        wire_to_compact,
        build_wire_packet,
    )

    snippet = "Subject: Test\n\nDear Team,\n\nInvoice payment contract compliance attached.\n\nRegards"
    rows = [
        {
            "template_id": "eb_t01",
            "shard_id": "zone_h_en_business_v1",
            "snippet": snippet,
        }
    ]
    catalog_hash = "a" * 64
    wire = build_wire_packet(template_id="eb_t01", catalog_sha256=catalog_hash)
    assert wire_to_compact(wire).startswith("[BIZ_MASK:eb_t01@")
    twin = measure_template_wire_twin(
        original_snippet=snippet,
        template_id="eb_t01",
        catalog_sha256=catalog_hash,
        catalog_rows=rows,
    )
    assert twin["exact_restore_ok"] is True
    assert twin["wire_family"] == "BIZ_MASK"
    assert twin["saving_rate"] > 0.0


def test_build_en_business_spec_smoke() -> None:
    proc = subprocess.run(
        [sys.executable, str(SPEC_BUILDER)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(
        (ROOT / "docs/final/artifacts/compression_en_business_deep_pack_spec_v1_latest.json").read_text(
            encoding="utf-8"
        )
    )
    assert doc["schema"] == "compression_en_business_deep_pack_spec_v1"
    assert doc["vertical_id"] == "zone_h_en_business_v1"
    assert doc["three_layer_layout"]["deep_pack"]["wire_prefix"] == "BIZ_MASK"


def test_build_catalog_from_corpus_fixture_smoke(tmp_path: Path) -> None:
    report = tmp_path / "extract_report.json"
    prospect = tmp_path / "prospect.jsonl"
    empty_catalog = tmp_path / "empty_catalog.jsonl"
    empty_catalog.write_text("", encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--input-jsonl",
            str(FIXTURE),
            "--catalog",
            str(empty_catalog),
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
    assert doc["schema"] == "zone_h_en_business_template_catalog_extract_v1"
    assert doc["wire_family"] == "BIZ_MASK"
    assert doc["extract_stats"]["candidates_novel"] == 3
    assert doc["twin_preview"]["exact_restore_pass_count"] == 3
    assert prospect.is_file()
    rows = [json.loads(line) for line in prospect.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 3
