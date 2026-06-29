#!/usr/bin/env python3
"""Map news_observation_v1 rows to Logos research themes ([NON_GATING] overlay).

Does not change direction_score or trading gates. Outputs a sidecar JSON for
insight_bundle / Track C / three-lens envelope consumers.

research_only · B-track only.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NEWS_JSONL = ROOT / "docs/final/artifacts/news_observation_v1_latest.jsonl"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_news_theme_overlay_v1_latest.json"

# Korean keyword groups -> logos_metaphor_db slug (research metaphor, not doctrine)
THEME_RULES: list[dict[str, Any]] = [
    {
        "theme_slug": "elijah_carmel",
        "theme_ko": "갈멜·불·심판 은유",
        "anchor_ref": "열왕기상 18:39",
        "keywords": ("산불", "화재", "폭염", "가뭄", "건조", "불조심"),
    },
    {
        "theme_slug": "noah_flood",
        "theme_ko": "홍수·심판 은유",
        "anchor_ref": "창세기 7:12",
        "keywords": ("호우", "폭우", "침수", "수해", "집중호우", "태풍"),
    },
    {
        "theme_slug": "amos_plumb_line",
        "theme_ko": "수평·질서 은유",
        "anchor_ref": "아모스 7:8",
        "keywords": ("지방선거", "선거", "투표", "정치", "부정"),
    },
    {
        "theme_slug": "babel_tower",
        "theme_ko": "바벨·혼란 은유",
        "anchor_ref": "창세기 11:7",
        "keywords": ("교통사고", "추돌", "충돌", "붕괴", "사고", "마비"),
    },
    {
        "theme_slug": "hosea_redemption",
        "theme_ko": "구속·회복 은유",
        "anchor_ref": "호세아 3:1",
        "keywords": ("구조", "복구", "지원", "피해", "복구예산"),
    },
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_as_of_date(cell: str) -> date | None:
    s = str(cell or "").strip()
    if not s:
        return None
    try:
        if "T" in s:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
            obj = json.loads(line)
            if isinstance(obj, dict) and obj.get("schema_version") == "news_observation_v1":
                rows.append(obj)
    return rows


def _match_themes(text: str) -> list[str]:
    hits: list[str] = []
    for rule in THEME_RULES:
        for kw in rule["keywords"]:
            if kw in text:
                hits.append(str(rule["theme_slug"]))
                break
    return hits


def _lag_pick(
    rows: list[dict[str, Any]],
    target: date,
    *,
    lag_days: int,
) -> list[dict[str, Any]]:
    start = target - timedelta(days=lag_days)
    end = target - timedelta(days=1)
    out: list[dict[str, Any]] = []
    for r in rows:
        pd = _parse_as_of_date(str(r.get("as_of_utc") or r.get("published_utc") or ""))
        if pd is None:
            continue
        if start <= pd <= end:
            out.append(r)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--news-jsonl", type=Path, default=DEFAULT_NEWS_JSONL)
    ap.add_argument("--date-from", default="2026-06-01")
    ap.add_argument("--date-to", default="2026-06-30")
    ap.add_argument("--lag-days", type=int, default=7)
    ap.add_argument("--source-prefix", default="korea_disaster_", help="Filter source_id prefix")
    ap.add_argument("-o", "--out-json", type=Path, default=DEFAULT_OUT)
    ns = ap.parse_args()

    all_rows = _load_jsonl(ns.news_jsonl)
    if ns.source_prefix:
        all_rows = [r for r in all_rows if str(r.get("source_id") or "").startswith(ns.source_prefix)]

    d0 = date.fromisoformat(ns.date_from)
    d1 = date.fromisoformat(ns.date_to)
    days_out: list[dict[str, Any]] = []

    d = d0
    while d <= d1:
        picked = _lag_pick(all_rows, d, lag_days=ns.lag_days)
        by_theme: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in picked:
            text = str(row.get("canonical_text") or "")
            for slug in _match_themes(text):
                by_theme[slug].append(
                    {
                        "observation_id": str(row.get("observation_id") or ""),
                        "snippet": text[:200],
                        "source_id": str(row.get("source_id") or ""),
                    }
                )

        theme_rows: list[dict[str, Any]] = []
        for rule in THEME_RULES:
            slug = str(rule["theme_slug"])
            samples = by_theme.get(slug, [])
            if not samples:
                continue
            theme_rows.append(
                {
                    "theme_slug": slug,
                    "theme_ko": rule["theme_ko"],
                    "anchor_ref": rule["anchor_ref"],
                    "hit_count": len(samples),
                    "samples": samples[:5],
                    "non_gating": True,
                }
            )

        days_out.append(
            {
                "date": d.isoformat(),
                "lag_start": (d - timedelta(days=ns.lag_days)).isoformat(),
                "lag_end": (d - timedelta(days=1)).isoformat(),
                "article_count_lag": len(picked),
                "themes": theme_rows,
            }
        )
        d += timedelta(days=1)

    report = {
        "schema": "logos_news_theme_overlay_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "boundary_ack": True,
        "labels": ["HYPO", "NON_GATING", "research_only"],
        "track_wall": "no_track_a_auto_merge; logos_not_price_vote",
        "inputs": {
            "news_jsonl": str(ns.news_jsonl.resolve()),
            "source_prefix": ns.source_prefix,
            "lag_days": ns.lag_days,
        },
        "method": {
            "mapping": "keyword_to_logos_metaphor_slug",
            "anti_lookahead": "excludes observations on target calendar day D",
        },
        "summary": {
            "n_days": len(days_out),
            "days_with_themes": sum(1 for x in days_out if x.get("themes")),
            "total_theme_hits": sum(
                sum(t.get("hit_count", 0) for t in (x.get("themes") or [])) for x in days_out
            ),
        },
        "days": days_out,
    }

    ns.out_json.parent.mkdir(parents=True, exist_ok=True)
    ns.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(ns.out_json),
                "days_with_themes": report["summary"]["days_with_themes"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
