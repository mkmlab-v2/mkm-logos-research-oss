#!/usr/bin/env python3
"""Gloss report v4: conservative prefix-chain lemmatization (codebook/gloss-validated peel only)."""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.master_codebook_lexicon_v1_bridge import resolve_latest_codebook_path

# Reuse lexicon rails + gloss stack from v3 (single source of truth for dictionaries).
import scripts.core.build_original_singularity_gloss_report_v3 as g3


def _keep_hebrew(token: str) -> str:
    return re.sub(r"[^\u05D0-\u05EA]", "", token)


def _prefix_chain_candidates(surface: str) -> list[str]:
    """Longest-first list: surface, strip one prefix while possible (max chain length capped)."""
    cands: list[str] = [surface]
    cur = surface
    steps = 0
    max_steps = 8
    while steps < max_steps and len(cur) >= 3 and cur[0] in g3.PREFIXES:
        cur = cur[1:]
        cands.append(cur)
        steps += 1
    return cands


def _pick_lemma_for_lookup(
    surface: str,
    codebook_forms: set[str],
    form_to_strongs: dict[str, str],
    overrides: dict[str, str],
) -> tuple[str, str]:
    """Return (lemma_token, lemma_source_tag)."""
    for cand in _prefix_chain_candidates(surface):
        if overrides.get(cand, "").strip():
            return cand, "override"
        if cand in g3.GLOSS_KO:
            return cand, "gloss_ko"
        if cand in codebook_forms:
            return cand, "codebook_form"
        s = form_to_strongs.get(cand, "")
        if s in g3.STRONGS_GLOSS_KO:
            return cand, "strongs_map"
        # suffix heuristic lives inside _gloss
        if g3._gloss(cand, form_to_strongs, overrides):
            return cand, "gloss_heuristic"
    return surface, "surface_only"


def _normalize_token_v4(
    token: str,
    codebook_forms: set[str],
    form_to_strongs: dict[str, str],
    overrides: dict[str, str],
) -> str:
    t = _keep_hebrew(token)
    if not t:
        return ""
    lemma, _src = _pick_lemma_for_lookup(t, codebook_forms, form_to_strongs, overrides)
    return lemma


def _tokenize_v4(
    text: str,
    codebook_forms: set[str],
    form_to_strongs: dict[str, str],
    overrides: dict[str, str],
) -> list[str]:
    raw = re.split(r"\s+", str(text or "").strip())
    out: list[str] = []
    for tok in raw:
        t = _normalize_token_v4(tok, codebook_forms, form_to_strongs, overrides)
        if not t:
            continue
        if t in g3.STOP_TOKENS:
            continue
        out.append(t)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Build gloss report v4 with validated prefix-chain lemmatization (conservative)."
    )
    ap.add_argument(
        "--balanced-report-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_balanced_report_v1.json",
    )
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/original_singularity_gloss_report_v4.json",
    )
    ap.add_argument(
        "--codebook-lexicon-json",
        default="",
        help="Explicit master_codebook_lexicon_v1 JSON; empty = resolve latest under btrack_pilot.",
    )
    ap.add_argument(
        "--gloss-overrides-json",
        default="docs/final/artifacts/hebrew_singularity_gloss_overrides_v1.json",
    )
    args = ap.parse_args()

    if str(args.codebook_lexicon_json).strip():
        codebook_path = Path(args.codebook_lexicon_json)
        if not codebook_path.is_absolute():
            codebook_path = ROOT / codebook_path
    else:
        pilot = ROOT / "reports" / "constitution" / "btrack_pilot"
        resolved = resolve_latest_codebook_path(out_dir=pilot)
        if resolved is None:
            print("ERROR: no master_codebook_lexicon_v1_*_rows_latest.json under btrack_pilot", flush=True)
            return 2
        codebook_path = resolved

    codebook_forms, form_to_strongs, _form_to_method = g3._load_codebook_index(str(codebook_path.resolve()))

    overrides_path = Path(args.gloss_overrides_json)
    if not overrides_path.is_absolute():
        overrides_path = ROOT / overrides_path
    overrides = g3._load_gloss_overrides(overrides_path if overrides_path.is_file() else None)

    bal_path = Path(args.balanced_report_json)
    if not bal_path.is_absolute():
        bal_path = ROOT / bal_path
    src = json.loads(bal_path.read_text(encoding="utf-8"))
    rows = src.get("balanced_union_top") or []
    per_regime = src.get("per_regime_top") or {}

    row_items: list[dict[str, Any]] = []
    global_counter: Counter[str] = Counter()
    regime_counter: dict[str, Counter[str]] = {k: Counter() for k in per_regime.keys()}

    for row in rows:
        text = str(row.get("text_preview") or "")
        tokens = _tokenize_v4(text, codebook_forms, form_to_strongs, overrides)
        for t in tokens:
            global_counter[t] += 1
        rid = str(row.get("target_regime") or "unknown")
        if rid not in regime_counter:
            regime_counter[rid] = Counter()
        for t in tokens:
            regime_counter[rid][t] += 1

        surf_tokens = re.split(r"\s+", str(text or "").strip())
        preview_rows: list[dict[str, Any]] = []
        for tok in surf_tokens[:14]:
            surf = _keep_hebrew(tok)
            if not surf:
                continue
            lemma, src_tag = _pick_lemma_for_lookup(surf, codebook_forms, form_to_strongs, overrides)
            preview_rows.append(
                {
                    "surface": surf,
                    "lemma_for_lookup": lemma,
                    "lemma_source": src_tag,
                    "gloss_ko": g3._gloss(lemma, form_to_strongs, overrides),
                    "known": bool(g3._gloss(lemma, form_to_strongs, overrides)),
                    "strongs_hint": form_to_strongs.get(lemma, ""),
                }
            )

        row_items.append(
            {
                "row_id": row.get("row_id"),
                "target_regime": rid,
                "score": float(row.get("score", 0.0)),
                "text_preview": text,
                "tokens_lemmatized": tokens[:24],
                "lemma_preview": preview_rows[:12],
            }
        )

    top_tokens_global = [
        {
            "token": t,
            "freq": int(f),
            "gloss_ko": g3._gloss(t, form_to_strongs, overrides),
            "known": bool(g3._gloss(t, form_to_strongs, overrides)),
            "strongs_hint": form_to_strongs.get(t, ""),
            "override": bool(t in overrides),
        }
        for t, f in global_counter.most_common(40)
    ]

    top_tokens_by_regime: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rid, cnt in regime_counter.items():
        for t, f in cnt.most_common(12):
            top_tokens_by_regime[rid].append(
                {
                    "token": t,
                    "freq": int(f),
                    "gloss_ko": g3._gloss(t, form_to_strongs, overrides),
                    "known": bool(g3._gloss(t, form_to_strongs, overrides)),
                    "strongs_hint": form_to_strongs.get(t, ""),
                    "override": bool(t in overrides),
                }
            )

    known_ratio = (
        (sum(1 for t in global_counter if g3._gloss(t, form_to_strongs, overrides)) / len(global_counter))
        if global_counter
        else 0.0
    )

    out = {
        "schema": "original_singularity_gloss_report_v4",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "inputs": {
            "balanced_report_json": args.balanced_report_json,
            "gloss_overrides_json": args.gloss_overrides_json if overrides_path.is_file() else "",
        },
        "bridges": {
            "master_codebook_lexicon_v1": {
                "path": str(codebook_path),
                "enabled": bool(codebook_forms),
                "hebrew_forms_loaded": len(codebook_forms),
                "strongs_hint_forms": len(form_to_strongs),
            },
            "hebrew_singularity_gloss_overrides_v1": {
                "path": str(overrides_path) if overrides_path.is_file() else "",
                "enabled": bool(overrides),
                "entry_count": len(overrides),
            },
        },
        "normalization": {
            "strategy": "validated_prefix_chain_longest_surface_first_then_peel_until_lookup_hit",
            "prefixes_chain": list(g3.PREFIXES),
            "max_chain_steps": 8,
            "stop_tokens_filtered": sorted(g3.STOP_TOKENS),
            "inherits_gloss_stack_from": "original_singularity_gloss_report_v3",
        },
        "summary": {
            "rows_in_union": len(rows),
            "unique_tokens": len(global_counter),
            "known_gloss_tokens": int(sum(1 for t in global_counter if g3._gloss(t, form_to_strongs, overrides))),
            "known_gloss_ratio": float(known_ratio),
            "codebook_hits_in_union": int(sum(1 for t in global_counter if t in codebook_forms)),
            "strongs_gloss_hits_in_union": int(
                sum(1 for t in global_counter if form_to_strongs.get(t, "") in g3.STRONGS_GLOSS_KO)
            ),
            "override_hits_in_union": int(sum(1 for t in global_counter if t in overrides)),
            "note": "Conservative lemma = first mapped candidate along validated Hebrew prefix peel; not full morphological analysis.",
        },
        "top_tokens_global": top_tokens_global,
        "top_tokens_by_regime": top_tokens_by_regime,
        "rows_glossed_preview": row_items,
    }

    out_path = Path(args.output_json)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
