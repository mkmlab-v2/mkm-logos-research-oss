#!/usr/bin/env python3
"""Audit Hebrew atoms against STEPBible TBESH (Extended Strongs) brief lexicon."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.build_original_language_master_atoms import _normalize_token  # noqa: E402

DEFAULT_TBESH = (
    ROOT
    / "vault"
    / "external_lexicon"
    / "sources"
    / "stepbible-data"
    / "Lexicons"
    / "TBESH - Translators Brief lexicon of Extended Strongs for Hebrew - STEPBible.org CC BY.txt"
)
DEFAULT_ATOMS = ROOT / "reports" / "constitution" / "btrack_pilot" / "original_language_master_atoms_latest.jsonl"
OUT_DIR = ROOT / "reports" / "constitution" / "btrack_pilot"


def _normalize_estrong(cell: str) -> str:
    cell = cell.strip()
    m = re.match(r"^H(\d+)", cell, re.I)
    if not m:
        return cell
    return f"H{int(m.group(1))}"


def build_tbesh_norm_index(tbesh_path: Path) -> dict[str, list[str]]:
    """Hebrew column (tab file) -> list of eStrong# normalized H{n}."""
    idx: dict[str, list[str]] = defaultdict(list)
    in_data = False
    with tbesh_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("eStrong#\tdStrong"):
                in_data = True
                continue
            if not in_data:
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 4:
                continue
            estr = parts[0].strip()
            heb = parts[3].strip()
            if not estr.startswith("H") or not heb:
                continue
            key = _normalize_token(heb)
            if not key:
                continue
            hnorm = _normalize_estrong(estr)
            if hnorm not in idx[key]:
                idx[key].append(hnorm)
    return dict(idx)


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
    ap = argparse.ArgumentParser(description="STEP TBESH audit summary for Hebrew atoms.")
    ap.add_argument("--tbesh", type=Path, default=DEFAULT_TBESH)
    ap.add_argument("--atoms", type=Path, default=DEFAULT_ATOMS)
    ap.add_argument("--out-summary", type=Path, default=None)
    ap.add_argument("--write-latest", action="store_true")
    args = ap.parse_args()

    tbesh_path = Path(args.tbesh)
    atoms_path = Path(args.atoms)
    if not tbesh_path.is_file():
        print(f"ERROR: TBESH file not found: {tbesh_path}")
        return 2
    if not atoms_path.is_file():
        print(f"ERROR: atoms not found: {atoms_path}")
        return 2

    idx = build_tbesh_norm_index(tbesh_path)
    stats: dict = {
        "schema": "master_atoms_step_audit_summary_v1",
        "rail_id": "rail_step_audit",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "tbesh": str(tbesh_path.resolve()),
            "atoms": str(atoms_path.resolve()),
        },
        "tbesh_norm_keys": len(idx),
        "hebrew_atoms": 0,
        "matched": 0,
        "unmatched": 0,
        "ambiguous": 0,
        "coverage": {},
    }

    for row in _iter_jsonl(atoms_path):
        if str(row.get("lang")) != "hebrew":
            continue
        stats["hebrew_atoms"] += 1
        norm = str(row.get("normalized_form") or "")
        refs = idx.get(norm, [])
        if not refs:
            stats["unmatched"] += 1
        elif len(refs) > 1:
            stats["ambiguous"] += 1
            stats["matched"] += 1
        else:
            stats["matched"] += 1

    ha = stats["hebrew_atoms"]
    stats["coverage"] = {
        "hebrew": {
            "matched_any_tbesh_row": stats["matched"],
            "unmatched": stats["unmatched"],
            "ambiguous_norm": stats["ambiguous"],
            "fraction_of_hebrew_atoms": round((stats["matched"] / ha) if ha else 0.0, 6),
        }
    }
    stats["note"] = "Audit-only join on TBESH Hebrew column after NFKD strip; not lemma disambiguation."

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = args.out_summary or (OUT_DIR / f"master_atoms_step_audit_summary_{ts}.json")
    out_path = Path(out_path)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.write_latest:
        latest = OUT_DIR / "master_atoms_step_audit_summary_latest.json"
        latest.write_bytes(out_path.read_bytes())

    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
