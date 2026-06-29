"""Tests for herbs/formulas alias table build + expanded curated artifact."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "data/herbs_formulas/herbs_formulas_alias_seed_v1.json"
ARTIFACT = ROOT / "docs/final/artifacts/herbs_formulas_alias_table_v1_latest.json"
BUILD = ROOT / "scripts/build_herbs_formulas_alias_table_v1.py"
MINIMAL = ROOT / "tests/fixtures/herbs_formulas_alias_table_minimal_v1.json"


def test_build_alias_table_script_exit_0(tmp_path: Path) -> None:
    out = tmp_path / "alias_table.json"
    proc = subprocess.run(
        [sys.executable, str(BUILD), "--seed", str(SEED), "--out", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "herbs_formulas_alias_table_v1"
    assert doc["provenance"]["herb_count"] == 17
    assert doc["provenance"]["formula_count"] == 5


def test_build_rejects_alias_collision(tmp_path: Path) -> None:
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    seed["herbs"][0]["aliases"] = list(seed["herbs"][0].get("aliases", [])) + ["작약"]
    bad_seed = tmp_path / "bad_seed.json"
    bad_seed.write_text(json.dumps(seed, ensure_ascii=False, indent=2), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(BUILD), "--seed", str(bad_seed), "--out", str(tmp_path / "out.json")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1


@pytest.mark.skipif(not ARTIFACT.is_file(), reason="artifact not built yet")
def test_expanded_artifact_resolves_lecture_formulas() -> None:
    from scripts.herbs_formulas_alias_table_v1 import resolve_alias_queries

    doc = resolve_alias_queries(
        ["麻黄汤", "小青龙汤", "소청룡탕", "마황탕"],
        table_path=ARTIFACT,
        include_formula_composition=True,
    )
    assert doc["integrity_flags"]["herb_count"] == 17
    assert doc["integrity_flags"]["formula_count"] == 5
    assert doc["results"][0]["match_type"] == "formula"
    assert doc["results"][0]["canonical_id"] == "formula:mahuangtang"
    assert len(doc["results"][0]["composition"]) == 4
    assert doc["results"][1]["canonical_id"] == "formula:xiaoqinglongtang"
    assert len(doc["results"][1]["composition"]) == 8
    assert doc["results"][2]["canonical_id"] == "formula:xiaoqinglongtang"
    assert doc["results"][3]["canonical_id"] == "formula:mahuangtang"


@pytest.mark.skipif(not ARTIFACT.is_file(), reason="artifact not built yet")
def test_default_table_path_prefers_artifact(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MKM_HERBS_FORMULAS_ALIAS_TABLE_PATH", raising=False)
    from scripts import herbs_formulas_alias_table_v1 as mod

    mod.cached_default_table_mtime.cache_clear()
    path = mod.default_table_path()
    assert path.name == "herbs_formulas_alias_table_v1_latest.json"


def test_minimal_fixture_composition_herbs_exist() -> None:
    doc = json.loads(MINIMAL.read_text(encoding="utf-8"))
    herb_ids = {h["canonical_id"] for h in doc["herbs"]}
    for formula in doc["formulas"]:
        for row in formula["composition"]:
            assert row["herb_id"] in herb_ids
