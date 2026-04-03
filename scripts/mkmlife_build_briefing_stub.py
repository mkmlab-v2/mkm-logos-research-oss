#!/usr/bin/env python3
"""
Build mkmlife briefing stub records: RSS fetch -> attach persona (UX layer) -> JSONL.

No Gemini required. Enable feeds in data/mkmlife/rss_sources_v1.json (set enabled: true).

Usage (from repo root):
  py scripts/mkmlife_build_briefing_stub.py --constitution 태음인 --pathology IL
  py scripts/mkmlife_build_briefing_stub.py --constitution 소음인 --pathology DL --max-per-feed 5
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

WORKSPACE = Path(__file__).resolve().parent.parent
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

from tools.mkmlife.persona_mapper import resolve_persona_by_constitution_pathology  # noqa: E402
from tools.mkmlife.rss_minimal import parse_feed_items  # noqa: E402
from tools.mkmlife.briefing_score_v1 import score_briefing_stub_row  # noqa: E402


def fetch_url(url: str, timeout: float) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "mkmlife-briefing-stub/1.0 (+local)"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def load_sources(path: Path) -> Dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def build_records(
    *,
    constitution_ko: str,
    pathology_level: str,
    sibseong_input: str,
    feeds: List[Dict[str, Any]],
    max_per_feed: int,
    timeout: float,
    use_scoring: bool,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    persona = resolve_persona_by_constitution_pathology(constitution_ko, pathology_level)
    pid = persona["persona_id"]
    persona_boost_fallback = persona.get("news_category_boost", [])
    disclaimer = persona.get("disclaimer_ui_ko", "")
    created = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    records: List[Dict[str, Any]] = []
    errors: List[str] = []

    for feed in feeds:
        if not feed.get("enabled", False):
            continue
        fid = feed.get("id", "unknown")
        url = feed.get("url", "")
        cat = feed.get("category", "")
        if not url:
            errors.append(f"{fid}: missing url")
            continue
        try:
            raw = fetch_url(url, timeout=timeout)
        except (urllib.error.URLError, OSError) as e:
            errors.append(f"{fid}: fetch failed: {e}")
            continue
        items = parse_feed_items(raw)
        for it in items[:max_per_feed]:
            title = it["title"]
            row: Dict[str, Any] = {
                "schema": "mkmlife_briefing_record_v1",
                "created_at_utc": created,
                "persona_id": pid,
                "constitution_ko": constitution_ko,
                "pathology_level": pathology_level.upper(),
                "feed_id": fid,
                "feed_category": cat,
                "title": title,
                "link": it["link"],
                "summary_stub": "[pending] Gemini or n8n summarization step",
                "disclaimer_ui_ko": disclaimer,
            }
            if use_scoring:
                score, breakdown, eff_boost = score_briefing_stub_row(
                    title=title,
                    feed_category=cat,
                    feed_id=fid,
                    constitution_ko=constitution_ko,
                    sibseong_input=sibseong_input,
                )
                row["score_final"] = round(score, 4)
                row["score_breakdown_v1"] = breakdown
                row["sibseong_input"] = sibseong_input
                row["news_category_boost"] = eff_boost
                row["summary_prompt_v1"] = (
                    "헤드라인을 원문 복제하지 말고 비평적 재구성으로 2~3문장 요약하라. "
                    "출처 링크를 유지하고 의료·투자 단정 문구를 금지한다. "
                    "프레이밍: 요약-근거-개인화 인사이트."
                )
                row["scoring_engine"] = "briefing_score_v1"
            else:
                row["news_category_boost"] = persona_boost_fallback
                row["scoring_engine"] = "legacy_persona_boost_only"
            records.append(row)
    if use_scoring:
        records.sort(key=lambda r: float(r.get("score_final", 0)), reverse=True)
    return records, errors


def main() -> int:
    ap = argparse.ArgumentParser(description="mkmlife RSS -> briefing stub JSONL")
    ap.add_argument("--constitution", default="태음인", help="태양인|태음인|소양인|소음인")
    ap.add_argument("--pathology", default="IL", help="SL|IL|DL")
    ap.add_argument(
        "--sources",
        type=Path,
        default=WORKSPACE / "data" / "mkmlife" / "rss_sources_v1.json",
    )
    ap.add_argument("--out", type=Path, default=WORKSPACE / "reports" / "mkmlife" / "briefing_stub_latest.jsonl")
    ap.add_argument("--max-per-feed", type=int, default=3)
    ap.add_argument("--timeout", type=float, default=25.0)
    ap.add_argument("--dry-run", action="store_true", help="Print persona only; no network")
    ap.add_argument(
        "--sibseong",
        default="JJ",
        help="십성 코드(BG..JI) 또는 한글 라벨. merged_boost·score_final에 사용 (기본 JJ=정재/재성).",
    )
    ap.add_argument(
        "--legacy-no-score",
        action="store_true",
        help="v1.0 동작: 페르소나 news_category_boost만 붙이고 score 정렬 없음.",
    )
    args = ap.parse_args()

    if args.dry_run:
        p = resolve_persona_by_constitution_pathology(args.constitution, args.pathology)
        print(json.dumps({"persona_id": p["persona_id"], "persona": p}, ensure_ascii=False, indent=2))
        return 0

    data = load_sources(args.sources)
    feeds = data.get("feeds", [])
    enabled = [f for f in feeds if f.get("enabled")]
    if not enabled:
        print(
            "No enabled feeds. Edit data/mkmlife/rss_sources_v1.json and set enabled: true on at least one feed.",
            file=sys.stderr,
        )
        return 2

    records, errors = build_records(
        constitution_ko=args.constitution,
        pathology_level=args.pathology,
        sibseong_input=args.sibseong,
        feeds=feeds,
        max_per_feed=args.max_per_feed,
        timeout=args.timeout,
        use_scoring=not args.legacy_no_score,
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for row in records:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    if errors:
        err_path = args.out.with_suffix(".errors.txt")
        err_path.write_text("\n".join(errors) + "\n", encoding="utf-8")

    print(f"Wrote {len(records)} records to {args.out}")
    if errors:
        print(f"Errors logged: {len(errors)} (see {args.out.with_suffix('.errors.txt')})")
        return 1 if not records else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
