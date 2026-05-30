#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch magic_orb insight + graph_bloom for fixture queries (B-track, NON_GATING)."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
FIXTURE = ROOT / "docs/final/fixtures/magic_orb_question_insight_queries_v1.json"
FIXTURE_FALLBACK = ROOT / "projects/mkm/mkm-life/public/data/magic_orb_question_insight_queries_v1.json"
BY_QUERY_REPORTS = ROOT / "reports/magic_orb_insight_by_query"
BY_QUERY_PUBLIC = ROOT / "projects/mkm/mkm-life/public/data/magic_orb_insight_by_query"
DEFAULT_BATCH_OUT = ROOT / "reports/magic_orb_question_insight_query_batch_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _query_hash16(query: str) -> str:
    norm = " ".join(query.strip().split())[:800]
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]


def _load_fixture(path: Path) -> list[dict[str, Any]]:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    items = doc.get("items") or []
    return [it for it in items if isinstance(it, dict) and it.get("id") and it.get("query_ko")]


def _run_chain(
    *,
    query: str,
    query_id: str,
    expand_graph: bool,
    sync_public: bool,
    router_out: Path,
    insight_out: Path,
    bloom_out: Path,
    dry_run: bool,
) -> int:
    cmd = [
        PY,
        str(ROOT / "scripts/run_question_semantic_rag_bridge_chain_v1.py"),
        "--query",
        query,
        "--query-id",
        query_id,
        "--router-out",
        str(router_out),
        "--insight-out",
        str(insight_out),
        "--bloom-out",
        str(bloom_out),
        "--chain-out",
        str(BY_QUERY_REPORTS / f"chain_{query_id}_latest.json"),
        "--skip-ann-lite",
    ]
    if expand_graph:
        cmd.append("--expand-graph")
    if sync_public:
        cmd.append("--sync-public")
    if dry_run:
        cmd.append("--dry-run")
    print("+", " ".join(cmd), flush=True)
    if dry_run:
        return 0
    return subprocess.call(cmd, cwd=str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fixture-json", type=Path, default=FIXTURE)
    ap.add_argument("--primary-query-id", default="q01")
    ap.add_argument("--expand-graph", action="store_true", help="bible_meaning_graph enrichment on all rows")
    ap.add_argument("--expand-primary-only", action="store_true", help="expand-graph only for primary id")
    ap.add_argument("--sync-public-primary", action="store_true", default=True)
    ap.add_argument("--sync-public-by-query", action="store_true", default=True)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_BATCH_OUT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    fixture_path = args.fixture_json if args.fixture_json.is_absolute() else ROOT / args.fixture_json
    if not fixture_path.is_file() and FIXTURE_FALLBACK.is_file():
        fixture_path = FIXTURE_FALLBACK
    items = _load_fixture(fixture_path)
    if not items:
        raise SystemExit(f"no items in fixture: {args.fixture_json}")

    BY_QUERY_REPORTS.mkdir(parents=True, exist_ok=True)
    if args.sync_public_by_query:
        BY_QUERY_PUBLIC.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    all_ok = True

    for it in items:
        qid = str(it["id"])
        query = str(it["query_ko"])
        qh = _query_hash16(query)
        is_primary = qid == args.primary_query_id
        expand = args.expand_graph or (args.expand_primary_only and is_primary)
        sync_pub = (args.sync_public_primary and is_primary) or (
            args.sync_public_by_query and not is_primary
        )

        router_out = BY_QUERY_REPORTS / f"router_{qid}_latest.json"
        bloom_out = BY_QUERY_REPORTS / f"bloom_{qid}_latest.json"
        insight_out = BY_QUERY_REPORTS / f"insight_{qid}_latest.json"

        if is_primary:
            router_out = ROOT / "reports/question_logos_subgraph_router_sidecar_v1_latest.json"
            bloom_out = ROOT / "docs/final/artifacts/magic_orb_graph_bloom_v1_latest.json"
            insight_out = ROOT / "docs/final/artifacts/magic_orb_question_insight_v1_latest.json"

        rc = _run_chain(
            query=query,
            query_id=qid,
            expand_graph=expand,
            sync_public=sync_pub and is_primary,
            router_out=router_out,
            insight_out=insight_out,
            bloom_out=bloom_out,
            dry_run=args.dry_run,
        )
        ok = rc == 0
        all_ok = all_ok and ok

        bloom_nodes = None
        if ok and insight_out.is_file() and not args.dry_run:
            payload = json.loads(insight_out.read_text(encoding="utf-8-sig"))
            gb = payload.get("graph_bloom") or {}
            bloom_nodes = (gb.get("stats") or {}).get("node_count")

        if ok and args.sync_public_by_query and not args.dry_run:
            public_copy = BY_QUERY_PUBLIC / f"{qh}.json"
            public_copy.write_text(insight_out.read_text(encoding="utf-8"), encoding="utf-8")
            if is_primary:
                latest_public = ROOT / "projects/mkm/mkm-life/public/data/magic_orb_question_insight_v1_latest.json"
                latest_public.write_text(insight_out.read_text(encoding="utf-8"), encoding="utf-8")

        rows.append(
            {
                "query_id": qid,
                "query_ko": query,
                "query_key_hash": qh,
                "is_primary": is_primary,
                "expand_graph": expand,
                "exit_code": rc,
                "ok": ok,
                "graph_bloom_nodes": bloom_nodes,
                "insight_artifact": str(insight_out.relative_to(ROOT)).replace("\\", "/"),
                "public_by_query": (
                    str((BY_QUERY_PUBLIC / f"{qh}.json").relative_to(ROOT)).replace("\\", "/")
                    if args.sync_public_by_query
                    else None
                ),
            }
        )

    batch_doc = {
        "schema": "magic_orb_question_insight_query_batch_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "fixture_json": str(args.fixture_json.relative_to(ROOT)).replace("\\", "/"),
        "primary_query_id": args.primary_query_id,
        "expand_graph": bool(args.expand_graph or args.expand_primary_only),
        "all_ok": all_ok,
        "rows": rows,
    }
    out = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(batch_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": all_ok, "batch": str(out), "rows": len(rows)}, ensure_ascii=False))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
