"""Shared evo_material path map for person directory build + sync gate."""

from __future__ import annotations

from pathlib import Path
from typing import Any

# Slug -> repo-relative evo_material artifact (B-track reference only; auto_apply=none).
EVO_MATERIAL_BY_SLUG: dict[str, str] = {
    "family_son_kangmin": "docs/final/artifacts/evo_material_family_anchor_son_kangmin_v1_latest.json",
    "family_daughter": "docs/final/artifacts/evo_material_family_anchor_daughter_v1_latest.json",
    "commander": "docs/final/artifacts/evo_material_operator_commander_v1_latest.json",
}

EVO_MATERIAL_REQUIRED_SLUGS = frozenset(EVO_MATERIAL_BY_SLUG.keys())


def evo_material_refs_for_slug(root: Path, slug: str, pointer_doc: dict[str, Any] | None = None) -> list[dict[str, str]]:
    """Build evo_material_refs list for a person directory encounter row."""
    refs: list[dict[str, str]] = []
    canonical = EVO_MATERIAL_BY_SLUG.get(slug)
    if canonical:
        refs.append({"kind": "evo_material", "path": canonical})
    if pointer_doc:
        paths = pointer_doc.get("paths")
        if isinstance(paths, dict):
            explicit = paths.get("evo_material")
            if isinstance(explicit, str) and explicit.strip():
                path = explicit.strip().replace("\\", "/")
                if not any(r.get("path") == path for r in refs):
                    refs.append({"kind": "evo_material_pointer", "path": path})
    for ref in refs:
        rel = ref["path"]
        if not (root / rel).is_file():
            ref["exists"] = "false"
        else:
            ref["exists"] = "true"
    return refs


def build_evo_material_index(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for slug, rel in sorted(EVO_MATERIAL_BY_SLUG.items()):
        if (root / rel).is_file():
            out[slug] = rel
    return out
