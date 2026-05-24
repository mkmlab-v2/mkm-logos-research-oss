#!/usr/bin/env python3
"""Shared B-track helpers: apply CJK substitution to compression cases."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from scripts.ijeoma_cjk_compression_hypo_v1 import (  # noqa: E402
    compress_ijeoma_cjk_substitution,
    expand_ijeoma_cjk_substitution,
    resolve_marker_strategy,
)

DEFAULT_HYPO_LEX = (
    Path(__file__).resolve().parent.parent
    / "reports/constitution/btrack_pilot/ijeoma_hanja_codebook_lexicon_v1_hypo_latest.json"
)


def apply_cjk_substitution_to_cases(
    cases: list[dict[str, Any]],
    lexicon_path: Path,
    *,
    lane_meta: dict[str, Any] | None = None,
    marker_strategy: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return deep-copied cases with compressed/reconstructed from CJK substitution."""
    lex = lexicon_path.resolve()
    strategy = resolve_marker_strategy(marker_strategy)
    out_cases: list[dict[str, Any]] = []
    total_rep = 0
    for case in cases:
        c = copy.deepcopy(case)
        raw = str(c.get("raw_text") or "")
        comp, meta = compress_ijeoma_cjk_substitution(raw, lex, marker_strategy=strategy)
        rec = expand_ijeoma_cjk_substitution(comp, lex, marker_strategy=strategy)
        c["compressed_text"] = comp
        c["reconstructed_text"] = rec
        c["cjk_substitution_hypo_v1"] = meta
        total_rep += int(meta.get("replacements") or 0)
        out_cases.append(c)
    summary = {
        "lexicon_path": str(lex),
        "case_count": len(out_cases),
        "total_replacements": total_rep,
        "eval_contract": "cjk_substitution_hypo_v1",
        "marker_strategy": strategy,
    }
    if lane_meta:
        summary.update(lane_meta)
    return out_cases, summary


def load_lane_with_cjk_substitution(
    lane_path: Path,
    lexicon_path: Path | None = None,
) -> dict[str, Any]:
    """Load multilens lane JSON and apply substitution to all cases."""
    import json

    path = lane_path.resolve()
    lex = (lexicon_path or DEFAULT_HYPO_LEX).resolve()
    doc = json.loads(path.read_text(encoding="utf-8"))
    cases, summary = apply_cjk_substitution_to_cases(
        list(doc.get("compression_cases") or []),
        lex,
        lane_meta={"source_lane": str(path)},
    )
    doc = dict(doc)
    doc["compression_cases"] = cases
    doc["cjk_substitution_summary"] = summary
    return doc
