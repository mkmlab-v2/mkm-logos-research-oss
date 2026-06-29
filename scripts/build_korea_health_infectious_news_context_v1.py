#!/usr/bin/env python3
"""Fetch Korea health / infectious-disease news for H-PL1 research slice (B-track).

Thin wrapper around build_korea_disaster_news_context_v1.py with health-focused queries.
Outputs articles JSON for biblical-history research slice ingest (not production overwrite).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTICLES = ROOT / "reports/korea_health_infectious_news_articles_v1.json"
DEFAULT_CSV = ROOT / "reports/korea_health_infectious_news_context_v1.csv"

DEFAULT_QUERIES = (
    "감염병",
    "코로나",
    "전염병",
    "방역",
    "독감",
    "세계보건기구",
    "호흡기바이러스",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date-from", default="2026-05-01")
    ap.add_argument("--date-to", default="2026-06-30")
    ap.add_argument("--queries", default=",".join(DEFAULT_QUERIES))
    ap.add_argument("--articles-json", type=Path, default=DEFAULT_ARTICLES)
    ap.add_argument("--out-csv", type=Path, default=DEFAULT_CSV)
    ap.add_argument("--use-exa", action="store_true")
    ap.add_argument("--exa-only", action="store_true")
    ap.add_argument("--skip-naver", action="store_true")
    ap.add_argument("--exa-per-query", type=int, default=20)
    args = ap.parse_args()

    cmd = [
        sys.executable,
        str(ROOT / "scripts/build_korea_disaster_news_context_v1.py"),
        "--date-from",
        args.date_from,
        "--date-to",
        args.date_to,
        "--queries",
        args.queries,
        "--articles-json",
        str(args.articles_json),
        "-o",
        str(args.out_csv),
        "--exa-per-query",
        str(args.exa_per_query),
    ]
    cmd.append("--use-exa")
    if args.exa_only:
        cmd.append("--exa-only")
    if args.skip_naver:
        cmd.append("--skip-naver")

    proc = subprocess.run(cmd, cwd=str(ROOT), check=False)
    if proc.returncode != 0:
        return int(proc.returncode)

    if args.articles_json.is_file():
        doc = json.loads(args.articles_json.read_text(encoding="utf-8-sig"))
        doc["schema"] = "korea_health_infectious_news_articles_v1"
        doc["research_lane"] = "biblical_history_H_PL1"
        doc["generated_at_utc"] = _utc_now()
        args.articles_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "articles_json": str(args.articles_json),
                "csv": str(args.out_csv),
                "queries": [q.strip() for q in args.queries.split(",") if q.strip()],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
