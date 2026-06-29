#!/usr/bin/env python3
"""Copy reports/magic_orb_insight_by_query/insight_{id}_latest.json to mkmlife public by-query hash."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "docs/final/fixtures/magic_orb_question_insight_queries_v1.json"
PUB = ROOT / "projects/mkm/mkm-life/public/data/magic_orb_insight_by_query"
REP = ROOT / "reports/magic_orb_insight_by_query"


def query_hash16(query: str) -> str:
    norm = " ".join(query.strip().split())[:800]
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--query-ids", nargs="+", required=True)
    ap.add_argument("--fixture-json", type=Path, default=FIXTURE)
    args = ap.parse_args()
    allow = {str(x) for x in args.query_ids}
    doc = json.loads(args.fixture_json.read_text(encoding="utf-8"))
    items = [it for it in (doc.get("items") or []) if isinstance(it, dict) and str(it.get("id")) in allow]
    if not items:
        print(f"no fixture items for {allow}")
        return 2
    PUB.mkdir(parents=True, exist_ok=True)
    for it in items:
        qid = str(it["id"])
        src = REP / f"insight_{qid}_latest.json"
        if not src.is_file():
            print(f"missing {src}")
            return 2
        dst = PUB / f"{query_hash16(str(it['query_ko']))}.json"
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"OK {qid} -> {dst.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
