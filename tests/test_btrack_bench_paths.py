from __future__ import annotations

import json
from pathlib import Path

import tools.myeongni as myeongni_pkg
from tools.myeongni.btrack_bench_paths import (
    CANONICAL_A_TRACK_EVAL,
    CANONICAL_BENCH_POINTER,
    CROSS_REF_BOOTSTRAP_A_TRACK_EVAL,
    DIRECT_A_TRACK_EVAL,
)

_ROOT = Path(__file__).resolve().parents[1]


def test_canonical_filenames_are_distinct_from_direct_and_bootstrap() -> None:
    assert CANONICAL_A_TRACK_EVAL != DIRECT_A_TRACK_EVAL
    assert CANONICAL_A_TRACK_EVAL != CROSS_REF_BOOTSTRAP_A_TRACK_EVAL


def test_package_reexports_bench_paths() -> None:
    assert myeongni_pkg.CANONICAL_A_TRACK_EVAL == CANONICAL_A_TRACK_EVAL
    assert myeongni_pkg.CANONICAL_BENCH_POINTER == CANONICAL_BENCH_POINTER


def test_pointer_json_exists_and_schema() -> None:
    p = _ROOT / CANONICAL_BENCH_POINTER
    assert p.is_file(), f"missing {p}"
    doc = json.loads(p.read_text(encoding="utf-8"))
    assert doc.get("schema") == "btrack_canonical_bench_pointer_v1"
    assert "canonical_builder_script" in doc
    assert str(doc.get("canonical_a_track_eval", "")).endswith("a_track_eval.jsonl")
