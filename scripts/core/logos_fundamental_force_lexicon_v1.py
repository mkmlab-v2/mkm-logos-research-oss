"""Fundamental-force pedagogical lexicon — alias only; kernel unchanged."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
LEXICON = ROOT / "docs/final/artifacts/logos_fundamental_force_lexicon_v1.json"


@lru_cache(maxsize=1)
def load_lexicon(path: Path | None = None) -> dict[str, Any]:
    p = path or LEXICON
    doc = json.loads(p.read_text(encoding="utf-8"))
    if doc.get("kernel_recipe_id") != "gematria_bridge_v1":
        raise ValueError("fundamental_force_lexicon must not override kernel recipe")
    return doc


def primitive_to_force(primitive: str, *, lexicon_path: Path | None = None) -> dict[str, Any] | None:
    for entry in load_lexicon(lexicon_path).get("entries", []):
        if entry.get("primitive") == primitive:
            return dict(entry)
    return None


def force_to_primitive(force_id: str, *, lexicon_path: Path | None = None) -> str | None:
    for entry in load_lexicon(lexicon_path).get("entries", []):
        if entry.get("force_id") == force_id:
            return str(entry.get("primitive"))
    return None


def format_force_copy_ko(primitive: str, *, lexicon_path: Path | None = None) -> str:
    row = primitive_to_force(primitive, lexicon_path=lexicon_path)
    if not row:
        return f"[HYPO] primitive={primitive}"
    return (
        f"[HYPO] {row['force_label_ko']} ↔ {row['sasang_label_ko']} "
        f"({row['kernel_param']}); 물리·체질 단정 아님"
    )
