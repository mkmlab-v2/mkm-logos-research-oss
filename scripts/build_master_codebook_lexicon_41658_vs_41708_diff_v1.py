#!/usr/bin/env python3
"""B-track [HYPO]: diff 41658 base vs 41708 production lexicon rows (read-only)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41658_rows_latest.json"
PROD = ROOT / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41708_rows_latest.json"
DEFAULT_OUT = (
    ROOT
    / "experiments/compression_pipeline_grid_sweep_v1/results/master_codebook_lexicon_41658_vs_41708_diff_v1_latest.json"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _index(entries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in entries:
        aid = str(row.get("atom_id") or "")
        if aid:
            out[aid] = row
    return out


def build_diff(base_path: Path, prod_path: Path) -> dict[str, Any]:
    base_doc = _load(base_path)
    prod_doc = _load(prod_path)
    base_idx = _index(base_doc.get("entries") or [])
    prod_idx = _index(prod_doc.get("entries") or [])
    base_ids = set(base_idx)
    prod_ids = set(prod_idx)
    added_ids = sorted(prod_ids - base_ids)
    removed_ids = sorted(base_ids - prod_ids)
    changed: list[dict[str, Any]] = []
    for aid in sorted(base_ids & prod_ids):
        b, p = base_idx[aid], prod_idx[aid]
        if b.get("normalized_form") != p.get("normalized_form"):
            changed.append(
                {
                    "atom_id": aid,
                    "base_form": b.get("normalized_form"),
                    "prod_form": p.get("normalized_form"),
                }
            )
    added_sample = [
        {
            "atom_id": aid,
            "normalized_form": prod_idx[aid].get("normalized_form"),
            "lang": prod_idx[aid].get("lang"),
        }
        for aid in added_ids[:80]
    ]
    return {
        "schema": "master_codebook_lexicon_41658_vs_41708_diff_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "base_path": str(base_path).replace("\\", "/"),
        "prod_path": str(prod_path).replace("\\", "/"),
        "base_row_count": base_doc.get("row_count") or len(base_idx),
        "prod_row_count": prod_doc.get("row_count") or len(prod_idx),
        "delta_row_count": (prod_doc.get("row_count") or len(prod_idx))
        - (base_doc.get("row_count") or len(base_idx)),
        "added_count": len(added_ids),
        "removed_count": len(removed_ids),
        "normalized_form_changed_count": len(changed),
        "added_atom_ids_sample": added_sample,
        "removed_atom_ids": removed_ids[:40],
        "normalized_form_changed_sample": changed[:40],
        "interpretation": (
            "41708 = 41658 + Hangul curated v2 overlay (typically +50 rows). "
            "Grid sweep must default to 41708 when comparing to frozen ACTIVE."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", type=Path, default=BASE)
    ap.add_argument("--prod", type=Path, default=PROD)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    if not args.base.is_file() or not args.prod.is_file():
        print("missing lexicon input", file=sys.stderr)
        return 1
    doc = build_diff(args.base, args.prod)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(args.out), "delta_row_count": doc["delta_row_count"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
