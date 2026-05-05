#!/usr/bin/env python3
"""Fetch external macro/news signals (FRED + NewsAPI) for B-track.

Outputs:
- docs/final/artifacts/external_macro_signals_latest.json
- docs/final/artifacts/external_news_feed_latest.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MACRO_OUT = ROOT / "docs/final/artifacts/external_macro_signals_latest.json"
DEFAULT_NEWS_OUT = ROOT / "docs/final/artifacts/external_news_feed_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _env(name: str, default: str = "") -> str:
    return str(__import__("os").environ.get(name, default)).strip()


def _request_json(url: str, *, headers: dict[str, str] | None = None, timeout: float = 15.0) -> dict[str, Any]:
    req = request.Request(url=url, method="GET", headers=dict(headers or {}))
    with request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise RuntimeError("unexpected response shape")
    return obj


def _fred_latest_pair(api_key: str, series_id: str) -> tuple[float | None, float | None]:
    q = parse.urlencode(
        {
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 10,
        }
    )
    doc = _request_json(f"https://api.stlouisfed.org/fred/series/observations?{q}")
    obs = doc.get("observations")
    vals: list[float] = []
    if isinstance(obs, list):
        for row in obs:
            if not isinstance(row, dict):
                continue
            v = str(row.get("value") or "").strip()
            if not v or v == ".":
                continue
            try:
                vals.append(float(v))
            except ValueError:
                continue
            if len(vals) >= 2:
                break
    if len(vals) < 2:
        return (vals[0], None) if vals else (None, None)
    return vals[0], vals[1]


def _macro_doc(rows: list[dict[str, Any]]) -> dict[str, Any]:
    score = 0.0
    for r in rows:
        sid = str(r.get("series_id") or "")
        latest = r.get("latest")
        prev = r.get("prev")
        if not isinstance(latest, (int, float)) or not isinstance(prev, (int, float)):
            continue
        delta = float(latest) - float(prev)
        if sid in {"DFF", "FEDFUNDS"}:
            # rates up -> risk-off bias
            score -= delta
        else:
            score += delta
    trend = "flat"
    if score > 0.05:
        trend = "up"
    elif score < -0.05:
        trend = "down"
    return {
        "schema": "external_macro_signals_v1",
        "ts_utc": _utc_now(),
        "fred_series": rows,
        "macro_trend": {"trend": trend, "score": round(score, 6)},
        "boundary_ack": True,
        "hypothesis_tier": "B",
        "note": "B-track external macro helper (FRED).",
    }


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def _news_doc(query: str, response: dict[str, Any], max_items: int) -> dict[str, Any]:
    arts = response.get("articles")
    data: list[dict[str, Any]] = []
    if isinstance(arts, list):
        for row in arts[:max_items]:
            if not isinstance(row, dict):
                continue
            title = _strip_html(str(row.get("title") or ""))
            desc = _strip_html(str(row.get("description") or ""))
            if not title and not desc:
                continue
            data.append(
                {
                    "source": "newsapi_v2_everything",
                    "query": query,
                    "title": title,
                    "description": desc,
                    "url": str(row.get("url") or "").strip(),
                    "published_at": str(row.get("publishedAt") or "").strip(),
                }
            )
    return {
        "schema": "external_news_feed_v1",
        "ts_utc": _utc_now(),
        "query": query,
        "items_count": len(data),
        "data": data,
        "boundary_ack": True,
        "note": "B-track external news helper (NewsAPI).",
    }


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fred-series", default="DFF,FEDFUNDS")
    ap.add_argument("--news-query", default="")
    ap.add_argument("--news-page-size", type=int, default=20)
    ap.add_argument("--macro-out", type=Path, default=DEFAULT_MACRO_OUT)
    ap.add_argument("--news-out", type=Path, default=DEFAULT_NEWS_OUT)
    ap.add_argument("--allow-cache-fallback", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    news_query = args.news_query.strip() or _env("MKM_NEWSAPI_QUERY", "global macro markets")
    fred_key = _env("FRED_API_KEY")
    news_key = _env("NEWSAPI_API_KEY")

    macro_rows: list[dict[str, Any]] = []
    if fred_key:
        for sid in [s.strip() for s in str(args.fred_series).split(",") if s.strip()]:
            try:
                latest, prev = _fred_latest_pair(fred_key, sid)
            except Exception:
                latest, prev = None, None
            macro_rows.append({"series_id": sid, "latest": latest, "prev": prev})

    news_resp: dict[str, Any] = {"articles": []}
    if news_key:
        q = parse.urlencode({"q": news_query, "sortBy": "publishedAt", "pageSize": int(max(1, min(args.news_page_size, 100)))})
        try:
            news_resp = _request_json(f"https://newsapi.org/v2/everything?{q}", headers={"X-Api-Key": news_key})
        except Exception as exc:
            if not args.allow_cache_fallback:
                print(f"ERROR: NewsAPI request failed: {exc}", file=sys.stderr)
                return 1

    macro_doc = _macro_doc(macro_rows)
    news_doc = _news_doc(news_query, news_resp, args.news_page_size)

    if not fred_key and not news_key and not args.allow_cache_fallback:
        print("ERROR: missing FRED_API_KEY and NEWSAPI_API_KEY", file=sys.stderr)
        return 2

    if args.dry_run:
        print(json.dumps({"macro_trend": macro_doc["macro_trend"], "news_count": news_doc["items_count"]}, ensure_ascii=False, indent=2))
        return 0

    for p, d in ((args.macro_out, macro_doc), (args.news_out, news_doc)):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {p.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
