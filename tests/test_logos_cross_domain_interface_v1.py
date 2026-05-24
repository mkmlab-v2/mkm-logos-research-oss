# @MKM12-METADATA
# Type: Logic
# Purpose: Regression for CDIM v1 read-only assembler.
# Keywords: cdim, cross_domain, fusion_stub, logos

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_ASSEMBLER = _ROOT / "scripts" / "assemble_logos_cross_domain_interface_v1.py"
_SCHEMA = _ROOT / "docs" / "final" / "schemas" / "logos_cross_domain_interface_v1.schema.json"
_DESIGN = _ROOT / "docs" / "final" / "LOGOS_CROSS_DOMAIN_INTERFACE_MAPPER_V1.md"
_FUSION_RUNNER = _ROOT / "scripts" / "report_independent_lens_fusion_stub_v0.py"
_FIXTURE_LOGOS_BATCH = _ROOT / "tests" / "fixtures" / "logos_4lens_batch_minimal_v1.json"


def _minimal_lens(schema: str, lens_id: str, direction: float, conf: float) -> dict:
    return {
        "schema": schema,
        "version": "0.1.0",
        "lens_id": lens_id,
        "engine_id": "independent_lens_v0",
        "ts_utc": "2026-05-02T12:00:00Z",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "scores": {"direction_score": direction, "confidence": conf},
    }


def test_design_doc_and_schema_exist() -> None:
    assert _DESIGN.is_file()
    assert _SCHEMA.is_file()
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    assert schema["properties"]["schema"]["const"] == "logos_cross_domain_interface_v1"


def test_schema_valid_draft07() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator.check_schema(schema)


def _write_minimal_fusion(tmp_path: Path) -> Path:
    mye = tmp_path / "myeongni.json"
    sas = tmp_path / "sasang.json"
    logos = tmp_path / "logos.json"
    mye.write_text(
        json.dumps(_minimal_lens("myeongni_independent_lens_v0", "myeongni", 0.5, 0.6), ensure_ascii=False),
        encoding="utf-8",
    )
    sas.write_text(
        json.dumps(_minimal_lens("sasang_independent_lens_v0", "sasang", -0.2, 0.5), ensure_ascii=False),
        encoding="utf-8",
    )
    logos_doc = _minimal_lens("logos_independent_lens_v0", "logos", -0.3, 0.4)
    logos_doc["evidence_refs"] = [{"verse_id": "JHN.3.16", "hash_tagged_snippet": "[#JHN.3.16]"}]
    logos.write_text(json.dumps(logos_doc, ensure_ascii=False), encoding="utf-8")

    fusion_out = tmp_path / "fusion.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(_FUSION_RUNNER),
            "--myeongni",
            str(mye),
            "--sasang",
            str(sas),
            "--logos",
            str(logos),
            "--output",
            str(fusion_out),
            "--no-market-sasang",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr
    return fusion_out


def test_assembler_emits_cdim(tmp_path: Path) -> None:
    fusion_out = _write_minimal_fusion(tmp_path)
    out = tmp_path / "cdim.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(_ASSEMBLER),
            "--fusion-json",
            str(fusion_out),
            "--no-cross-rag",
            "--no-state-mapping",
            "--no-concept-bridge",
            "--output",
            str(out),
            "--validate",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_cross_domain_interface_v1"
    assert doc["version"] == "1.0.0"
    assert doc["boundary_ack"] is True
    assert doc["no_verse_level_ohaeng_ingest"] is True
    assert "HYPO" in doc["labels"]
    assert len(doc["lens_snapshots"]) >= 3
    assert len(doc["cross_refs"]) >= 1
    assert "universal_ohaeng_taxonomy_on_bible_corpus" in doc["forbidden_claims"]
    for ref in doc["cross_refs"]:
        assert ref["relation_type"] in (
            "align",
            "conflict",
            "ref_only",
            "4d_cosine_assign",
            "concept_path",
            "graphrag_route",
        )


def test_forbidden_claims_no_topology_overlap_word_in_schema_only() -> None:
    """Regression: limitation strings may mention topology; schema must not require % fields."""
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    props = schema.get("properties") or {}
    assert "topology_overlap_percent" not in props
