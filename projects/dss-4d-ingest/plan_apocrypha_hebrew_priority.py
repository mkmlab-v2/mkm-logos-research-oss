#!/usr/bin/env python3
"""Emit Hebrew-priority apocrypha ingest plan (ext3 manifest · [HYPO])."""

from __future__ import annotations

import argparse
from pathlib import Path

from _frontline_legacy_common import ROOT, research_meta, utc_now, write_json


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--manifest", default="pilot_manifest_ext3_hebrew_priority.json")
    ap.add_argument("--out-json", type=Path, default=None)
    args = ap.parse_args()

    out_path = args.out_json or ROOT / "outputs" / f"apocrypha_hebrew_priority_plan_{args.tag}.json"
    ndjson = ROOT / "outputs" / "apocrypha_tokens_pilot_manifest_ext3_hebrew_priority.ndjson"

    payload = {
        "schema": "apocrypha_hebrew_priority_plan_v1",
        "generated_at_utc": utc_now(),
        "tag": args.tag,
        "manifest": args.manifest,
        "ndjson_on_disk": str(ndjson),
        "ndjson_exists": ndjson.is_file(),
        "policy": "prefer_ext3_hebrew_primary_no_live_refetch_by_default",
        **research_meta(),
    }
    write_json(out_path, payload)
    print(f"plan_ready={payload['ndjson_exists']}\njson={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
