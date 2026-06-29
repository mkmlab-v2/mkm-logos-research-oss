"""Build personadiary B-track LoRA corpus from inbox exports (research_only)."""

from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
EXPORT_SCHEMA = ROOT / "docs/final/schemas/personadiary_btrack_export_v1.schema.json"
EXPORT_FIXTURE = ROOT / "docs/final/artifacts/fixtures/personadiary_btrack_export_v1.example.json"


def _load_builder():
    spec = importlib.util.spec_from_file_location(
        "build_personadiary_btrack_lora_corpus_v1",
        ROOT / "scripts/build_personadiary_btrack_lora_corpus_v1.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_build_corpus_from_fixture_inbox(tmp_path: Path) -> None:
    mod = _load_builder()
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    shutil.copy(EXPORT_FIXTURE, inbox / "sample_export.json")

    export_schema = json.loads(EXPORT_SCHEMA.read_text(encoding="utf-8"))
    out_jsonl = tmp_path / "corpus.jsonl"
    rows, errors = mod.build_corpus(
        inbox_dir=inbox,
        out_jsonl=out_jsonl,
        export_schema=export_schema,
    )

    assert errors == []
    assert len(rows) == 1
    assert rows[0]["schema"] == "personadiary_btrack_lora_corpus_row_v1"
    assert rows[0]["hypothesis_tier"] == "B"
    assert rows[0]["north_star_lines"]["body"]

    lines = out_jsonl.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["source_pseudonym_id"].startswith("pdexp_")


def test_build_corpus_skips_invalid_files(tmp_path: Path) -> None:
    mod = _load_builder()
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "bad.json").write_text('{"schema":"wrong"}', encoding="utf-8")
    shutil.copy(EXPORT_FIXTURE, inbox / "good.json")

    export_schema = json.loads(EXPORT_SCHEMA.read_text(encoding="utf-8"))
    out_jsonl = tmp_path / "corpus.jsonl"
    rows, errors = mod.build_corpus(
        inbox_dir=inbox,
        out_jsonl=out_jsonl,
        export_schema=export_schema,
    )

    assert len(rows) == 1
    assert len(errors) == 1
