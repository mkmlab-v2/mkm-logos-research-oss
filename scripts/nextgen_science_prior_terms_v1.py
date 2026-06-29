"""[HYPO] Science + sasang synergy terms for NG-40 salience / must_keep sidecar."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from scripts.nextgen_archetype_prior_terms_v1 import load_prior_terms

WORD_RE = re.compile(r"[A-Za-z0-9_가-힣]{2,}")

DEFAULT_SPEC = (
    "experiments/nextgen_clean_slate_cpu_v1/SCIENCE_PRIOR_SIDECAR_SPEC_V1.json"
)


def _tokenize_list(items: list[Any]) -> set[str]:
    out: set[str] = set()
    for item in items:
        if not item:
            continue
        s = str(item).strip().lower()
        if len(s) >= 2:
            out.add(s)
        out.update(t.lower() for t in WORD_RE.findall(str(item)))
    return out


def terms_from_science_spec(doc: dict[str, Any], *, max_science: int) -> tuple[frozenset[str], dict[str, Any]]:
    terms: set[str] = set()
    for key in (
        "science_anchor_tokens",
        "sasang_synergy_tokens",
        "myeongni_synergy_tokens",
        "physics_conservation_keywords",
    ):
        terms |= _tokenize_list(list(doc.get(key) or []))
    trimmed = frozenset(sorted(terms)[:max_science])
    meta = {
        "spec_schema": doc.get("schema"),
        "science_term_count": len(trimmed),
        "lens_roles": doc.get("lens_roles"),
    }
    return trimmed, meta


def load_science_prior_terms(
    *,
    root: Path,
    spec_path: Path | None = None,
    max_science: int = 96,
) -> tuple[frozenset[str], dict[str, Any]]:
    path = spec_path or (root / DEFAULT_SPEC)
    if not path.is_file():
        return frozenset(), {"spec_path": str(path), "present": False}
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    terms, meta = terms_from_science_spec(doc, max_science=max_science)
    meta["spec_path"] = str(path.relative_to(root)).replace("\\", "/")
    meta["present"] = True
    return terms, meta


def load_trilane_prior_terms(
    *,
    root: Path,
    spec_path: Path | None = None,
    salience_hook_path: Path | None = None,
    nav_frame_path: Path | None = None,
    logos_pack_path: Path | None = None,
    merge_archetype: bool = True,
) -> tuple[frozenset[str], dict[str, Any]]:
    """Logos(archetype) + science + sasang token union for sidecar-only use."""
    spec_file = spec_path or (root / DEFAULT_SPEC)
    merge = True
    max_combined = 320
    max_archetype = 128
    max_science = 96
    if spec_file.is_file():
        spec_doc = json.loads(spec_file.read_text(encoding="utf-8-sig"))
        mp = spec_doc.get("merge_policy") or {}
        merge = bool(mp.get("with_archetype_prior", True))
        max_combined = int(mp.get("max_combined_terms", max_combined))
        max_archetype = int(mp.get("archetype_max_terms", max_archetype))
        max_science = int(mp.get("science_max_terms", max_science))

    science_terms, science_meta = load_science_prior_terms(
        root=root, spec_path=spec_file, max_science=max_science
    )
    combined: set[str] = set(science_terms)
    archetype_meta: dict[str, Any] = {"skipped": True}
    if merge:
        archetype_terms, archetype_meta = load_prior_terms(
            root=root,
            salience_hook_path=salience_hook_path,
            nav_frame_path=nav_frame_path,
            logos_pack_path=logos_pack_path,
            max_terms=max_archetype,
        )
        combined |= set(archetype_terms)
        archetype_meta = archetype_meta

    trimmed = frozenset(sorted(combined)[:max_combined])
    meta = {
        "trilane": True,
        "science_meta": science_meta,
        "archetype_meta": archetype_meta,
        "combined_term_count": len(trimmed),
        "merge_archetype": merge,
    }
    return trimmed, meta
