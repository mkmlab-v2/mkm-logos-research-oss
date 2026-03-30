#!/usr/bin/env python3
"""Assemble master_atoms_lexicon_coverage_summary_v2 from per-rail summaries (contract §7.2)."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_MANIFEST = ROOT / "vault" / "external_lexicon" / "MANIFEST.json"


def _read_json(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8-sig")
    return json.loads(raw)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description="Merge rail summaries into coverage v2.")
    ap.add_argument("--strongs-summary", type=Path, default=OUT_DIR / "master_atoms_lexicon_seed_summary_latest.json")
    ap.add_argument("--morphhb-summary", type=Path, default=OUT_DIR / "master_atoms_morphhb_seed_summary_latest.json")
    ap.add_argument("--step-summary", type=Path, default=OUT_DIR / "master_atoms_step_audit_summary_latest.json")
    ap.add_argument("--corpus-split", type=Path, default=OUT_DIR / "master_atoms_corpus_split_summary_latest.json")
    ap.add_argument("--atoms-jsonl", type=Path, default=OUT_DIR / "original_language_master_atoms_latest.jsonl")
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--out-json", type=Path, default=OUT_DIR / "master_atoms_lexicon_coverage_summary_v2_latest.json")
    args = ap.parse_args()

    strongs = _read_json(Path(args.strongs_summary))
    morphhb = _read_json(Path(args.morphhb_summary))
    step = _read_json(Path(args.step_summary))
    corpus = _read_json(Path(args.corpus_split))

    manifest_path = Path(args.manifest)
    manifest_meta: dict[str, Any] = {}
    if manifest_path.is_file():
        man = _read_json(manifest_path)
        manifest_meta = {
            "path": str(manifest_path.resolve()),
            "sha256": _sha256_file(manifest_path),
            "schema": man.get("schema"),
            "generated_at_utc": man.get("generated_at_utc"),
        }

    v2: dict[str, Any] = {
        "schema": "master_atoms_lexicon_coverage_summary_v2",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "atoms": str(Path(args.atoms_jsonl).resolve()),
            "external_lexicon_manifest": manifest_meta or None,
            "morphhb_index": morphhb.get("inputs", {}).get("morphhb_index"),
            "strongs_greek_xml": strongs.get("inputs", {}).get("strongs_greek_xml"),
            "strongs_hebrew_xml": strongs.get("inputs", {}).get("strongs_hebrew_xml"),
            "tbesh": step.get("inputs", {}).get("tbesh"),
        },
        "precedence": ["rail_strongs_seed", "rail_morphhb", "rail_step_audit"],
        "by_rail": {
            "rail_strongs_seed": {
                "rail_id": "rail_strongs_seed",
                "coverage": strongs.get("coverage", {}),
                "source_summary_ref": str(Path(args.strongs_summary).resolve()),
            },
            "rail_morphhb": {
                "rail_id": "rail_morphhb",
                "coverage": morphhb.get("coverage", {}),
                "source_summary_ref": str(Path(args.morphhb_summary).resolve()),
            },
            "rail_step_audit": {
                "rail_id": "rail_step_audit",
                "coverage": step.get("coverage", {}),
                "source_summary_ref": str(Path(args.step_summary).resolve()),
                "note": step.get("note"),
            },
        },
        "corpus_buckets_ref": str(Path(args.corpus_split).resolve()),
        "corpus_split_snapshot": {
            "atoms_total": corpus.get("atoms_total"),
            "by_bucket_presence": corpus.get("by_bucket_presence"),
            "by_exclusive_pattern": corpus.get("by_exclusive_pattern"),
        },
        "note": "Do not sum fractions across rails; each rail has its own matcher semantics.",
    }

    out_path = Path(args.out_json)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(v2, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
