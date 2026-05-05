# -*- coding: utf-8 -*-
"""지장간(地支藏干) LUT v1 — 결정론 조회만; 해석·4D 가중치는 별도 policy."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

_PILLAR_KEYS = ("year", "month", "day", "hour")

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LUT = ROOT / "data" / "myeongni" / "jijangan_lut_v1.json"
SCHEMA_PATH = ROOT / "docs" / "final" / "schemas" / "jijangan_lut_v1.schema.json"

JIJI = frozenset({"자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"})


@lru_cache(maxsize=1)
def load_lut(path: Path | None = None) -> dict[str, Any]:
    p = path or DEFAULT_LUT
    doc = json.loads(p.read_text(encoding="utf-8"))
    if doc.get("schema") != "jijangan_lut_v1":
        raise ValueError("LUT schema must be jijangan_lut_v1")
    branches = doc.get("branches")
    if not isinstance(branches, dict):
        raise ValueError("branches missing")
    keys = set(branches.keys())
    if keys != JIJI:
        raise ValueError(f"branches must cover 12 지지; got {sorted(keys)}")
    return doc


def hidden_stems_for_branch(ji: str, *, lut_path: Path | None = None) -> list[dict[str, Any]]:
    """Return 지장간 rows for a single 지지 (한글 1글자)."""
    if not ji or len(ji) != 1:
        raise ValueError("ji must be a single Korean branch character")
    doc = load_lut(lut_path)
    branches = doc["branches"]
    row = branches.get(ji)
    if row is None:
        raise KeyError(f"unknown branch: {ji!r}")
    return list(row)


def all_gans_for_branch(ji: str, *, lut_path: Path | None = None) -> list[str]:
    """Flatten to 천간 문자열만 (순서 유지: 정기→중기→여기)."""
    return [x["gan"] for x in hidden_stems_for_branch(ji, lut_path=lut_path)]


def validate_against_schema_file(doc: dict[str, Any], schema_path: Path | None = None) -> None:
    """Optional Draft7 check when jsonschema is installed."""
    sp = schema_path or SCHEMA_PATH
    try:
        import jsonschema
    except ImportError:
        return
    schema = json.loads(sp.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)


def jijangan_overlay_for_saju(
    saju: Mapping[str, Any] | None,
    *,
    lut_path: Path | None = None,
) -> dict[str, Any]:
    """사주 네 기둥(간지 문자열)의 지지 1글자 → 지장간 행. 해석·가중치 없음."""
    doc = load_lut(lut_path)
    inner = dict(saju or {})
    pillars_out: dict[str, Any] = {}
    for key in _PILLAR_KEYS:
        pillar = inner.get(key) or ""
        ji = pillar[1] if len(pillar) >= 2 else ""
        entry: dict[str, Any] = {"pillar": pillar, "ji": ji or None}
        if not ji:
            entry["hidden_stems"] = []
            entry["note"] = "short_or_empty_pillar"
        elif ji not in JIJI:
            entry["hidden_stems"] = []
            entry["note"] = "ji_not_in_lut_alphabet"
        else:
            entry["hidden_stems"] = hidden_stems_for_branch(ji, lut_path=lut_path)
        pillars_out[key] = entry
    return {
        "schema": "jijangan_overlay_v1",
        "lut_schema": doc.get("schema"),
        "lut_version": doc.get("version"),
        "pillars": pillars_out,
    }
