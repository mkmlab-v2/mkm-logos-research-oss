#!/usr/bin/env python3
"""Build original-language master atoms (v1, normalization-based)."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
IN_VERSE = ROOT / "data" / "logos" / "verse_decoded_v2.jsonl"
IN_APO = ROOT / "data" / "logos" / "manuscripts" / "apocrypha_std.jsonl"
IN_DSS = ROOT / "data" / "logos" / "manuscripts" / "dss_parsed_enriched.jsonl"
OUT_JSONL = ROOT / "reports" / "constitution" / "btrack_pilot" / "original_language_master_atoms_latest.jsonl"
OUT_SUMMARY = ROOT / "reports" / "constitution" / "btrack_pilot" / "original_language_master_atoms_summary_latest.json"

TOK_RE = re.compile(r"[A-Za-z]+|[\u0370-\u03FF\u1F00-\u1FFF]+|[\u0590-\u05FF]+")


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                yield obj


def _strip_hebrew_marks(text: str) -> str:
    # Remove niqqud/cantillation to normalize to consonantal form.
    return "".join(ch for ch in unicodedata.normalize("NFKD", text) if not (0x0591 <= ord(ch) <= 0x05C7))


def _normalize_token(tok: str) -> str:
    t = tok.strip().lower()
    if not t:
        return ""
    if re.fullmatch(r"[\u0590-\u05FF]+", t):
        return _strip_hebrew_marks(t)
    if re.fullmatch(r"[\u0370-\u03FF\u1F00-\u1FFF]+", t):
        # Greek diacritics folded.
        t = "".join(ch for ch in unicodedata.normalize("NFKD", t) if not unicodedata.combining(ch))
        return t
    return t


def _heuristic_hebrew_lemma(tok: str) -> str:
    # Lightweight stemming for Hebrew surface normalization (not full morphology).
    t = tok
    # Remove common single-letter prefixes once.
    if len(t) >= 4 and t[0] in {"ו", "ב", "כ", "ל", "מ", "ה", "ש"}:
        t = t[1:]
    # Reduce common plural endings.
    if len(t) >= 5 and t.endswith("ים"):
        t = t[:-2]
    elif len(t) >= 5 and t.endswith("ות"):
        t = t[:-2]
    return t


def _to_atom_form(tok: str, lemma_mode: str) -> str:
    if lemma_mode == "heuristic_lemma_v2" and _lang_of(tok) == "hebrew":
        return _heuristic_hebrew_lemma(tok)
    return tok


def _lang_of(tok: str) -> str:
    if re.fullmatch(r"[\u0590-\u05FF]+", tok):
        return "hebrew"
    if re.fullmatch(r"[\u0370-\u03FF\u1F00-\u1FFF]+", tok):
        return "greek"
    return "other"


def _collect_text_fields(row: dict[str, Any]) -> list[str]:
    out = []
    for k in ("original_text", "text_hebrew", "text_greek", "text"):
        v = row.get(k)
        if isinstance(v, str) and v.strip():
            out.append(v)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Build original-language master atoms (v1)")
    ap.add_argument("--verse-jsonl", default=str(IN_VERSE))
    ap.add_argument("--apo-jsonl", default=str(IN_APO))
    ap.add_argument("--dss-jsonl", default=str(IN_DSS))
    ap.add_argument("--out-jsonl", default=str(OUT_JSONL))
    ap.add_argument("--out-summary", default=str(OUT_SUMMARY))
    ap.add_argument(
        "--lemma-mode",
        choices=("normalized_form_v1", "heuristic_lemma_v2"),
        default="normalized_form_v1",
        help="Token-to-atom normalization mode.",
    )
    args = ap.parse_args()

    inputs = [Path(args.verse_jsonl), Path(args.apo_jsonl), Path(args.dss_jsonl)]
    inputs = [p if p.is_absolute() else ROOT / p for p in inputs]
    out_jsonl = Path(args.out_jsonl)
    out_summary = Path(args.out_summary)
    if not out_jsonl.is_absolute():
        out_jsonl = ROOT / out_jsonl
    if not out_summary.is_absolute():
        out_summary = ROOT / out_summary

    for p in inputs:
        if not p.is_file():
            print(f"ERROR: missing file: {p}")
            return 2

    atoms: dict[str, dict[str, Any]] = {}
    surface_count = 0
    for src_path in inputs:
        src_name = src_path.name
        for row in _iter_jsonl(src_path):
            text_fields = _collect_text_fields(row)
            verse_id = str(row.get("verse_id", "") or row.get("id", "") or "")
            for text in text_fields:
                for m in TOK_RE.finditer(text):
                    surface = m.group(0)
                    norm = _normalize_token(surface)
                    if not norm:
                        continue
                    atom_form = _to_atom_form(norm, args.lemma_mode)
                    if not atom_form:
                        continue
                    surface_count += 1
                    key = f"{_lang_of(atom_form)}::{atom_form}"
                    entry = atoms.get(key)
                    if entry is None:
                        atoms[key] = {
                            "atom_id": key,
                            "lang": _lang_of(atom_form),
                            "normalized_form": atom_form,
                            "surface_forms": {surface},
                            "source_files": {src_name},
                            "source_refs": {verse_id} if verse_id else set(),
                            "occurrences": 1,
                            "lemma_method": args.lemma_mode,
                        }
                    else:
                        entry["surface_forms"].add(surface)
                        entry["source_files"].add(src_name)
                        if verse_id:
                            entry["source_refs"].add(verse_id)
                        entry["occurrences"] += 1

    out_rows = []
    for v in atoms.values():
        out_rows.append(
            {
                "atom_id": v["atom_id"],
                "lang": v["lang"],
                "normalized_form": v["normalized_form"],
                "surface_form_count": len(v["surface_forms"]),
                "sample_surface_forms": sorted(v["surface_forms"])[:5],
                "source_file_count": len(v["source_files"]),
                "source_files": sorted(v["source_files"]),
                "source_ref_count": len(v["source_refs"]),
                "occurrences": int(v["occurrences"]),
                "lemma_method": v["lemma_method"],
            }
        )
    out_rows.sort(key=lambda x: (x["lang"], -x["occurrences"], x["normalized_form"]))

    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with out_jsonl.open("w", encoding="utf-8") as f:
        for r in out_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    by_lang: dict[str, int] = {}
    for r in out_rows:
        by_lang[r["lang"]] = by_lang.get(r["lang"], 0) + 1
    summary = {
        "schema": "original_language_master_atoms_summary_v1",
        "generated_at_utc": ts,
        "inputs": [str(p) for p in inputs],
        "stats": {
            "surface_token_count": surface_count,
            "unique_master_atoms": len(out_rows),
            "unique_atoms_by_lang": by_lang,
            "lemma_method": args.lemma_mode,
            "note": "Pseudo-lemma mode (v1 normalized or v2 heuristic); not full morphology lemmatization.",
        },
        "output_jsonl": str(out_jsonl),
    }
    out_summary.parent.mkdir(parents=True, exist_ok=True)
    out_summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("OK: original language master atoms built")
    print(f"out={out_jsonl}")
    print(f"summary={out_summary}")
    print(f"unique_atoms={len(out_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
