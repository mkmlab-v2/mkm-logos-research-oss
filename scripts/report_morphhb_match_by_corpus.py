#!/usr/bin/env python3
"""Cross-tab MorphHB rail match_method × corpus exclusive_pattern (Hebrew atoms only)."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.report_master_atoms_corpus_split import (  # noqa: E402
    SOURCE_BASENAME_TO_BUCKET,
    _atom_exclusive_pattern,
)

OUT_DIR = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_ATOMS = OUT_DIR / "original_language_master_atoms_latest.jsonl"
DEFAULT_SEED = OUT_DIR / "master_atoms_morphhb_seed_latest.jsonl"
DEFAULT_OUT = OUT_DIR / "master_atoms_morphhb_match_by_corpus_latest.json"


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
    ap = argparse.ArgumentParser(description="MorphHB match_method × corpus pattern crosstab")
    ap.add_argument("--atoms-jsonl", type=Path, default=DEFAULT_ATOMS)
    ap.add_argument("--morphhb-seed-jsonl", type=Path, default=DEFAULT_SEED)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
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

    by_method: dict[str, int] = defaultdict(int)
    by_pattern: dict[str, int] = defaultdict(int)
    crosstab: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    hebrew_rows = 0

    for row in _iter_jsonl(seed_path):
        if str(row.get("lang")) != "hebrew":
            continue
        hebrew_rows += 1
        aid = row.get("atom_id")
        method = str(row.get("match_method") or "unknown")
        by_method[method] += 1

        atom = atoms_by_id.get(str(aid)) if aid is not None else None
        sfiles = (atom or {}).get("source_files") or []
        if not isinstance(sfiles, list):
            sfiles = []
        basenames = [str(x) for x in sfiles]
        _buckets, pattern = _atom_exclusive_pattern(basenames)
        by_pattern[pattern] += 1
        crosstab[method][pattern] += 1

    raw_crosstab: dict[str, dict[str, int]] = {
        m: dict(sorted(ct.items())) for m, ct in sorted(crosstab.items())
    }
    # Stable keys for downstream contracts (may be zero after multi-resolution).
    morphhb_methods = (
        "morphhb_unmatched",
        "morphhb_wlc",
        "morphhb_wlc_multi",
        "morphhb_wlc_no_strong",
    )
    crosstab_out: dict[str, dict[str, int]] = {
        m: dict(raw_crosstab.get(m, {})) for m in morphhb_methods
    }

    payload: dict[str, Any] = {
        "schema": "master_atoms_morphhb_match_by_corpus_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "atoms": str(atoms_path.resolve()),
            "morphhb_seed": str(seed_path.resolve()),
            "source_basename_to_bucket": dict(SOURCE_BASENAME_TO_BUCKET),
        },
        "hebrew_rows_in_morphhb_seed": hebrew_rows,
        "by_match_method": dict(sorted(by_method.items())),
        "by_exclusive_pattern": dict(sorted(by_pattern.items())),
        "crosstab_match_method_x_exclusive_pattern": crosstab_out,
        "note": "exclusive_pattern from report_master_atoms_corpus_split rules; Hebrew-only rows from morphhb seed.",
    }

    out = Path(args.out_json)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out), "hebrew_rows": hebrew_rows}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
