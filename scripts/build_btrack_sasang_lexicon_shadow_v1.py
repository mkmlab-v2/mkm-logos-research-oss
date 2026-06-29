#!/usr/bin/env python3
"""Build B-track Sasang role shadow for master codebook — read-only, no mutation."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.btrack_sasang_role_router_v1 import (  # noqa: E402
    build_lexicon_shadow,
    load_codebook_entries,
    sha256_file,
)
from scripts.core.master_codebook_lexicon_v1_bridge import resolve_latest_codebook_path  # noqa: E402

OUT_DEFAULT = ROOT / "reports/btrack_sasang_lexicon_shadow_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--codebook", type=Path, default=None, help="Explicit codebook JSON (read-only)")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--mismatch-threshold", type=float, default=0.55)
    ap.add_argument("--no-align-strong-hints", action="store_true")
    args = ap.parse_args()

    codebook = args.codebook or resolve_latest_codebook_path()
    if codebook is None or not codebook.is_file():
        print("codebook_missing", file=sys.stderr)
        return 1

    before_sha = sha256_file(codebook)
    entries = load_codebook_entries(codebook)
    doc = build_lexicon_shadow(
        entries,
        codebook_path=codebook,
        codebook_sha256=before_sha,
        mismatch_distance_threshold=args.mismatch_threshold,
        align_strong_rule_hints=not args.no_align_strong_hints,
    )
    after_sha = sha256_file(codebook)
    doc["generated_at_utc"] = _utc()
    doc["codebook_unmodified"] = before_sha == after_sha
    doc["reproduce_cmd"] = (
        "py scripts/build_btrack_sasang_lexicon_shadow_v1.py"
        + (f" --codebook {codebook}" if args.codebook else "")
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(args.out),
                "entries": doc["codebook_entry_count"],
                "mismatch_rate": doc["mismatch_summary"]["mismatch_rate"],
                "codebook_unmodified": doc["codebook_unmodified"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if doc["codebook_unmodified"] and doc["codebook_entry_count"] > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
