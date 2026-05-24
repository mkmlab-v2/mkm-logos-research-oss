#!/usr/bin/env python3
"""B-track [HYPO]: logos verse surface reconstruct from lexicon anchors + comp tokens.

Research-only decoder spike — does not write Track A active or MS headline.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.master_codebook_lexicon_v1_bridge import (  # noqa: E402
    _load_atom_id_to_form,
    gloss_rows_for_atom_ids,
    lexicon_hits_for_text,
)
from scripts.report_multilens_performance_eval import (  # noqa: E402
    _jaccard,
    _reconstruct_experimental_from_raw,
    _split_words,
)

DEFAULT_LEX = ROOT / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41658_rows_latest.json"
DEFAULT_OUT = ROOT / "reports/logos_verse_surface_reconstruct_hypo_v1_latest.json"


DEFAULT_ALIGNED_POC = ROOT / "docs/final/artifacts/logos_graph_wire_rag_poc_lexicon_aligned_v1_latest.json"


def _gloss_forms_present_in_raw(atom_ids: list[str], raw: str, lexicon_path: Path) -> list[str]:
    idx = _load_atom_id_to_form(str(lexicon_path.resolve()))
    raw_l = raw.lower()
    out: list[str] = []
    seen: set[str] = set()
    for aid in atom_ids:
        form = idx.get(str(aid), "")
        if not form or form in seen:
            continue
        if form in raw or form.lower() in raw_l:
            out.append(form)
            seen.add(form)
    return out


def _append_terms_to_surface(
    raw: str,
    rec_base: str,
    terms: list[str],
) -> tuple[str, int]:
    raw_words = _split_words(raw)
    out_words = _split_words(rec_base)
    seen = {w.lower() for w in out_words}
    added = 0
    for term in terms:
        for w in raw_words:
            if w == term or w.lower() == term.lower():
                lw = w.lower()
                if lw not in seen:
                    out_words.append(w)
                    seen.add(lw)
                    added += 1
    surface = " ".join(out_words) if out_words else rec_base
    return surface, added


def surface_reconstruct_v1(
    raw: str,
    compressed: str,
    *,
    lexicon_path: Path,
    include_hit_terms: bool = True,
) -> dict[str, Any]:
    """Heuristic surface rebuild: experimental decoder + lexicon hit terms present in raw."""
    rec_base = _reconstruct_experimental_from_raw(
        raw=raw,
        compressed_candidate=compressed,
        use_hangul_principle=False,
    )
    raw_words = _split_words(raw)
    raw_lower = {w.lower() for w in raw_words}
    out_words = _split_words(rec_base)
    seen = {w.lower() for w in out_words}

    if include_hit_terms:
        hits, meta = lexicon_hits_for_text(raw, lexicon_path, min_token_len=2, include_cjk_bigrams=True)
        for term in hits:
            for w in raw_words:
                if w.lower() == term.lower() or w == term:
                    lw = w.lower()
                    if lw not in seen:
                        out_words.append(w)
                        seen.add(lw)
        hit_count = meta.get("hit_count")
    else:
        hit_count = 0

    surface = " ".join(out_words) if out_words else rec_base

    return {
        "reconstructed_surface": surface,
        "reconstructed_base": rec_base,
        "jaccard_base": round(_jaccard(raw, rec_base), 6),
        "jaccard_surface": round(_jaccard(raw, surface), 6),
        "raw_token_count": len(raw_words),
        "surface_token_count": len(_split_words(surface)),
        "lexicon_hit_count": hit_count,
    }


def surface_reconstruct_with_wire_gloss_v1(
    raw: str,
    compressed: str,
    *,
    lexicon_path: Path,
    wire_atom_ids: list[str],
    case_wire_atom_ids: list[str] | None = None,
    include_hit_terms: bool = True,
) -> dict[str, Any]:
    """Surface rebuild + lexicon hits + wire gloss forms present in raw (B-track decoder hook)."""
    base_row = surface_reconstruct_v1(
        raw, compressed, lexicon_path=lexicon_path, include_hit_terms=include_hit_terms
    )
    merged_atoms: list[str] = []
    seen_a: set[str] = set()
    for aid in list(wire_atom_ids) + list(case_wire_atom_ids or []):
        key = str(aid)
        if key and key not in seen_a:
            seen_a.add(key)
            merged_atoms.append(key)

    gloss_forms = _gloss_forms_present_in_raw(merged_atoms, raw, lexicon_path)
    surface, wire_added = _append_terms_to_surface(raw, base_row["reconstructed_surface"], gloss_forms)
    _, gloss_meta = gloss_rows_for_atom_ids(merged_atoms, lexicon_path)

    return {
        **base_row,
        "reconstructed_surface": surface,
        "jaccard_surface": round(_jaccard(raw, surface), 6),
        "surface_token_count": len(_split_words(surface)),
        "wire_atom_id_count": len(merged_atoms),
        "wire_gloss_forms_in_raw": gloss_forms,
        "wire_gloss_terms_appended": wire_added,
        "wire_known_gloss_count": gloss_meta.get("known_gloss_count"),
    }


def run_batch(cases: list[dict[str, Any]], lexicon_path: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for case in cases:
        raw = str(case.get("raw_text") or "")
        comp = str(case.get("compressed_text_effective") or case.get("compressed_text") or "")
        row = surface_reconstruct_v1(raw, comp, lexicon_path=lexicon_path)
        row["id"] = case.get("id")
        rows.append(row)

    if not rows:
        return {"case_count": 0, "rows": []}

    mean_base = sum(r["jaccard_base"] for r in rows) / len(rows)
    mean_surf = sum(r["jaccard_surface"] for r in rows) / len(rows)
    return {
        "schema": "logos_verse_surface_reconstruct_hypo_v1",
        "hypothesis_tier": "B",
        "research_only": True,
        "case_count": len(rows),
        "mean_jaccard_base": round(mean_base, 6),
        "mean_jaccard_surface": round(mean_surf, 6),
        "surface_delta_pp": round((mean_surf - mean_base) * 100.0, 2),
        "proceed_hook": mean_surf > mean_base + 0.02,
        "rows_sample": rows[:12],
    }


def run_batch_wire_gloss(
    cases: list[dict[str, Any]],
    lexicon_path: Path,
    *,
    wire_atom_ids: list[str],
    influence_map: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for case in cases:
        raw = str(case.get("raw_text") or "")
        comp = str(case.get("compressed_text_effective") or case.get("compressed_text") or "")
        cid = str(case.get("id") or "")
        inf = (influence_map or {}).get(cid) or {}
        case_atoms = [str(x) for x in (inf.get("atom_id_sequence") or []) if x]
        row = surface_reconstruct_with_wire_gloss_v1(
            raw,
            comp,
            lexicon_path=lexicon_path,
            wire_atom_ids=wire_atom_ids,
            case_wire_atom_ids=case_atoms,
        )
        row["id"] = case.get("id")
        rows.append(row)

    if not rows:
        return {"case_count": 0, "rows": []}

    mean_base = sum(r["jaccard_base"] for r in rows) / len(rows)
    mean_surf = sum(r["jaccard_surface"] for r in rows) / len(rows)
    mean_lex_only = sum(
        surface_reconstruct_v1(
            str(c.get("raw_text") or ""),
            str(c.get("compressed_text_effective") or c.get("compressed_text") or ""),
            lexicon_path=lexicon_path,
        )["jaccard_surface"]
        for c in cases
    ) / len(rows)
    return {
        "schema": "logos_verse_surface_reconstruct_wire_gloss_v1",
        "hypothesis_tier": "B",
        "research_only": True,
        "case_count": len(rows),
        "mean_jaccard_base": round(mean_base, 6),
        "mean_jaccard_surface_lexicon_only": round(mean_lex_only, 6),
        "mean_jaccard_surface_wire_gloss": round(mean_surf, 6),
        "wire_gloss_delta_pp_vs_lexicon": round((mean_surf - mean_lex_only) * 100.0, 2),
        "surface_delta_pp_vs_base": round((mean_surf - mean_base) * 100.0, 2),
        "proceed_hook": mean_surf > mean_lex_only + 0.02,
        "rows_sample": rows[:12],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Logos verse surface reconstruct hypo v1")
    ap.add_argument("--cases-json", type=Path, required=True, help="Lane JSON with compression_cases")
    ap.add_argument("--cap", type=int, default=30)
    ap.add_argument("--lexicon", type=Path, default=DEFAULT_LEX)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--wire-gloss",
        choices=("none", "global", "per_case"),
        default="none",
        help="B-track wire gloss hook: global lexicon-filtered atoms or per-case graph wire map",
    )
    ap.add_argument("--aligned-poc", type=Path, default=DEFAULT_ALIGNED_POC)
    args = ap.parse_args()

    lane = json.loads(args.cases_json.read_text(encoding="utf-8"))
    cases = list(lane.get("compression_cases") or [])[: max(0, args.cap)]

    if args.wire_gloss == "none":
        doc = run_batch(cases, args.lexicon.resolve())
    else:
        import scripts.mkm_graph_wire_bridge_influence_v1 as wire

        orig_poc = wire.POC
        try:
            if args.aligned_poc.is_file():
                wire.POC = args.aligned_poc.resolve()
            wire_ids = wire.wire_atom_ids_lexicon_filtered(anchor_max=12, lexicon_path=args.lexicon)
            influence_map = None
            if args.wire_gloss == "per_case":
                influence_map = wire.build_influence_map_from_compression_cases(
                    cases, wire_atom_ids=wire_ids
                )
            doc = run_batch_wire_gloss(
                cases,
                args.lexicon.resolve(),
                wire_atom_ids=wire_ids,
                influence_map=influence_map,
            )
            doc["wire_gloss_mode"] = args.wire_gloss
            doc["aligned_poc"] = str(args.aligned_poc).replace("\\", "/")
        finally:
            wire.POC = orig_poc
    doc["generated_at_utc"] = __import__("datetime").datetime.now(
        __import__("datetime").timezone.utc
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out_json), "summary": {
        "mean_jaccard_surface": doc.get("mean_jaccard_surface"),
        "surface_delta_pp": doc.get("surface_delta_pp"),
        "proceed_hook": doc.get("proceed_hook"),
    }}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
