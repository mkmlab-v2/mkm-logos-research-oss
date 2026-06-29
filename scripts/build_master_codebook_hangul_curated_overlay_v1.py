#!/usr/bin/env python3
"""B-track [HYPO]: 41658 + curated manifest lemmas only (≤50)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MANIFEST = ROOT / "docs/final/artifacts/hangul_lexicon_curated_lemma_manifest_v1.json"
BASE = ROOT / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41658_rows_latest.json"
DEFAULT_OUT = ROOT / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41658_hangul_curated_overlay.json"
META_OUT = ROOT / "reports/master_codebook_hangul_curated_overlay_meta_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ko_entry(form: str, tier: str) -> dict[str, Any]:
    return {
        "atom_id": f"hangul_curated_v1::{form}",
        "lang": "ko",
        "normalized_form": form,
        "occurrences": 0,
        "lexicon_strongs_candidates": [],
        "lexicon_match_method": "hangul_curated_ingest_v1",
        "morphhb_match_method": "skipped_lang",
        "morphhb_strongs_hints": [],
        "morphhb_chosen": None,
        "morphhb_disambiguation": None,
        "curated_tier": tier,
    }


def build_from_manifest(manifest_path: Path, base_path: Path, out_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    base = json.loads(base_path.read_text(encoding="utf-8"))
    by_id = {
        e["atom_id"]: e
        for e in base.get("entries") or []
        if isinstance(e, dict) and e.get("atom_id")
    }
    existing = {
        str(e.get("normalized_form", "")).strip().lower()
        if str(e.get("normalized_form", "")).isascii()
        else str(e.get("normalized_form", "")).strip()
        for e in by_id.values()
    }
    added: list[str] = []
    for row in manifest.get("lemmas") or []:
        form = str(row.get("form", "")).strip()
        tier = str(row.get("tier", "B_sasang_core"))
        key = form.lower() if form.isascii() else form
        if not form or key in existing:
            continue
        ent = _ko_entry(form, tier)
        by_id[ent["atom_id"]] = ent
        existing.add(key)
        added.append(ent["atom_id"])
    entries = list(by_id.values())
    payload = dict(base)
    payload["generated_at_utc"] = _utc()
    payload["row_count"] = len(entries)
    payload["entries"] = entries
    payload["overlay_meta"] = {
        "schema": "master_codebook_hangul_curated_overlay_v1",
        "research_only": True,
        "track_a_active_write": False,
        "manifest": str(manifest_path.relative_to(ROOT)).replace("\\", "/"),
        "atom_ids_added": added,
        "atom_ids_added_count": len(added),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    return payload["overlay_meta"]


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    manifest_path = args.manifest if args.manifest.is_absolute() else (ROOT / args.manifest)
    out_path = args.out if args.out.is_absolute() else (ROOT / args.out)
    if not manifest_path.is_file() or not BASE.is_file():
        print("ABORT: manifest or base missing")
        return 1
    meta = build_from_manifest(manifest_path, BASE, out_path)
    meta_doc = {"schema": "master_codebook_hangul_curated_overlay_meta_v1", "generated_at_utc": _utc(), **meta}
    META_OUT.write_text(json.dumps(meta_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(out_path), "added": meta["atom_ids_added_count"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
