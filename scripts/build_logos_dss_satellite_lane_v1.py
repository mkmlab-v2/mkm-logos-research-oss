#!/usr/bin/env python3
"""Project DSS enriched JSONL into logos_verse_4d_v1 satellite lane (B-track, no canon merge)."""

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

from scripts.build_logos_verse_4d_corpus_v1 import _row_to_record  # noqa: E402

DEFAULT_IN = ROOT / "data/logos/manuscripts/dss_parsed_enriched.jsonl"
DEFAULT_OUT = ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_dss_lane_v1_latest.jsonl"
DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/logos_dss_satellite_lane_manifest_v1_latest.json"

TRACK_WALL = {
    "a_track_auto_promotion": False,
    "live_trading_trigger": False,
    "ready_for_external_send": False,
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    resolved = path.resolve()
    root = ROOT.resolve()
    if resolved == root or root in resolved.parents:
        return str(resolved.relative_to(root)).replace("\\", "/")
    return str(resolved.as_posix())


def _adapt_row(row: dict[str, Any]) -> dict[str, Any]:
    rid = str(row.get("id") or "").strip()
    text = str(row.get("text") or "").strip()
    if not rid or not text:
        return {}
    return {
        "verse_id": f"dss:{rid}",
        "original_text": text,
        "source_ref": str(row.get("source_doc") or "dss_enriched"),
        "dss_enriched_id": rid,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-jsonl", type=Path, default=DEFAULT_IN)
    ap.add_argument("--output-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--max-rows", type=int, default=0)
    args = ap.parse_args()

    if not args.input_jsonl.is_file():
        print(f"missing {args.input_jsonl}", file=sys.stderr)
        return 2

    ts = _utc_now()
    input_posix = _rel(args.input_jsonl)
    records: list[dict[str, Any]] = []
    for i, line in enumerate(args.input_jsonl.read_text(encoding="utf-8").splitlines()):
        if args.max_rows and i >= args.max_rows:
            break
        if not line.strip():
            continue
        adapted = _adapt_row(json.loads(line))
        if not adapted:
            continue
        rec = _row_to_record(
            adapted,
            lane="dss",
            recipe_id="gematria_bridge_v1_recompute_audit",
            source_kind="recomputed",
            input_path=input_posix,
            ts=ts,
            recompute=True,
        )
        if rec:
            rec["track_wall"] = dict(TRACK_WALL)
            rec["dss_enriched_id"] = adapted["dss_enriched_id"]
            records.append(rec)

    if not records:
        print("no DSS lane records emitted", file=sys.stderr)
        return 2

    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.output_jsonl.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    manifest = {
        "schema": "logos_dss_satellite_lane_manifest_v1",
        "version": "1.0.0",
        "ts_utc": ts,
        "hypothesis_tier": "B",
        "input_enriched_jsonl": input_posix,
        "output_lane_jsonl": _rel(args.output_jsonl),
        "row_count": len(records),
        "lane": "dss",
        "merge_into_canon_forbidden": True,
        "track_wall": dict(TRACK_WALL),
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output_jsonl} rows={len(records)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
