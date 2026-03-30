#!/usr/bin/env python3
"""Map Hebrew master atoms to morphhb WLC lemmas (rail_morphhb).

Reads master atoms JSONL + morphhb_norm_to_lemma_index JSON (see build_morphhb_form_to_lemma_index).
Greek/other languages: skipped_lang with empty morphhb_candidates.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_ATOMS = ROOT / "reports" / "constitution" / "btrack_pilot" / "original_language_master_atoms_latest.jsonl"
DEFAULT_INDEX = ROOT / "reports" / "constitution" / "btrack_pilot" / "morphhb_norm_to_lemma_index_latest.json"
OUT_DIR = ROOT / "reports" / "constitution" / "btrack_pilot"


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                yield obj


def _classify_morphhb(candidates: list[dict[str, Any]]) -> tuple[str, list[str]]:
    """Return (match_method, merged_strongs_hints order-stable unique)."""
    if not candidates:
        return "morphhb_unmatched", []
    hint_sets = [tuple(x.get("strongs_hints") or []) for x in candidates]
    flat: list[str] = []
    for hs in hint_sets:
        for h in hs:
            if h not in flat:
                flat.append(h)
    uniq_sets = {tuple(x.get("strongs_hints") or []) for x in candidates}
    if len(uniq_sets) == 1 and flat:
        return "morphhb_wlc", flat
    if len(uniq_sets) == 1 and not flat:
        return "morphhb_wlc_no_strong", []
    if len(uniq_sets) > 1:
        return "morphhb_wlc_multi", flat
    return "morphhb_wlc", flat


def main() -> int:
    ap = argparse.ArgumentParser(description="Map Hebrew atoms to morphhb WLC index (rail_morphhb)")
    ap.add_argument("--atoms", type=Path, default=DEFAULT_ATOMS)
    ap.add_argument("--index-json", type=Path, default=DEFAULT_INDEX)
    ap.add_argument("--out-jsonl", type=Path, default=None)
    ap.add_argument("--out-summary", type=Path, default=None)
    ap.add_argument(
        "--write-latest",
        action="store_true",
        help="Copy to master_atoms_morphhb_seed_latest.jsonl / _summary_latest.json",
    )
    args = ap.parse_args()

    atoms_path = Path(args.atoms)
    index_path = Path(args.index_json)
    if not atoms_path.is_file():
        print(f"ERROR: missing atoms: {atoms_path}", flush=True)
        return 2
    if not index_path.is_file():
        print(f"ERROR: missing index (run build_morphhb_form_to_lemma_index.py): {index_path}", flush=True)
        return 2

    raw = json.loads(index_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema") != "morphhb_norm_to_lemma_index_v1":
        print("ERROR: index JSON schema mismatch", flush=True)
        return 2
    index: dict[str, list[dict[str, Any]]] = raw.get("index") or {}

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_jsonl = args.out_jsonl or (OUT_DIR / f"master_atoms_morphhb_seed_{ts}.jsonl")
    out_summary = args.out_summary or (OUT_DIR / f"master_atoms_morphhb_seed_summary_{ts}.json")
    out_jsonl = Path(out_jsonl)
    out_summary = Path(out_summary)
    if not out_jsonl.is_absolute():
        out_jsonl = ROOT / out_jsonl
    if not out_summary.is_absolute():
        out_summary = ROOT / out_summary
    out_jsonl.parent.mkdir(parents=True, exist_ok=True)

    stats: dict[str, Any] = {
        "rail_id": "rail_morphhb",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "atoms": str(atoms_path),
            "morphhb_index": str(index_path),
        },
        "atoms_total": 0,
        "hebrew_atoms": 0,
        "matched_hebrew": 0,
        "unmatched_hebrew": 0,
        "ambiguous_hebrew": 0,
        "no_strong_hint_hebrew": 0,
        "skipped_non_hebrew": 0,
    }

    with out_jsonl.open("w", encoding="utf-8") as out_f:
        for row in _iter_jsonl(atoms_path):
            stats["atoms_total"] += 1
            lang = str(row.get("lang") or "")
            norm = str(row.get("normalized_form") or "")
            morphhb_candidates: list[dict[str, Any]] = []
            method: str
            strongs_from_morphhb: list[str] = []

            if lang != "hebrew":
                stats["skipped_non_hebrew"] += 1
                method = "skipped_lang"
            else:
                stats["hebrew_atoms"] += 1
                morphhb_candidates = list(index.get(norm, []))
                method, strongs_from_morphhb = _classify_morphhb(morphhb_candidates)

                if method == "morphhb_unmatched":
                    stats["unmatched_hebrew"] += 1
                elif method == "morphhb_wlc_multi":
                    stats["ambiguous_hebrew"] += 1
                    stats["matched_hebrew"] += 1
                elif method == "morphhb_wlc_no_strong":
                    stats["no_strong_hint_hebrew"] += 1
                    stats["matched_hebrew"] += 1
                else:
                    stats["matched_hebrew"] += 1

            out_row = {
                "atom_id": row.get("atom_id"),
                "rail_id": "rail_morphhb",
                "lang": lang,
                "normalized_form": norm,
                "morphhb_candidates": morphhb_candidates,
                "morphhb_strongs_hints": strongs_from_morphhb,
                "match_method": method,
            }
            out_f.write(json.dumps(out_row, ensure_ascii=False) + "\n")

    ha = stats["hebrew_atoms"]
    stats["coverage"] = {
        "hebrew": {
            "matched_any_wlc_row": stats["matched_hebrew"],
            "unmatched": stats["unmatched_hebrew"],
            "ambiguous_morphhb": stats["ambiguous_hebrew"],
            "matched_no_strong_digit_in_lemma": stats["no_strong_hint_hebrew"],
            "fraction_of_hebrew_atoms": round(
                (stats["matched_hebrew"] / ha) if ha else 0.0,
                6,
            ),
        }
    }

    out_summary.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.write_latest:
        latest_j = OUT_DIR / "master_atoms_morphhb_seed_latest.jsonl"
        latest_s = OUT_DIR / "master_atoms_morphhb_seed_summary_latest.json"
        latest_j.write_bytes(out_jsonl.read_bytes())
        latest_s.write_bytes(out_summary.read_bytes())
        stats["latest_alias"] = {"jsonl": str(latest_j), "summary": str(latest_s)}
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
