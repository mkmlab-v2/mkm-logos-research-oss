#!/usr/bin/env python3
"""TR / Byzantine tradition ingest scaffold for 15 NT MT-only gaps (no licensed text)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_POLICY = ROOT / "data/logos/logos_gap_mt_only_policy_v1.jsonl"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_tr_tradition_scaffold_v1_latest.json"
DEFAULT_MANIFEST_DIR = ROOT / "data/logos/manuscripts/tr_tradition"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--policy-jsonl", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--write-manifest-dir", action="store_true")
    args = ap.parse_args()

    if not args.policy_jsonl.is_file():
        print(f"missing {args.policy_jsonl}", file=sys.stderr)
        return 2

    verses: list[dict[str, Any]] = []
    for line in args.policy_jsonl.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        pol = json.loads(line)
        vid = str(pol["verse_id"])
        verses.append(
            {
                "verse_id": vid,
                "tradition": "TR_byzantine",
                "licensed": False,
                "greek_text_path": None,
                "ingest_status": "awaiting_source",
                "allowed_actions": [
                    "attach_licensed_greek_jsonl",
                    "compute_tr_vs_sblgnt_l2_in_variant_layer_only",
                ],
                "forbidden_actions": [
                    "merge_into_verse_decoded_v2_complete",
                    "auto_promote_track_a",
                ],
            }
        )

    doc = {
        "schema": "logos_tr_tradition_scaffold_v1",
        "version": "1.0.0",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "verse_count": len(verses),
        "verses": verses,
        "ingest_contract": {
            "expected_input": "data/logos/manuscripts/tr_greek_by_verse_v1.jsonl",
            "fields": ["verse_id", "greek_text", "source_id", "license_tag"],
            "downstream": "docs/final/artifacts/logos_textual_variant_distance_v1_latest.json",
        },
        "track_wall": {
            "merge_into_complete_jsonl": False,
            "ready_for_external_send": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.write_manifest_dir:
        DEFAULT_MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
        readme = DEFAULT_MANIFEST_DIR / "README.ingest.txt"
        readme.write_text(
            "Place licensed TR/Byzantine Greek per-verse JSONL here.\n"
            "Do not commit unlicensed text to git.\n",
            encoding="utf-8",
        )

    print(f"wrote {args.output} verses={len(verses)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
