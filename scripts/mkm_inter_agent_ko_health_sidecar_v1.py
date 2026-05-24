#!/usr/bin/env python3
"""[HYPO] B-track KO health sidecar lexicon overlay (research_only; not production bridge)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from scripts.mkm_inter_agent_ko_tokenization_v1 import TokenizationMode, tokenize

_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SIDECAR = _ROOT / "docs/final/artifacts/mkm_inter_agent_ko_health_sidecar_lexicon_v1.json"


@lru_cache(maxsize=4)
def _load_sidecar(path_str: str) -> tuple[frozenset[str], dict[str, str]]:
    doc = json.loads(Path(path_str).read_text(encoding="utf-8"))
    if doc.get("schema") != "mkm_inter_agent_ko_health_sidecar_lexicon_v1":
        return frozenset(), {}
    forms: set[str] = set()
    form_to_atom: dict[str, str] = {}
    for ent in doc.get("entries") or []:
        if not isinstance(ent, dict):
            continue
        nf = str(ent.get("normalized_form") or "").strip().lower()
        aid = str(ent.get("atom_id") or "").strip()
        if not nf or not aid:
            continue
        forms.add(nf)
        form_to_atom.setdefault(nf, aid)
    return frozenset(forms), form_to_atom


def sidecar_atom_sequence_for_text(
    raw: str,
    sidecar_path: Path | None = None,
    *,
    tokenization: TokenizationMode = "hangul_syllable",
    max_atoms: int = 48,
) -> tuple[list[str], dict[str, Any]]:
    path = (sidecar_path or DEFAULT_SIDECAR).resolve()
    if not path.is_file():
        return [], {"status": "skipped", "reason": "sidecar_missing", "path": str(path)}
    forms, form_to_atom = _load_sidecar(str(path))
    sequence: list[str] = []
    seen: set[str] = set()
    for tok in tokenize(raw, tokenization):
        key = tok.lower() if tok.isascii() else tok
        if len(key) < 1:
            continue
        if key not in form_to_atom or key in seen:
            continue
        seen.add(key)
        sequence.append(form_to_atom[key])
        if len(sequence) >= max_atoms:
            break
    return sequence, {
        "status": "ok",
        "path": str(path),
        "tokenization": tokenization,
        "sidecar_term_count": len(forms),
        "atom_id_count": len(sequence),
        "research_only": True,
        "hypothesis_tier": "B",
    }


def merged_atom_sequence_for_text(
    raw: str,
    main_codebook_path: Path,
    sidecar_path: Path | None = None,
    *,
    tokenization: TokenizationMode = "word",
) -> tuple[list[str], dict[str, Any]]:
    """Main lexicon atoms (appearance order) then sidecar fill-ins for unmatched tokens."""
    from scripts.core.master_codebook_lexicon_v1_bridge import lexicon_atom_sequence_for_text

    main_seq, main_meta = lexicon_atom_sequence_for_text(raw, main_codebook_path)
    side_seq, side_meta = sidecar_atom_sequence_for_text(
        raw, sidecar_path, tokenization=tokenization
    )
    merged: list[str] = []
    seen: set[str] = set()
    for aid in main_seq + side_seq:
        if aid in seen:
            continue
        seen.add(aid)
        merged.append(aid)
    return merged, {
        "main": main_meta,
        "sidecar": side_meta,
        "merged_atom_id_count": len(merged),
        "main_atom_id_count": len(main_seq),
        "sidecar_atom_id_count": len(side_seq),
        "tokenization": tokenization,
        "research_only": True,
    }
