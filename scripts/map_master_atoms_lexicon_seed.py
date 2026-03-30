#!/usr/bin/env python3
"""Map original-language master atoms to Strong numbers using local OpenScriptures data.

Reads master atoms JSONL and Strong Greek/Hebrew XML under vault/external_lexicon (or overrides).
Uses the same token normalization as build_original_language_master_atoms._normalize_token.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.build_original_language_master_atoms import _normalize_token  # noqa: E402

NS = "{http://www.bibletechnologies.net/2003/OSIS/namespace}"

DEFAULT_LEX_ROOT = ROOT / "vault" / "external_lexicon" / "sources" / "openscriptures-strongs"
DEFAULT_ATOMS = ROOT / "reports" / "constitution" / "btrack_pilot" / "original_language_master_atoms_latest.jsonl"
OUT_DIR = ROOT / "reports" / "constitution" / "btrack_pilot"


def _default_paths(lex_root: Path) -> tuple[Path, Path]:
    greek = (
        lex_root
        / "greek"
        / "StrongsGreekDictionaryXML_1.4"
        / "strongsgreek.xml"
    )
    hebrew = lex_root / "hebrew" / "StrongHebrewG.xml"
    return greek, hebrew


def _add_key_ref(mapping: dict[str, list[str]], key: str, ref: str) -> None:
    if not key:
        return
    bucket = mapping.setdefault(key, [])
    if ref not in bucket:
        bucket.append(ref)


def load_strongs_greek(path: Path) -> dict[str, list[str]]:
    """normalized Greek form -> ['G####', ...] (first <greek unicode= per entry)."""
    tree = ET.parse(path)
    root = tree.getroot()
    # Body is under <entries> after prologue; iterate all entries.
    out: dict[str, list[str]] = {}
    for entry in root.iter("entry"):
        sid = entry.get("strongs")
        if not sid:
            continue
        try:
            n = int(sid, 10)
        except ValueError:
            continue
        gref = f"G{n}"
        greek_el = None
        for child in entry.iter("greek"):
            u = child.get("unicode")
            if u:
                greek_el = u
                break
        if not greek_el:
            continue
        key = _normalize_token(greek_el)
        if not key:
            continue
        _add_key_ref(out, key, gref)
    return out


def load_strongs_hebrew(path: Path) -> dict[str, list[str]]:
    """normalized Hebrew form -> ['H###', ...] from entry headline <w ID=\"Hn\" ...>."""
    tree = ET.parse(path)
    root = tree.getroot()
    out: dict[str, list[str]] = {}
    for w in root.iter(f"{NS}w"):
        wid = w.get("ID")
        if not wid or not re.fullmatch(r"H[0-9]+", wid):
            continue
        lemma = (w.get("lemma") or "").strip()
        text = (w.text or "").strip()
        for raw in (lemma, text):
            if not raw:
                continue
            key = _normalize_token(raw)
            if not key:
                continue
            _add_key_ref(out, key, wid)
    return out


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                yield obj


def main() -> int:
    ap = argparse.ArgumentParser(description="Map master atoms to Strong numbers (seed).")
    ap.add_argument("--atoms", type=Path, default=DEFAULT_ATOMS)
    ap.add_argument("--strongs-root", type=Path, default=DEFAULT_LEX_ROOT)
    ap.add_argument("--greek-xml", type=Path, default=None)
    ap.add_argument("--hebrew-xml", type=Path, default=None)
    ap.add_argument("--out-jsonl", type=Path, default=None)
    ap.add_argument("--out-summary", type=Path, default=None)
    ap.add_argument(
        "--write-latest",
        action="store_true",
        help="Also copy outputs to master_atoms_lexicon_seed_latest.jsonl / _summary_latest.json",
    )
    args = ap.parse_args()

    greek_p, hebrew_p = _default_paths(Path(args.strongs_root))
    if args.greek_xml:
        greek_p = Path(args.greek_xml)
    if args.hebrew_xml:
        hebrew_p = Path(args.hebrew_xml)

    atoms_path = Path(args.atoms)
    for label, p in ("Greek Strong XML", greek_p), ("Hebrew Strong XML", hebrew_p), ("atoms", atoms_path):
        if not p.is_file():
            print(f"ERROR: missing {label}: {p}")
            return 2

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_jsonl = args.out_jsonl or (OUT_DIR / f"master_atoms_lexicon_seed_{ts}.jsonl")
    out_summary = args.out_summary or (OUT_DIR / f"master_atoms_lexicon_seed_summary_{ts}.json")
    out_jsonl = Path(out_jsonl)
    out_summary = Path(out_summary)
    if not out_jsonl.is_absolute():
        out_jsonl = ROOT / out_jsonl
    if not out_summary.is_absolute():
        out_summary = ROOT / out_summary
    out_jsonl.parent.mkdir(parents=True, exist_ok=True)

    greek_map = load_strongs_greek(greek_p)
    hebrew_map = load_strongs_hebrew(hebrew_p)

    stats = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "atoms": str(atoms_path),
            "strongs_greek_xml": str(greek_p),
            "strongs_hebrew_xml": str(hebrew_p),
        },
        "strongs_index_sizes": {
            "greek_keys": len(greek_map),
            "hebrew_keys": len(hebrew_map),
        },
        "atoms_total": 0,
        "greek_atoms": 0,
        "hebrew_atoms": 0,
        "matched_greek": 0,
        "matched_hebrew": 0,
        "ambiguous_greek": 0,
        "ambiguous_hebrew": 0,
        "unmatched_greek": 0,
        "unmatched_hebrew": 0,
    }

    with out_jsonl.open("w", encoding="utf-8") as out_f:
        for row in _iter_jsonl(atoms_path):
            stats["atoms_total"] += 1
            lang = str(row.get("lang") or "")
            norm = str(row.get("normalized_form") or "")
            if lang == "greek":
                stats["greek_atoms"] += 1
                refs = greek_map.get(norm, [])
            elif lang == "hebrew":
                stats["hebrew_atoms"] += 1
                refs = hebrew_map.get(norm, [])
            else:
                refs = []

            if lang == "greek":
                if not refs:
                    stats["unmatched_greek"] += 1
                    method = "unmatched"
                elif len(refs) > 1:
                    stats["ambiguous_greek"] += 1
                    stats["matched_greek"] += 1
                    method = "strongs_norm_multi"
                else:
                    stats["matched_greek"] += 1
                    method = "strongs_norm"
            elif lang == "hebrew":
                if not refs:
                    stats["unmatched_hebrew"] += 1
                    method = "unmatched"
                elif len(refs) > 1:
                    stats["ambiguous_hebrew"] += 1
                    stats["matched_hebrew"] += 1
                    method = "strongs_norm_multi"
                else:
                    stats["matched_hebrew"] += 1
                    method = "strongs_norm"
            else:
                method = "skipped_lang"

            out_row: dict[str, Any] = {
                "atom_id": row.get("atom_id"),
                "lang": lang,
                "normalized_form": norm,
                "strongs_candidates": refs,
                "match_method": method,
            }
            out_f.write(json.dumps(out_row, ensure_ascii=False) + "\n")

    ga, ha = stats["greek_atoms"], stats["hebrew_atoms"]
    stats["coverage"] = {
        "greek": {
            "matched_any_of_one_or_more_candidates": stats["matched_greek"],
            "unmatched": stats["unmatched_greek"],
            "ambiguous_keys": stats["ambiguous_greek"],
            "fraction_of_greek_atoms": round(
                (stats["matched_greek"] / ga) if ga else 0.0,
                6,
            ),
        },
        "hebrew": {
            "matched_any_of_one_or_more_candidates": stats["matched_hebrew"],
            "unmatched": stats["unmatched_hebrew"],
            "ambiguous_keys": stats["ambiguous_hebrew"],
            "fraction_of_hebrew_atoms": round(
                (stats["matched_hebrew"] / ha) if ha else 0.0,
                6,
            ),
        },
    }

    out_summary.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.write_latest:
        latest_jsonl = OUT_DIR / "master_atoms_lexicon_seed_latest.jsonl"
        latest_summary = OUT_DIR / "master_atoms_lexicon_seed_summary_latest.json"
        latest_jsonl.write_bytes(out_jsonl.read_bytes())
        latest_summary.write_bytes(out_summary.read_bytes())
        stats["latest_alias"] = {
            "jsonl": str(latest_jsonl),
            "summary": str(latest_summary),
        }
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
