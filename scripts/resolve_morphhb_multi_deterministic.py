#!/usr/bin/env python3
"""Resolve morphhb_wlc_multi rows using Strong-seed intersection, then deterministic sort."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.map_master_atoms_morphhb_seed import _classify_morphhb  # noqa: E402

OUT_DIR = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_MORPHHB = OUT_DIR / "master_atoms_morphhb_seed_latest.jsonl"
DEFAULT_LEXICON = OUT_DIR / "master_atoms_lexicon_seed_latest.jsonl"
DEFAULT_MORPHHB_INDEX = OUT_DIR / "morphhb_norm_to_lemma_index_latest.json"
DEFAULT_ATOMS = OUT_DIR / "original_language_master_atoms_latest.jsonl"


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                yield obj


def _sort_key_hint(c: dict[str, Any]) -> tuple[str, str, tuple[str, ...]]:
    lemma = str(c.get("lemma") or "")
    morph = str(c.get("morph") or "")
    hints = tuple(sorted(c.get("strongs_hints") or []))
    return (lemma, morph, hints)


def _pick_deterministic(
    candidates: list[dict[str, Any]],
    lex_strongs: list[str],
) -> tuple[dict[str, Any], str]:
    """Return (chosen_row, rule_id)."""
    L = {x for x in lex_strongs if isinstance(x, str) and x.startswith("H")}
    with_hit = [
        c
        for c in candidates
        if L & {h for h in (c.get("strongs_hints") or []) if isinstance(h, str)}
    ]
    if len(with_hit) == 1:
        return with_hit[0], "strong_intersection_unique"
    pool = with_hit if with_hit else list(candidates)
    if not pool:
        raise RuntimeError("empty candidate pool")
    chosen = sorted(pool, key=_sort_key_hint)[0]
    if with_hit:
        return chosen, "strong_intersection_lexicographic"
    return chosen, "lexicographic_all_candidates"


def _recount_stats(
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    atoms_total = len(rows)
    hebrew = 0
    unmatched = 0
    ambiguous = 0
    no_strong = 0
    matched = 0
    skipped_non_hebrew = 0
    for row in rows:
        lang = str(row.get("lang") or "")
        method = str(row.get("match_method") or "")
        if lang != "hebrew":
            skipped_non_hebrew += 1
            continue
        hebrew += 1
        if method == "morphhb_unmatched":
            unmatched += 1
        elif method == "morphhb_wlc_multi":
            ambiguous += 1
            matched += 1
        elif method == "morphhb_wlc_no_strong":
            no_strong += 1
            matched += 1
        elif method == "morphhb_wlc":
            matched += 1
    ha = hebrew
    return {
        "rail_id": "rail_morphhb",
        "atoms_total": atoms_total,
        "hebrew_atoms": hebrew,
        "matched_hebrew": matched,
        "unmatched_hebrew": unmatched,
        "ambiguous_hebrew": ambiguous,
        "no_strong_hint_hebrew": no_strong,
        "skipped_non_hebrew": skipped_non_hebrew,
        "coverage": {
            "hebrew": {
                "matched_any_wlc_row": matched,
                "unmatched": unmatched,
                "ambiguous_morphhb": ambiguous,
                "matched_no_strong_digit_in_lemma": no_strong,
                "fraction_of_hebrew_atoms": round((matched / ha) if ha else 0.0, 6),
            }
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Deterministic disambiguation for morphhb_wlc_multi")
    ap.add_argument("--atoms", type=Path, default=DEFAULT_ATOMS, help="Master atoms JSONL (SSOT path echo)")
    ap.add_argument("--morphhb-seed-jsonl", type=Path, default=DEFAULT_MORPHHB)
    ap.add_argument("--lexicon-seed-jsonl", type=Path, default=DEFAULT_LEXICON)
    ap.add_argument(
        "--index-json",
        type=Path,
        default=DEFAULT_MORPHHB_INDEX,
        help="WLC lemma index path (copied into summary inputs for v2 / reproducibility)",
    )
    ap.add_argument("--out-jsonl", type=Path, default=None)
    ap.add_argument("--out-summary", type=Path, default=None)
    ap.add_argument(
        "--write-latest",
        action="store_true",
        help="Overwrite master_atoms_morphhb_seed_latest.jsonl and _summary_latest.json",
    )
    args = ap.parse_args()

    mpath = Path(args.morphhb_seed_jsonl)
    lpath = Path(args.lexicon_seed_jsonl)
    if not mpath.is_file():
        print(f"ERROR: missing morphhb seed: {mpath}", flush=True)
        return 2
    if not lpath.is_file():
        print(f"ERROR: missing lexicon seed: {lpath}", flush=True)
        return 2

    strongs_map: dict[str, list[str]] = {}
    for row in _iter_jsonl(lpath):
        aid = row.get("atom_id")
        if isinstance(aid, str) and aid:
            strongs_map[aid] = list(row.get("strongs_candidates") or [])

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_jsonl = args.out_jsonl or (OUT_DIR / f"master_atoms_morphhb_seed_resolved_{ts}.jsonl")
    out_summary = args.out_summary or (OUT_DIR / f"master_atoms_morphhb_seed_resolved_summary_{ts}.json")
    out_jsonl = Path(out_jsonl)
    out_summary = Path(out_summary)
    if not out_jsonl.is_absolute():
        out_jsonl = ROOT / out_jsonl
    if not out_summary.is_absolute():
        out_summary = ROOT / out_summary

    rule_counts: Counter[str] = Counter()
    resolved_multi = 0
    out_rows: list[dict[str, Any]] = []

    for row in _iter_jsonl(mpath):
        if str(row.get("match_method")) != "morphhb_wlc_multi":
            out_rows.append(row)
            continue
        resolved_multi += 1
        cands: list[dict[str, Any]] = list(row.get("morphhb_candidates") or [])
        aid = row.get("atom_id")
        lex = strongs_map.get(str(aid), []) if aid is not None else []
        chosen, rule = _pick_deterministic(cands, lex)
        rule_counts[rule] += 1
        hints = list(chosen.get("strongs_hints") or [])
        _, merged_flat = _classify_morphhb([chosen])
        out_row = {
            **row,
            "morphhb_candidates": cands,
            "morphhb_chosen": chosen,
            "morphhb_strongs_hints": merged_flat if merged_flat else hints,
            "match_method": "morphhb_wlc",
            "morphhb_disambiguation": {
                "prior_method": "morphhb_wlc_multi",
                "rule": rule,
            },
        }
        out_rows.append(out_row)

    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with out_jsonl.open("w", encoding="utf-8") as out_f:
        for row in out_rows:
            out_f.write(json.dumps(row, ensure_ascii=False) + "\n")

    stats = _recount_stats(out_rows)
    stats["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    atoms_path = Path(args.atoms)
    idx_path = Path(args.index_json)
    stats["inputs"] = {
        "atoms": str(atoms_path.resolve()) if atoms_path.is_file() else None,
        "morphhb_index": str(idx_path.resolve()) if idx_path.is_file() else None,
        "morphhb_seed_in": str(mpath.resolve()),
        "lexicon_seed": str(lpath.resolve()),
    }
    stats["multi_resolution"] = {
        "rows_resolved_from_wlc_multi": resolved_multi,
        "by_rule": dict(rule_counts),
    }
    out_summary.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.write_latest:
        latest_j = OUT_DIR / "master_atoms_morphhb_seed_latest.jsonl"
        latest_s = OUT_DIR / "master_atoms_morphhb_seed_summary_latest.json"
        latest_j.write_bytes(out_jsonl.read_bytes())
        latest_s.write_bytes(out_summary.read_bytes())
        stats["latest_alias"] = {"jsonl": str(latest_j), "summary": str(latest_s)}

    print(json.dumps({"ok": True, "resolved_multi": resolved_multi, "by_rule": dict(rule_counts), "out": str(out_jsonl)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
