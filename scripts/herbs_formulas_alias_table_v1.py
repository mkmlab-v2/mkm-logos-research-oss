#!/usr/bin/env python3
"""Herbs/formulas alias table loader + resolver (B-track fixture PoC; not 41k lexicon)."""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TABLE_PATH = ROOT / "tests" / "fixtures" / "herbs_formulas_alias_table_minimal_v1.json"
TABLE_SCHEMA = "herbs_formulas_alias_table_v1"
RESOLVE_SCHEMA = "herbs_formulas_alias_resolve_v1"

_WS_RE = re.compile(r"\s+")


def normalize_alias(text: str) -> str:
    return _WS_RE.sub(" ", text.strip().lower())


def default_table_path() -> Path:
    raw = os.environ.get("MKM_HERBS_FORMULAS_ALIAS_TABLE_PATH", "").strip()
    if raw:
        path = Path(raw)
        return path if path.is_absolute() else ROOT / path
    artifact = ROOT / "docs/final/artifacts/herbs_formulas_alias_table_v1_latest.json"
    if artifact.is_file():
        return artifact
    return DEFAULT_TABLE_PATH


def load_alias_table(path: Path | None = None) -> dict[str, Any]:
    table_path = (path or default_table_path()).resolve()
    if not table_path.is_file():
        raise FileNotFoundError(f"missing alias table: {table_path}")
    doc = json.loads(table_path.read_text(encoding="utf-8"))
    if doc.get("schema") != TABLE_SCHEMA:
        raise ValueError(f"unexpected alias table schema: {doc.get('schema')!r}")
    return doc


def _herb_index(table: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for herb in table.get("herbs", []):
        if not isinstance(herb, dict):
            continue
        canonical_id = str(herb.get("canonical_id") or "")
        if not canonical_id:
            continue
        names: list[str] = []
        for key in ("canonical_name_hans", "canonical_name_ko", "pinyin"):
            val = herb.get(key)
            if isinstance(val, str) and val.strip():
                names.append(val.strip())
        for alias in herb.get("aliases", []):
            if isinstance(alias, str) and alias.strip():
                names.append(alias.strip())
        for name in names:
            index[normalize_alias(name)] = herb
    return index


def _formula_index(table: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for formula in table.get("formulas", []):
        if not isinstance(formula, dict):
            continue
        formula_id = str(formula.get("formula_id") or "")
        if not formula_id:
            continue
        names: list[str] = []
        for key in ("canonical_name_hans", "canonical_name_ko"):
            val = formula.get(key)
            if isinstance(val, str) and val.strip():
                names.append(val.strip())
        for alias in formula.get("aliases", []):
            if isinstance(alias, str) and alias.strip():
                names.append(alias.strip())
        for name in names:
            index[normalize_alias(name)] = formula
    return index


def _herb_by_id(table: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for herb in table.get("herbs", []):
        if isinstance(herb, dict) and herb.get("canonical_id"):
            out[str(herb["canonical_id"])] = herb
    return out


def resolve_single_query(
    query: str,
    *,
    table: dict[str, Any],
    include_formula_composition: bool = False,
) -> dict[str, Any]:
    normalized = normalize_alias(query)
    if not normalized:
        return {
            "query": query,
            "match_type": "none",
            "normalized_query": normalized,
            "confidence": 0.0,
        }

    herb_index = _herb_index(table)
    if normalized in herb_index:
        herb = herb_index[normalized]
        return {
            "query": query,
            "match_type": "herb",
            "normalized_query": normalized,
            "canonical_id": herb.get("canonical_id"),
            "canonical_name_hans": herb.get("canonical_name_hans"),
            "canonical_name_ko": herb.get("canonical_name_ko"),
            "confidence": 1.0,
        }

    formula_index = _formula_index(table)
    if normalized in formula_index:
        formula = formula_index[normalized]
        result: dict[str, Any] = {
            "query": query,
            "match_type": "formula",
            "normalized_query": normalized,
            "canonical_id": formula.get("formula_id"),
            "canonical_name_hans": formula.get("canonical_name_hans"),
            "canonical_name_ko": formula.get("canonical_name_ko"),
            "confidence": 1.0,
        }
        if include_formula_composition:
            result["composition"] = formula.get("composition", [])
        return result

    return {
        "query": query,
        "match_type": "none",
        "normalized_query": normalized,
        "confidence": 0.0,
    }


def resolve_alias_queries(
    queries: list[str],
    *,
    table_path: Path | None = None,
    include_formula_composition: bool = False,
) -> dict[str, Any]:
    table = load_alias_table(table_path)
    results = [
        resolve_single_query(q, table=table, include_formula_composition=include_formula_composition)
        for q in queries
    ]
    table_file = (table_path or default_table_path()).resolve()
    return {
        "schema": RESOLVE_SCHEMA,
        "version": "1.0.0",
        "research_only": True,
        "track_b_only": True,
        "send_gate": "HOLD",
        "expert_review_required": True,
        "boundary_ack": table.get(
            "boundary_ack",
            "Alias resolve is assistive only; expert must verify before clinical use.",
        ),
        "table_path": table_file.as_posix(),
        "table_schema": TABLE_SCHEMA,
        "include_formula_composition": include_formula_composition,
        "results": results,
        "integrity_flags": {
            "fixture_table": "minimal" in table_file.name,
            "curated_artifact": table_file.name.endswith("_latest.json"),
            "not_full_materia_medica": True,
            "not_logos_lexicon_bridge": True,
            "herb_count": len(table.get("herbs", [])),
            "formula_count": len(table.get("formulas", [])),
        },
    }


@lru_cache(maxsize=1)
def cached_default_table_mtime() -> float:
    path = default_table_path()
    return path.stat().st_mtime if path.is_file() else 0.0
