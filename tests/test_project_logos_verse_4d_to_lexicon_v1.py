# @MKM12-METADATA
# Type: Logic
# Purpose: Smoke test project_logos_verse_4d_to_lexicon_v1 (Track B Phase 3).
# Keywords: logos, verse_4d, lexicon, codebook

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "project_logos_verse_4d_to_lexicon_v1.py"
_ROW_SCHEMA = _ROOT / "docs/final/schemas/logos_verse_4d_v1.schema.json"
_LEXICON_SCHEMA = _ROOT / "docs/final/schemas/lexicon_4d_v1.schema.json"
_EXAMPLE = _ROOT / "docs/final/artifacts/fixtures/logos_verse_4d_v1.example.json"
_TRACK_WALL = {
    "a_track_auto_promotion": False,
    "live_trading_trigger": False,
    "ready_for_external_send": False,
}


def _minimal_verse(verse_id: str, text: str, vec: dict[str, float]) -> dict:
    base = json.loads(_EXAMPLE.read_text(encoding="utf-8"))
    base["verse_id"] = verse_id
    base["text_span"]["original_script_text"] = text
    base["vector_4d"] = vec
    return base


def _tiny_codebook(tmp_path: Path) -> Path:
    p = tmp_path / "master_codebook_lexicon_v1_3_rows_latest.json"
    p.write_text(
        json.dumps(
            {
                "schema": "master_codebook_lexicon_v1",
                "row_count": 3,
                "entries": [
                    {
                        "atom_id": "hebrew::ברא",
                        "lang": "hebrew",
                        "normalized_form": "ברא",
                        "occurrences": 10,
                    },
                    {
                        "atom_id": "hebrew::אלהים",
                        "lang": "hebrew",
                        "normalized_form": "אלהים",
                        "occurrences": 8,
                    },
                    {
                        "atom_id": "greek::θεος",
                        "lang": "greek",
                        "normalized_form": "θεος",
                        "occurrences": 5,
                    },
                ],
                "inputs": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return p


def test_lexicon_schema_draft07() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(_LEXICON_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator.check_schema(schema)


def test_project_smoke_mock_codebook(tmp_path: Path) -> None:
    if not _EXAMPLE.is_file():
        pytest.skip("logos_verse_4d_v1.example.json missing")

    verse_path = tmp_path / "verses.jsonl"
    v1 = _minimal_verse("Gen.1.1", "בָּרָא אֱלֹהִים", {"S": 0.2, "L": 0.3, "K": 0.4, "M": 0.1})
    v2 = _minimal_verse("Gen.1.2", "בָּרָא אֱלֹהִים", {"S": 0.4, "L": 0.2, "K": 0.3, "M": 0.1})
    v3 = _minimal_verse("Jn.1.1", "θεος", {"S": 0.5, "L": 0.1, "K": 0.2, "M": 0.2})
    verse_path.write_text(
        "\n".join(json.dumps(v, ensure_ascii=False) for v in (v1, v2, v3)) + "\n",
        encoding="utf-8",
    )

    codebook = _tiny_codebook(tmp_path)
    out_jsonl = tmp_path / "with_atoms.jsonl"
    out_lex = tmp_path / "lexicon_4d.json"

    cp = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--verse-jsonl",
            str(verse_path),
            "--codebook-json",
            str(codebook),
            "--max-rows",
            "50",
            "--min-verse-count-for-lexicon",
            "2",
            "--out-jsonl",
            str(out_jsonl),
            "--out-lexicon-4d-json",
            str(out_lex),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    summary = json.loads(cp.stdout.strip().splitlines()[-1])
    assert summary["ok"] is True
    assert summary["stats"]["verses_processed"] == 3
    assert summary["stats"]["verses_with_atom_match"] >= 2
    assert summary["stats"]["token_match_rate"] > 0

    lines = [ln for ln in out_jsonl.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 3
    jsonschema = pytest.importorskip("jsonschema")
    row_schema = json.loads(_ROW_SCHEMA.read_text(encoding="utf-8"))
    for ln in lines:
        row = json.loads(ln)
        jsonschema.Draft7Validator(row_schema).validate(row)
        overlay = row.get("atom_overlay") or {}
        assert overlay.get("overlay_recipe_id") == "project_logos_verse_4d_to_lexicon_v1"
        if row["verse_id"] == "Gen.1.1":
            assert overlay.get("top_atoms")
            wsum = sum(a["weight"] for a in overlay["top_atoms"])
            assert abs(wsum - 1.0) < 1e-5

    lex_doc = json.loads(out_lex.read_text(encoding="utf-8"))
    lex_schema = json.loads(_LEXICON_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(lex_schema).validate(lex_doc)
    assert lex_doc["schema"] == "lexicon_4d_v1"
    assert lex_doc["track_wall"] == _TRACK_WALL
    # ברא appears in two verses -> included at min_verse_count=2
    forms = {r["normalized_form"] for r in lex_doc["rows"]}
    assert "ברא" in forms


def test_real_corpus_smoke_if_present() -> None:
    verse_path = _ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_v1_latest.jsonl"
    if not verse_path.is_file():
        pytest.skip("logos_verse_4d_v1_latest.jsonl not present")
    from scripts.core.master_codebook_lexicon_v1_bridge import resolve_latest_codebook_path

    if resolve_latest_codebook_path() is None:
        pytest.skip("master codebook export not present")

    cp = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--verse-jsonl",
            str(verse_path),
            "--max-rows",
            "50",
            "--out-jsonl",
            str(verse_path.parent / "_pytest_with_atoms_sample.jsonl"),
            "--out-lexicon-4d-json",
            str(verse_path.parent / "_pytest_lexicon_4d_sample.json"),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    (verse_path.parent / "_pytest_with_atoms_sample.jsonl").unlink(missing_ok=True)
    (verse_path.parent / "_pytest_lexicon_4d_sample.json").unlink(missing_ok=True)
