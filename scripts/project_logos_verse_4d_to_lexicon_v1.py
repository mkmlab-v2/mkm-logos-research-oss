#!/usr/bin/env python3
"""Project logos_verse_4d_v1 rows onto master codebook atoms (Track B Phase 3).

Joins verse original-script tokens (Hebrew/Greek) to master_codebook_lexicon_v1
entries and writes per-verse atom_overlay plus optional lexicon_4d_v1 aggregates.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.build_original_language_master_atoms import (  # noqa: E402
    TOK_RE,
    _normalize_token,
)
from scripts.core.master_codebook_lexicon_v1_bridge import (  # noqa: E402
    resolve_latest_codebook_path,
)

OVERLAY_RECIPE_ID = "project_logos_verse_4d_to_lexicon_v1"
_AXES = ("S", "L", "K", "M")
_TRACK_WALL = {
    "a_track_auto_promotion": False,
    "live_trading_trigger": False,
    "ready_for_external_send": False,
}

DEFAULT_VERSE_JSONL = ROOT / "reports" / "constitution" / "btrack_pilot" / "logos_verse_4d_v1_latest.jsonl"
DEFAULT_OUT_JSONL = ROOT / "reports" / "constitution" / "btrack_pilot" / "logos_verse_4d_v1_with_atoms_latest.jsonl"
DEFAULT_OUT_LEXICON = ROOT / "reports" / "constitution" / "btrack_pilot" / "lexicon_4d_v1_latest.json"
MAX_TOP_ATOMS = 32


def _iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                yield obj


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve_path(p: Path) -> Path:
    return p if p.is_absolute() else ROOT / p


def load_form_to_entry(codebook_path: Path) -> dict[str, dict[str, Any]]:
    doc = json.loads(codebook_path.read_text(encoding="utf-8"))
    if doc.get("schema") != "master_codebook_lexicon_v1":
        raise ValueError(f"unexpected codebook schema: {doc.get('schema')!r}")
    out: dict[str, dict[str, Any]] = {}
    for ent in doc.get("entries") or []:
        if not isinstance(ent, dict):
            continue
        nf = ent.get("normalized_form")
        aid = ent.get("atom_id")
        if not isinstance(nf, str) or not nf.strip() or not isinstance(aid, str) or not aid:
            continue
        key = nf.strip().lower()
        prev = out.get(key)
        if prev is None or int(ent.get("occurrences") or 0) >= int(prev.get("occurrences") or 0):
            out[key] = ent
    return out


def token_atom_counts(text: str, form_to_entry: dict[str, dict[str, Any]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for m in TOK_RE.finditer(text):
        norm = _normalize_token(m.group(0))
        if not norm:
            continue
        ent = form_to_entry.get(norm.lower())
        if ent is None:
            continue
        aid = str(ent["atom_id"])
        counts[aid] += 1
    return counts


def build_top_atoms(
    counts: Counter[str],
    form_to_entry: dict[str, dict[str, Any]],
    *,
    entry_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    if not counts:
        return []
    total = sum(counts.values())
    ranked = counts.most_common(MAX_TOP_ATOMS)
    top: list[dict[str, Any]] = []
    for aid, cnt in ranked:
        ent = entry_by_id.get(aid)
        if ent is None:
            continue
        nf = ent.get("normalized_form")
        top.append(
            {
                "atom_id": aid,
                "normalized_form": str(nf) if nf is not None else "",
                "weight": round(cnt / total, 8),
            }
        )
    return top


def _vector_4d(row: dict[str, Any]) -> dict[str, float] | None:
    v = row.get("vector_4d")
    if not isinstance(v, dict):
        return None
    try:
        return {k: float(v[k]) for k in _AXES}
    except (KeyError, TypeError, ValueError):
        return None


def _entry_by_atom_id(form_to_entry: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for ent in form_to_entry.values():
        aid = ent.get("atom_id")
        if isinstance(aid, str) and aid:
            by_id[aid] = ent
    return by_id


class _LexiconAcc:
    __slots__ = ("sum_vec", "token_weight", "verse_ids")

    def __init__(self) -> None:
        self.sum_vec = {k: 0.0 for k in _AXES}
        self.token_weight = 0.0
        self.verse_ids: set[str] = set()


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Project logos_verse_4d_v1 onto master codebook lexicon (Track B)"
    )
    ap.add_argument("--verse-jsonl", type=Path, default=DEFAULT_VERSE_JSONL)
    ap.add_argument(
        "--codebook-json",
        type=Path,
        default=None,
        help="master_codebook_lexicon_v1 JSON; default: highest row-count *_rows_latest.json",
    )
    ap.add_argument("--max-rows", type=int, default=0, help="0 = all verses")
    ap.add_argument(
        "--min-verse-count-for-lexicon",
        type=int,
        default=2,
        help="Minimum distinct verses for lexicon_4d_v1 row emission",
    )
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_OUT_JSONL)
    ap.add_argument(
        "--out-lexicon-4d-json",
        type=Path,
        default=DEFAULT_OUT_LEXICON,
        help="Write lexicon_4d_v1 aggregate JSON (omit path to skip)",
    )
    ap.add_argument(
        "--skip-lexicon-4d",
        action="store_true",
        help="Do not write lexicon_4d aggregate file",
    )
    ap.add_argument(
        "--filter-atom-id",
        default="",
        help="DF-P2-01: emit only verses where this codebook atom_id has token hits",
    )
    args = ap.parse_args()

    verse_path = _resolve_path(Path(args.verse_jsonl))
    if not verse_path.is_file():
        print(f"ERROR: missing verse jsonl: {verse_path}", flush=True)
        return 2

    codebook_path: Path | None
    if args.codebook_json is not None:
        codebook_path = _resolve_path(Path(args.codebook_json))
        if not codebook_path.is_file():
            print(f"ERROR: missing codebook json: {codebook_path}", flush=True)
            return 2
    else:
        codebook_path = resolve_latest_codebook_path()
        if codebook_path is None:
            print(
                "ERROR: no master_codebook_lexicon_v1_*_rows_latest.json under "
                "reports/constitution/btrack_pilot/ — run export_master_codebook_v1.py "
                "or pass --codebook-json",
                flush=True,
            )
            return 2

    form_to_entry = load_form_to_entry(codebook_path)
    entry_by_id = _entry_by_atom_id(form_to_entry)
    if not form_to_entry:
        print(f"ERROR: codebook has no normalized_form entries: {codebook_path}", flush=True)
        return 2

    out_jsonl = _resolve_path(Path(args.out_jsonl))
    out_jsonl.parent.mkdir(parents=True, exist_ok=True)

    lexicon_acc: dict[str, _LexiconAcc] = defaultdict(_LexiconAcc)
    verses_processed = 0
    verses_with_match = 0
    total_tokens = 0
    matched_tokens = 0

    with out_jsonl.open("w", encoding="utf-8") as out_f:
        for row in _iter_jsonl(verse_path):
            if args.max_rows and verses_processed >= args.max_rows:
                break
            if row.get("schema") != "logos_verse_4d_v1":
                continue

            text_span = row.get("text_span") or {}
            text = ""
            if isinstance(text_span, dict):
                raw = text_span.get("original_script_text")
                if isinstance(raw, str):
                    text = raw

            counts = token_atom_counts(text, form_to_entry)
            if args.filter_atom_id and int(counts.get(args.filter_atom_id) or 0) < 1:
                verses_processed += 1
                continue
            tok_total = sum(
                1 for m in TOK_RE.finditer(text) if _normalize_token(m.group(0))
            )
            match_total = sum(counts.values())
            total_tokens += tok_total
            matched_tokens += match_total
            if match_total > 0:
                verses_with_match += 1

            enriched = dict(row)
            enriched["atom_overlay"] = {
                "top_atoms": build_top_atoms(counts, form_to_entry, entry_by_id=entry_by_id),
                "overlay_recipe_id": OVERLAY_RECIPE_ID,
            }
            out_f.write(json.dumps(enriched, ensure_ascii=False) + "\n")

            vec = _vector_4d(row)
            vid = str(row.get("verse_id") or "")
            if vec is not None and counts and vid:
                for aid, cnt in counts.items():
                    acc = lexicon_acc[aid]
                    acc.verse_ids.add(vid)
                    w = float(cnt)
                    acc.token_weight += w
                    for k in _AXES:
                        acc.sum_vec[k] += vec[k] * w

            verses_processed += 1

    match_rate = (matched_tokens / total_tokens) if total_tokens else 0.0
    verse_match_rate = (verses_with_match / verses_processed) if verses_processed else 0.0

    lexicon_rows: list[dict[str, Any]] = []
    min_vc = max(1, int(args.min_verse_count_for_lexicon))
    for aid, acc in lexicon_acc.items():
        if len(acc.verse_ids) < min_vc or acc.token_weight <= 0:
            continue
        ent = entry_by_id.get(aid, {})
        lexicon_rows.append(
            {
                "atom_id": aid,
                "normalized_form": str(ent.get("normalized_form") or ""),
                "lang": str(ent.get("lang") or ""),
                "vector_4d": {
                    k: round(acc.sum_vec[k] / acc.token_weight, 8) for k in _AXES
                },
                "verse_count": len(acc.verse_ids),
                "token_occurrences": int(round(acc.token_weight)),
            }
        )
    lexicon_rows.sort(key=lambda r: (-r["verse_count"], -r["token_occurrences"], r["atom_id"]))

    stats = {
        "verses_processed": verses_processed,
        "verses_with_atom_match": verses_with_match,
        "verse_atom_match_rate": round(verse_match_rate, 6),
        "script_tokens": total_tokens,
        "matched_tokens": matched_tokens,
        "token_match_rate": round(match_rate, 6),
        "codebook_forms": len(form_to_entry),
        "lexicon_4d_rows": len(lexicon_rows),
    }

    out_lexicon_path: str | None = None
    if not args.skip_lexicon_4d and args.out_lexicon_4d_json:
        lex_path = _resolve_path(Path(args.out_lexicon_4d_json))
        lex_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": "lexicon_4d_v1",
            "version": "1.0.0",
            "generated_at_utc": _utc_now(),
            "min_verse_count": min_vc,
            "inputs": {
                "verse_jsonl": str(verse_path.resolve()),
                "codebook_json": str(codebook_path.resolve()),
                "overlay_recipe_id": OVERLAY_RECIPE_ID,
            },
            "rows": lexicon_rows,
            "stats": stats,
            "hypothesis_tier": "B",
            "boundary_ack": True,
            "track_wall": dict(_TRACK_WALL),
        }
        lex_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        out_lexicon_path = str(lex_path)

    summary = {
        "ok": True,
        "out_jsonl": str(out_jsonl),
        "out_lexicon_4d_json": out_lexicon_path,
        "codebook_json": str(codebook_path.resolve()),
        "stats": stats,
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
