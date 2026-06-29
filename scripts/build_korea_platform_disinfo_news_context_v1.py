#!/usr/bin/env python3
"""Fetch Korea platform / disinformation news for H-PR1 research ingest (B-track)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTICLES = ROOT / "reports/korea_platform_disinfo_news_articles_v1.json"
DEFAULT_CSV = ROOT / "reports/korea_platform_disinfo_news_context_v1.csv"

DEFAULT_QUERIES = (
    "가짜뉴스",
    "플랫폼 규제",
    "인터넷 검열",
    "딥페이크",
    "SNS 허위정보",
    "소셜미디어",
    "디지털 플랫폼",
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
    ap.add_argument("--exa-per-query", type=int, default=15)
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
    if args.use_exa:
        cmd.append("--use-exa")
    if args.exa_only:
        cmd.append("--exa-only")
    if args.skip_naver:
        cmd.append("--skip-naver")

    proc = subprocess.run(cmd, cwd=str(ROOT), check=False)
    meta = {
        "schema": "korea_platform_disinfo_news_context_v1",
        "generated_at_utc": _utc_now(),
        "research_rail": "B",
        "hypothesis_id": "H-PR1",
        "articles_json": str(args.articles_json),
        "exit_code": proc.returncode,
    }
    if args.articles_json.is_file():
        doc = json.loads(args.articles_json.read_text(encoding="utf-8-sig"))
        meta["n_articles"] = doc.get("n_articles")
    print(json.dumps(meta, ensure_ascii=False))
    return int(proc.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
