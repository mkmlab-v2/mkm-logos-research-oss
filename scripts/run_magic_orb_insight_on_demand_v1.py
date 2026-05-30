#!/usr/bin/env python3
"""On-demand magic_orb insight for arbitrary query ([HYPO] B-track)."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
BY_QUERY_REPORTS = ROOT / "reports/magic_orb_insight_by_query"
BY_QUERY_PUBLIC = ROOT / "projects/mkm/mkm-life/public/data/magic_orb_insight_by_query"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _query_hash16(query: str) -> str:
    norm = " ".join(query.strip().split())[:800]
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--query", required=True)
    ap.add_argument("--query-id", default="ondemand")
    ap.add_argument("--expand-graph", action="store_true")
    ap.add_argument("--include-ann-lite", action="store_true")
    ap.add_argument("--sync-public", action="store_true", default=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    qid = str(args.query_id)
    qh = _query_hash16(args.query)
    BY_QUERY_REPORTS.mkdir(parents=True, exist_ok=True)
    if args.sync_public:
        BY_QUERY_PUBLIC.mkdir(parents=True, exist_ok=True)

    router_out = BY_QUERY_REPORTS / f"router_{qid}_latest.json"
    bloom_out = BY_QUERY_REPORTS / f"bloom_{qid}_latest.json"
    insight_out = BY_QUERY_REPORTS / f"insight_{qid}_latest.json"
    chain_out = BY_QUERY_REPORTS / f"chain_{qid}_latest.json"

    cmd = [
        PY,
        str(ROOT / "scripts/run_question_semantic_rag_bridge_chain_v1.py"),
        "--query",
        args.query,
        "--query-id",
        qid,
        "--router-out",
        str(router_out),
        "--insight-out",
        str(insight_out),
        "--bloom-out",
        str(bloom_out),
        "--chain-out",
        str(chain_out),
    ]
    if args.expand_graph:
        cmd.append("--expand-graph")
    if not args.include_ann_lite:
        cmd.append("--skip-ann-lite")
    if args.dry_run:
        cmd.append("--dry-run")

    print("+", " ".join(cmd), flush=True)
    if args.dry_run:
        return 0
    rc = subprocess.call(cmd, cwd=str(ROOT))
    if rc != 0:
        return rc

    public_copy = BY_QUERY_PUBLIC / f"{qh}.json"
    if args.sync_public and insight_out.is_file():
        public_copy.write_text(insight_out.read_text(encoding="utf-8"), encoding="utf-8")

    summary = {
        "schema": "magic_orb_insight_on_demand_v1",
        "generated_at_utc": _utc_now(),
        "query": args.query,
        "query_id": qid,
        "query_key_hash": qh,
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "insight_artifact": str(insight_out.relative_to(ROOT)).replace("\\", "/"),
        "public_by_query": str(public_copy.relative_to(ROOT)).replace("\\", "/") if public_copy.is_file() else None,
    }
    out = BY_QUERY_REPORTS / f"on_demand_{qh}_latest.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "hash": qh, "public": str(public_copy)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
