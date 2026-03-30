#!/usr/bin/env python3
"""Top-N Canon-only Hebrew atoms where MorphHB rail is morphhb_unmatched (by occurrences)."""

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

from scripts.report_master_atoms_corpus_split import _atom_exclusive_pattern  # noqa: E402

OUT_DIR = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_ATOMS = OUT_DIR / "original_language_master_atoms_latest.jsonl"
DEFAULT_SEED = OUT_DIR / "master_atoms_morphhb_seed_latest.jsonl"
DEFAULT_OUT = OUT_DIR / "canon_unmatched_top100_audit_latest.json"


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
    ap = argparse.ArgumentParser(description="Canon-only MorphHB unmatched top-N by occurrences")
    ap.add_argument("--atoms-jsonl", type=Path, default=DEFAULT_ATOMS)
    ap.add_argument("--morphhb-seed-jsonl", type=Path, default=DEFAULT_SEED)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--top", type=int, default=100)
    args = ap.parse_args()

    atoms_path = Path(args.atoms_jsonl)
    seed_path = Path(args.morphhb_seed_jsonl)
    if not atoms_path.is_file():
        print(f"ERROR: missing atoms: {atoms_path}", flush=True)
        return 2
    if not seed_path.is_file():
        print(f"ERROR: missing morphhb seed: {seed_path}", flush=True)
        return 2

    atoms_by_id: dict[str, dict[str, Any]] = {}
    for row in _iter_jsonl(atoms_path):
        aid = row.get("atom_id")
        if isinstance(aid, str) and aid:
            atoms_by_id[aid] = row

    candidates: list[dict[str, Any]] = []
    for row in _iter_jsonl(seed_path):
        if str(row.get("lang")) != "hebrew":
            continue
        if str(row.get("match_method")) != "morphhb_unmatched":
            continue
        aid = row.get("atom_id")
        atom = atoms_by_id.get(str(aid)) if aid is not None else None
        if not atom:
            continue
        sfiles = atom.get("source_files") or []
        if not isinstance(sfiles, list):
            sfiles = []
        basenames = [str(x) for x in sfiles]
        _b, pattern = _atom_exclusive_pattern(basenames)
        if pattern != "canon_decode_only":
            continue
        occ = int(atom.get("occurrences") or 0)
        candidates.append(
            {
                "atom_id": aid,
                "normalized_form": row.get("normalized_form"),
                "occurrences": occ,
                "source_ref_count": int(atom.get("source_ref_count") or 0),
                "surface_form_count": int(atom.get("surface_form_count") or 0),
                "sample_surface_forms": (atom.get("sample_surface_forms") or [])[:12],
                "exclusive_pattern": pattern,
            }
        )

    candidates.sort(key=lambda x: (-x["occurrences"], str(x.get("normalized_form") or "")))
    top_n = candidates[: max(0, int(args.top))]

    payload: dict[str, Any] = {
        "schema": "canon_unmatched_morphhb_top_audit_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "atoms": str(atoms_path.resolve()),
            "morphhb_seed": str(seed_path.resolve()),
        },
        "filter": {
            "lang": "hebrew",
            "match_method": "morphhb_unmatched",
            "exclusive_pattern": "canon_decode_only",
            "sort_key": "occurrences_desc",
        },
        "canon_unmatched_count": len(candidates),
        "top_n": int(args.top),
        "rows": top_n,
        "note": "Observational sample; causes require manual/blind review (normalization vs rare form vs WLC gap).",
    }

    out = Path(args.out_json)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "out": str(out), "canon_unmatched": len(candidates), "emitted": len(top_n)},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
