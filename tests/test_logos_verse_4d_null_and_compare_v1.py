# @MKM12-METADATA
# Type: Logic
# Purpose: logos_verse_4d null corpus + OS compare smoke (Track B Phase 4).
# Keywords: logos, track_b, verse_4d, null, os_compare

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_NULL_BUILDER = _ROOT / "scripts/build_logos_verse_4d_null_corpus_v1.py"
_COMPARE = _ROOT / "scripts/compare_logos_verse_4d_os_metrics_v1.py"
_COMPARE_SCHEMA = _ROOT / "docs/final/schemas/logos_verse_4d_os_compare_v1.schema.json"
_DEFAULT_CANON = _ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_v1_latest.jsonl"


def test_os_compare_schema_draft07() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(_COMPARE_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator.check_schema(schema)


def test_null_and_compare_smoke_max_30(tmp_path: Path) -> None:
    src = _DEFAULT_CANON
    if not src.is_file():
        pytest.skip("logos_verse_4d_v1_latest.jsonl not present")

    out_vec = tmp_path / "null_vec.jsonl"
    out_char = tmp_path / "null_char.jsonl"
    out_tok = tmp_path / "null_tok.jsonl"
    cp_null = subprocess.run(
        [
            sys.executable,
            str(_NULL_BUILDER),
            "--input-jsonl",
            str(src),
            "--max-rows",
            "30",
            "--seed",
            "42",
            "--skip-apocrypha",
            "--out-vector-permutation",
            str(out_vec),
            "--out-char-shuffle",
            str(out_char),
            "--out-token-shuffle",
            str(out_tok),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert cp_null.returncode == 0, cp_null.stderr + cp_null.stdout
    for p in (out_vec, out_char, out_tok):
        lines = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert len(lines) == 30

    out_report = tmp_path / "compare.json"
    cp_cmp = subprocess.run(
        [
            sys.executable,
            str(_COMPARE),
            "--corpus",
            f"canon={src}",
            "--corpus",
            f"null_vector_permutation={out_vec}",
            "--corpus",
            f"null_char_shuffle={out_char}",
            "--corpus",
            f"null_token_shuffle={out_tok}",
            "--max-rows",
            "30",
            "--sample-size",
            "30",
            "--top-k",
            "4",
            "--out-json",
            str(out_report),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert cp_cmp.returncode == 0, cp_cmp.stderr + cp_cmp.stdout
    report = json.loads(out_report.read_text(encoding="utf-8"))
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(_COMPARE_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(report)
    assert report["track_wall"]["ready_for_external_send"] is False
    assert len(report["corpora"]) == 4
    assert "null_vector_permutation" in report["deltas_vs_canon"]


def test_phase4_chain_smoke_max_30(tmp_path: Path) -> None:
    """Phase-4 orchestration smoke — outputs stay under tmp_path (never *_latest.jsonl)."""
    src = _DEFAULT_CANON
    if not src.is_file():
        pytest.skip("logos_verse_4d_v1_latest.jsonl not present")
    out_vec = tmp_path / "null_vec.jsonl"
    out_char = tmp_path / "null_char.jsonl"
    out_tok = tmp_path / "null_tok.jsonl"
    cp_null = subprocess.run(
        [
            sys.executable,
            str(_NULL_BUILDER),
            "--input-jsonl",
            str(src),
            "--max-rows",
            "30",
            "--seed",
            "42",
            "--skip-apocrypha",
            "--out-vector-permutation",
            str(out_vec),
            "--out-char-shuffle",
            str(out_char),
            "--out-token-shuffle",
            str(out_tok),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert cp_null.returncode == 0, cp_null.stderr + cp_null.stdout
    out_report = tmp_path / "compare.json"
    cp_cmp = subprocess.run(
        [
            sys.executable,
            str(_COMPARE),
            "--corpus",
            f"canon={src}",
            "--corpus",
            f"null_vector_permutation={out_vec}",
            "--corpus",
            f"null_char_shuffle={out_char}",
            "--corpus",
            f"null_token_shuffle={out_tok}",
            "--max-rows",
            "30",
            "--sample-size",
            "30",
            "--top-k",
            "4",
            "--out-json",
            str(out_report),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert cp_cmp.returncode == 0, cp_cmp.stderr + cp_cmp.stdout
    report = json.loads(out_report.read_text(encoding="utf-8"))
    assert report["corpora"][0]["rows"] == 30
