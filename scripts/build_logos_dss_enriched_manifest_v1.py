#!/usr/bin/env python3
"""Manifest for DSS enriched JSONL (row counts, sources) — B-track satellite."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "data/logos/manuscripts/dss_parsed_enriched.jsonl"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_dss_enriched_manifest_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    resolved = path.resolve()
    root = ROOT.resolve()
    if resolved == root or root in resolved.parents:
        return str(resolved.relative_to(root)).replace("\\", "/")
    return str(resolved.as_posix())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-jsonl", type=Path, default=DEFAULT_IN)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.input_jsonl.is_file():
        print(f"missing {args.input_jsonl} — run build_btrack_dss_enriched_from_docs.py", file=sys.stderr)
        return 2

    rows = 0
    docs: Counter[str] = Counter()
    shared = 0
    for line in args.input_jsonl.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        rows += 1
        docs[str(row.get("source_doc") or "unknown")] += 1
        if row.get("has_shared_source"):
            shared += 1

    doc = {
        "schema": "logos_dss_enriched_manifest_v1",
        "version": "1.0.0",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "input_jsonl": _rel(args.input_jsonl),
        "row_count": rows,
        "rows_with_shared_vault_source": shared,
        "source_doc_counts": dict(docs.most_common(20)),
        "cross_ref_draft": "docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json",
        "track_wall": {
            "merge_into_canon_forbidden": True,
            "ready_for_external_send": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output} rows={rows}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
