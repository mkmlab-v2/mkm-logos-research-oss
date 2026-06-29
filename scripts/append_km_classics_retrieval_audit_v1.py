#!/usr/bin/env python3
"""D3: Append km classics retrieval audit row (no patient text) [HYPO]."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "km_classics_retrieval_audit_v1"
DEFAULT_AUDIT = Path(__file__).resolve().parents[1] / "reports/km_classics_retrieval_audit_v1.jsonl"

# D4: on-demand batch only — no always-on background RAG agent.
ON_DEMAND_ONLY = True


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_audit_row(
    *,
    retrieval_query: str | None,
    source_ids_requested: list[str] | None,
    hit_source_ids: list[str],
    index_path: str,
    index_sha256_prefix: str | None = None,
    bundle_id: str | None = None,
    request_id: str | None = None,
    on_demand_only: bool = ON_DEMAND_ONLY,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "schema": SCHEMA,
        "version": 1,
        "hypothesis_tier": "B",
        "clinician_lane_only": True,
        "personadiary_join": False,
        "on_demand_only": on_demand_only,
        "ts_utc": _utc_now(),
        "retrieval_query": retrieval_query or "",
        "source_ids_requested": source_ids_requested or [],
        "hit_source_ids": hit_source_ids,
        "index_path": index_path,
        "index_sha256_prefix": index_sha256_prefix,
    }
    if bundle_id:
        row["bundle_id"] = bundle_id
    if request_id:
        row["request_id"] = request_id
    return row


def build_retrieval_audit_row(
    *,
    retrieval_query: str | None,
    requested_source_ids: list[str] | None,
    hit_source_ids: list[str],
    index_path: str,
    index_sha256_prefix: str | None = None,
    bundle_id: str = "",
    request_id: str | None = None,
) -> dict[str, Any]:
    return build_audit_row(
        retrieval_query=retrieval_query,
        source_ids_requested=requested_source_ids,
        hit_source_ids=hit_source_ids,
        index_path=index_path,
        index_sha256_prefix=index_sha256_prefix,
        bundle_id=bundle_id or None,
        request_id=request_id,
    )


def append_audit_row(audit_path: Path, row: dict[str, Any]) -> None:
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def append_retrieval_audit_row(row: dict[str, Any], audit_path: Path | None) -> None:
    path = audit_path or DEFAULT_AUDIT
    append_audit_row(path, row)


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--audit-jsonl", type=Path, default=DEFAULT_AUDIT)
    ap.add_argument("--retrieval-query", default="")
    ap.add_argument("--source-ids", default="", help="Comma-separated requested ids")
    ap.add_argument("--hit-source-ids", default="", help="Comma-separated resolved ids")
    ap.add_argument("--index-path", required=True)
    ap.add_argument("--index-sha256-prefix", default="")
    ap.add_argument("--bundle-id", default="")
    ap.add_argument("--request-id", default="")
    args = ap.parse_args()

    requested = [x.strip() for x in args.source_ids.split(",") if x.strip()] or None
    hits = [x.strip() for x in args.hit_source_ids.split(",") if x.strip()]
    row = build_audit_row(
        retrieval_query=args.retrieval_query or None,
        source_ids_requested=requested,
        hit_source_ids=hits,
        index_path=args.index_path.replace("\\", "/"),
        index_sha256_prefix=args.index_sha256_prefix or None,
        bundle_id=args.bundle_id or None,
        request_id=args.request_id or None,
    )
    append_audit_row(args.audit_jsonl, row)
    print(json.dumps({"ok": True, "audit": str(args.audit_jsonl), "hits": len(hits)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
