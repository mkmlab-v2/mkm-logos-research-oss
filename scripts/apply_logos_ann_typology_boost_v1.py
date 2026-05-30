#!/usr/bin/env python3
"""Apply typology lexicon boost to logos_vector_ann_lite_query_result_v1 (CPU-only).

Re-ranks top_k by injecting/boosting verse scores from B-track typology lexicon.
Does not re-run sentence-transformers or touch GPU/Nemotron paths.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEXICON = ROOT / "docs/final/fixtures/logos_ann_typology_lexicon_v1.json"
ARTIFACT_SCHEMA = "logos_vector_ann_lite_query_result_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def normalize_verse_ref(raw: str) -> str:
    s = str(raw or "").strip()
    if not s:
        return ""
    if "::" in s:
        s = s.split("::", 1)[1]
    m = re.match(r"^([A-Za-z0-9]+)\.(\d+)\.(\d+)$", s)
    if m:
        return s
    return s


def _keyword_hits(query: str, keywords: list[str]) -> int:
    q = query.lower()
    hits = 0
    for kw in keywords:
        k = str(kw or "").strip().lower()
        if k and k in q:
            hits += 1
    return hits


def match_lexicon_entries(
    *,
    query: str,
    query_id: str | None,
    lexicon: dict[str, Any],
) -> list[dict[str, Any]]:
    matched: list[dict[str, Any]] = []
    for entry in lexicon.get("entries") or []:
        if not isinstance(entry, dict):
            continue
        qids = [str(x) for x in (entry.get("query_ids") or [])]
        if query_id and qids and query_id not in qids:
            continue
        kws = list(entry.get("query_keywords_ko") or []) + list(entry.get("query_keywords_en") or [])
        min_hits = int(entry.get("keyword_hit_min") or 1)
        if qids and query_id in qids:
            matched.append(entry)
            continue
        if _keyword_hits(query, kws) >= min_hits:
            matched.append(entry)
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for e in matched:
        tid = str(e.get("theme_id") or "")
        if tid in seen:
            continue
        seen.add(tid)
        deduped.append(e)
    return deduped


def apply_typology_boost(
    ann_doc: dict[str, Any],
    *,
    query: str,
    query_id: str | None,
    lexicon: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if ann_doc.get("schema") != ARTIFACT_SCHEMA:
        raise ValueError(f"expected schema {ARTIFACT_SCHEMA}")

    entries = match_lexicon_entries(query=query, query_id=query_id, lexicon=lexicon)
    default_delta = float(lexicon.get("default_boost_delta") or 0.15)

    raw_top = ann_doc.get("top_k") or []
    scores: dict[str, float] = {}
    for row in raw_top:
        if not isinstance(row, dict):
            continue
        vid = normalize_verse_ref(str(row.get("verse_id") or ""))
        if vid:
            scores[vid] = float(row.get("score") or 0.0)

    original_k = int(ann_doc.get("top_k_requested") or 0)
    if original_k < 1:
        original_k = max(len(raw_top), 8)

    base_score = max(scores.values()) if scores else 0.35
    injected: list[str] = []
    themes: list[str] = []

    for entry in entries:
        theme = str(entry.get("theme_id") or "")
        if theme:
            themes.append(theme)
        delta = float(entry.get("boost_delta") or default_delta)
        for raw_vid in entry.get("boost_verse_ids") or []:
            vid = normalize_verse_ref(str(raw_vid))
            if not vid:
                continue
            new_score = max(scores.get(vid, 0.0), base_score + delta)
            if vid not in scores or new_score > scores[vid]:
                if vid not in scores:
                    injected.append(vid)
                scores[vid] = new_score

    ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
    top_k = [{"verse_id": vid, "score": round(score, 9)} for vid, score in ranked[:original_k]]

    meta = {
        "applied": bool(entries),
        "applied_at_utc": _utc_now(),
        "lexicon_path": None,
        "themes_matched": themes,
        "entries_matched": len(entries),
        "injected_verse_ids": injected,
        "boost_method": "typology_lexicon_score_floor_v1",
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
    }

    out = dict(ann_doc)
    out["top_k"] = top_k
    out["typology_boost"] = meta
    note = str(out.get("notes") or "")
    if entries:
        suffix = " typology_boost applied (CPU lexicon; not semantic re-encode)."
        if suffix.strip() not in note:
            out["notes"] = (note + suffix).strip()
    return out, meta


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ann-query-json", type=Path, required=True)
    ap.add_argument("--query", type=str, default=None, help="Override query text (else infer from query_seed).")
    ap.add_argument("--query-id", type=str, default=None)
    ap.add_argument("--lexicon-json", type=Path, default=DEFAULT_LEXICON)
    ap.add_argument(
        "--out-json",
        type=Path,
        default=None,
        help="Output path (default: overwrite --ann-query-json).",
    )
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    ann_path = args.ann_query_json if args.ann_query_json.is_absolute() else ROOT / args.ann_query_json
    lex_path = args.lexicon_json if args.lexicon_json.is_absolute() else ROOT / args.lexicon_json
    out_path = args.out_json if args.out_json else ann_path
    if out_path and not out_path.is_absolute():
        out_path = ROOT / out_path

    ann_doc = _read_json(ann_path)
    lexicon = _read_json(lex_path)
    if not ann_doc:
        print(f"[ERROR] missing or invalid ann doc: {ann_path}", file=sys.stderr)
        return 2
    if lexicon.get("schema") != "logos_ann_typology_lexicon_v1":
        print(f"[ERROR] invalid lexicon schema: {lex_path}", file=sys.stderr)
        return 2

    query = args.query
    if not query:
        seed = str(ann_doc.get("query_seed") or "")
        if seed.startswith("st_query:"):
            query = seed[len("st_query:") :]
        elif seed.startswith(QUERY_SEED_PREFIX := "query_v1|"):
            query = seed[len(QUERY_SEED_PREFIX) :]
        else:
            query = seed

    try:
        boosted, meta = apply_typology_boost(
            ann_doc,
            query=query or "",
            query_id=args.query_id,
            lexicon=lexicon,
        )
    except ValueError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 2

    meta["lexicon_path"] = str(lex_path.relative_to(ROOT)).replace("\\", "/") if lex_path.is_relative_to(ROOT) else str(lex_path)
    boosted["typology_boost"] = meta

    summary = {
        "ok": True,
        "ann_path": str(ann_path),
        "themes_matched": meta.get("themes_matched"),
        "injected_count": len(meta.get("injected_verse_ids") or []),
        "top1": (boosted.get("top_k") or [{}])[0],
    }
    print(json.dumps(summary, ensure_ascii=False))

    if args.dry_run:
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(boosted, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
