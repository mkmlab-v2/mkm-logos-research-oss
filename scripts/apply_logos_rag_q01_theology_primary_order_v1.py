#!/usr/bin/env python3
"""Finalize q01: Ps/Jer thematic primary; Job.24.19 harness-only ([HYPO] B-track)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOLD = ROOT / "docs/final/artifacts/logos_semantic_query_gold_human_v1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gold-json", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    doc = json.loads(args.gold_json.read_text(encoding="utf-8-sig"))
    q01 = None
    for it in doc.get("items") or []:
        if isinstance(it, dict) and str(it.get("id")) == "q01":
            q01 = it
            break
    if not q01:
        raise SystemExit("q01 not found")

    thematic = ["Ps.89.28", "Jer.31.33", "Ps.45.13"]
    harness = ["Job.24.19"]
    prev = list(q01.get("gold_verse_ids_human") or [])
    q01["gold_verse_ids_human"] = thematic
    q01["gold_verse_ids_harness_top1"] = harness
    q01["adjudication_status"] = "commander_theology_primary_v1"
    q01["theology_primary_no_harness_union"] = True
    q01["adjudication_note"] = (
        "[HYPO] Commander: covenant thematic primary Ps/Jer; Job.24.19 harness-only for retrieval align."
    )
    doc["updated_at_utc"] = _utc_now()

    if not args.dry_run:
        args.gold_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "dry_run": args.dry_run,
                "prev_human": prev,
                "new_human": thematic,
                "harness_top1": harness,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
