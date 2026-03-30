#!/usr/bin/env python3
"""Export Master Codebook V1: atom catalog + Strong seed + MorphHB seed (lexicon rails only)."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_ATOMS = OUT_DIR / "original_language_master_atoms_latest.jsonl"
DEFAULT_LEXICON = OUT_DIR / "master_atoms_lexicon_seed_latest.jsonl"
DEFAULT_MORPHHB = OUT_DIR / "master_atoms_morphhb_seed_latest.jsonl"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                yield obj


def _input_meta(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"path": str(path), "sha256": None, "missing": True}
    return {"path": str(path.resolve()), "sha256": _sha256_file(path)}


def main() -> int:
    ap = argparse.ArgumentParser(description="Export master_codebook_lexicon_v1 JSON")
    ap.add_argument("--atoms-jsonl", type=Path, default=DEFAULT_ATOMS)
    ap.add_argument("--lexicon-seed-jsonl", type=Path, default=DEFAULT_LEXICON)
    ap.add_argument("--morphhb-seed-jsonl", type=Path, default=DEFAULT_MORPHHB)
    ap.add_argument("--out-json", type=Path, default=None)
    args = ap.parse_args()

    atoms_path = Path(args.atoms_jsonl)
    lex_path = Path(args.lexicon_seed_jsonl)
    morph_path = Path(args.morphhb_seed_jsonl)
    for p, label in (
        (atoms_path, "atoms"),
        (lex_path, "lexicon seed"),
        (morph_path, "morphhb seed"),
    ):
        if not p.is_file():
            print(f"ERROR: missing {label}: {p}", flush=True)
            return 2

    lex_by_id: dict[str, dict[str, Any]] = {}
    for row in _iter_jsonl(lex_path):
        aid = row.get("atom_id")
        if isinstance(aid, str) and aid:
            lex_by_id[aid] = row

    morph_by_id: dict[str, dict[str, Any]] = {}
    for row in _iter_jsonl(morph_path):
        aid = row.get("atom_id")
        if isinstance(aid, str) and aid:
            morph_by_id[aid] = row

    entries: list[dict[str, Any]] = []
    for atom in _iter_jsonl(atoms_path):
        aid = atom.get("atom_id")
        if not isinstance(aid, str) or not aid:
            continue
        lang = str(atom.get("lang") or "")
        lex_r = lex_by_id.get(aid, {})
        mo_r = morph_by_id.get(aid, {})
        entry: dict[str, Any] = {
            "atom_id": aid,
            "lang": lang,
            "normalized_form": atom.get("normalized_form"),
            "occurrences": int(atom.get("occurrences") or 0),
            "lexicon_strongs_candidates": list(lex_r.get("strongs_candidates") or []),
            "lexicon_match_method": str(lex_r.get("match_method") or ""),
            "morphhb_match_method": str(mo_r.get("match_method") or ""),
            "morphhb_strongs_hints": list(mo_r.get("morphhb_strongs_hints") or []),
            "morphhb_chosen": mo_r.get("morphhb_chosen"),
            "morphhb_disambiguation": mo_r.get("morphhb_disambiguation"),
        }
        entries.append(entry)

    n = len(entries)
    out_name = f"master_codebook_lexicon_v1_{n}_rows_latest.json"
    out = Path(args.out_json) if args.out_json else (OUT_DIR / out_name)
    if not out.is_absolute():
        out = ROOT / out

    payload: dict[str, Any] = {
        "schema": "master_codebook_lexicon_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "row_count": n,
        "inputs": {
            "atoms": _input_meta(atoms_path),
            "lexicon_seed": _input_meta(lex_path),
            "morphhb_seed": _input_meta(morph_path),
        },
        "rail_coverage_note": (
            "V1 joins original_language_master_atoms with Strong + MorphHB rail seeds per atom_id. "
            "Does not include TBESH audit row-level fields; 14K symbol clustering is out of scope (milestone 1b)."
        ),
        "entries": entries,
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    # Compact JSON: full pretty indentation would inflate ~40k rows beyond practical Git/Vault limits.
    out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out), "row_count": n}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
