#!/usr/bin/env python3
"""Fetch Naver OpenAPI signals for B-track research artifacts.

Produces:
- docs/final/artifacts/naver_openapi_signals_latest.json
- docs/final/artifacts/naver_news_feed_latest.json

This script is research_only and does not connect to live trading actions.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SIGNALS_OUT = ROOT / "docs/final/artifacts/naver_openapi_signals_latest.json"
DEFAULT_NEWS_OUT = ROOT / "docs/final/artifacts/naver_news_feed_latest.json"
DEFAULT_PRE_NEWS_INPUT = ROOT / "docs/final/artifacts/pre_news_shadow_input_latest.json"
PREMARKET_CONFIG = ROOT / "data/commander/kospi_premarket_news_ingest_v1.json"
PRE_NEWS_SHADOW_CONFIG = ROOT / "data/commander/pre_news_shadow_naver_ingest_v1.json"


def _load_env() -> None:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return
    import os

    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        k = k.strip()
        if k and k not in os.environ:
            os.environ[k] = v.strip().strip('"').strip("'")


def _env(name: str, default: str = "") -> str:
    return str(__import__("os").environ.get(name, default)).strip()




def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _request_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    timeout: float = 15.0,
) -> dict[str, Any]:
    data = None
    req_headers = dict(headers or {})
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")
    req = request.Request(url=url, method=method, headers=req_headers, data=data)
    with request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise RuntimeError("unexpected response shape (non-dict)")
    return obj


def _strip_markup(text: str) -> str:
    # Naver search API wraps highlight tokens in <b> tags.
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


def load_news_ingest_profile(path: Path | None = None) -> dict[str, Any]:
    p = path or PREMARKET_CONFIG
    doc = _read_json(p)
    if not doc:
        return {}
    schema = str(doc.get("schema") or "")
    if schema in ("kospi_premarket_news_ingest_v1", "pre_news_shadow_naver_ingest_v1"):
        return doc
    return {}


def load_premarket_profile(path: Path | None = None) -> dict[str, Any]:
    p = path or PREMARKET_CONFIG
    doc = load_news_ingest_profile(p)
    if doc.get("schema") != "kospi_premarket_news_ingest_v1":
        return {}
    return doc


def _normalize_headline_key(title: str, link: str = "") -> str:
    t = re.sub(r"\s+", " ", (title or "").strip().lower())
    if link:
        return f"{t}|{link.strip().lower()}"
    return t


def merge_news_feed_items(
    batches: list[tuple[str, list[dict[str, Any]]]],
    *,
    max_items: int,
) -> list[dict[str, Any]]:
    """Dedupe merged Naver news rows by title+link; preserve first-seen query tag."""
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for query, items in batches:
        for item in items:
            title = str(item.get("title") or "").strip()
            link = str(item.get("link") or "").strip()
            if not title:
                continue
            key = _normalize_headline_key(title, link)
            if key in seen:
                continue
            seen.add(key)
            row = dict(item)
            row["query"] = query
            out.append(row)
            if len(out) >= max_items:
                return out
    return out


def _build_news_feed_doc(query: str, response: dict[str, Any], max_items: int) -> dict[str, Any]:
    items = response.get("items")
    normalized: list[dict[str, Any]] = []
    if isinstance(items, list):
        for item in items[:max_items]:
            if not isinstance(item, dict):
                continue
            title = _strip_markup(str(item.get("title") or ""))
            desc = _strip_markup(str(item.get("description") or ""))
            if not title and not desc:
                continue
            normalized.append(
                {
                    "source": "naver_news_search_api_v1",
                    "query": query,
                    "title": title,
                    "description": desc,
                    "link": str(item.get("originallink") or item.get("link") or "").strip(),
                    "pub_date": str(item.get("pubDate") or "").strip(),
                }
            )
    return {
        "schema": "naver_news_feed_v1",
        "ts_utc": _utc_now(),
        "query": query,
        "items_count": len(normalized),
        "data": normalized,
        "policy_scope": {
            "trading_primary_asset": "BTCUSDT",
            "kospi_role": "observation_only",
        },
        "boundary_ack": True,
        "note": "B-track research_only news feed from Naver Search OpenAPI.",
    }


def _build_merged_news_feed_doc(
    queries: list[str],
    merged_items: list[dict[str, Any]],
    *,
    profile_id: str | None = None,
) -> dict[str, Any]:
    return {
        "schema": "naver_news_feed_v1",
        "ts_utc": _utc_now(),
        "query": queries[0] if len(queries) == 1 else "merged",
        "queries": queries,
        "profile_id": profile_id,
        "items_count": len(merged_items),
        "data": merged_items,
        "policy_scope": {
            "trading_primary_asset": "KOSPI",
            "kospi_role": "premarket_observation",
        },
        "boundary_ack": True,
        "note": "Merged KOSPI premarket news feed (multi-query, deduped). research_only.",
    }


def _series_points_from_group(entry: dict[str, Any]) -> list[float]:
    out: list[float] = []
    data = entry.get("data")
    if not isinstance(data, list):
        return out
    for row in data:
        if not isinstance(row, dict):
            continue
        ratio = row.get("ratio")
        if isinstance(ratio, (int, float)):
            out.append(float(ratio))
    return out


def _compute_trend_summary(points: list[float]) -> dict[str, Any]:
    if not points:
        return {"n_points": 0, "trend": "unknown", "delta_last_first": 0.0, "mean": 0.0}
    first = points[0]
    last = points[-1]
    delta = last - first
    mean = sum(points) / float(len(points))
    trend = "flat"
    if delta > 3.0:
        trend = "up"
    elif delta < -3.0:
        trend = "down"
    return {
        "n_points": len(points),
        "trend": trend,
        "delta_last_first": round(delta, 6),
        "mean": round(mean, 6),
    }


def _parse_trend_weights(raw: str, keywords: list[str]) -> dict[str, float]:
    # Format: "비트코인=0.5,코스피=0.3,환율=0.2"
    parsed: dict[str, float] = {}
    for part in (raw or "").split(","):
        s = part.strip()
        if not s or "=" not in s:
            continue
        k, v = s.split("=", 1)
        key = k.strip()
        try:
            w = float(v.strip())
        except ValueError:
            continue
        if key and w >= 0.0:
            parsed[key] = w
    if not parsed:
        base = 1.0 / float(len(keywords))
        return {k: base for k in keywords}
    total = 0.0
    out: dict[str, float] = {}
    for k in keywords:
        w = float(parsed.get(k, 0.0))
        out[k] = w
        total += w
    if total <= 0:
        base = 1.0 / float(len(keywords))
        return {k: base for k in keywords}
    return {k: (v / total) for k, v in out.items()}


def _compute_weighted_group_summary(groups: list[dict[str, Any]]) -> dict[str, Any]:
    if not groups:
        return {"n_groups": 0, "trend": "unknown", "weighted_delta": 0.0, "weighted_mean": 0.0}
    w_delta = 0.0
    w_mean = 0.0
    n = 0
    for g in groups:
        try:
            w = float(g.get("weight") or 0.0)
            d = float(g.get("delta_last_first") or 0.0)
            m = float(g.get("mean") or 0.0)
        except (TypeError, ValueError):
            continue
        w_delta += w * d
        w_mean += w * m
        n += 1
    trend = "flat"
    if w_delta > 3.0:
        trend = "up"
    elif w_delta < -3.0:
        trend = "down"
    return {
        "n_groups": n,
        "trend": trend,
        "weighted_delta": round(w_delta, 6),
        "weighted_mean": round(w_mean, 6),
    }


def _build_signals_doc(
    trend_keywords: list[str],
    trend_weights: dict[str, float],
    datalab_resp: dict[str, Any],
    lookback_days: int,
) -> dict[str, Any]:
    results = datalab_resp.get("results")
    per_group: list[dict[str, Any]] = []
    all_points: list[float] = []
    if isinstance(results, list):
        for entry in results:
            if not isinstance(entry, dict):
                continue
            group_name = str(entry.get("title") or entry.get("groupName") or "").strip()
            if not group_name:
                continue
            pts = _series_points_from_group(entry)
            all_points.extend(pts)
            s = _compute_trend_summary(pts)
            per_group.append({"group": group_name, "weight": round(float(trend_weights.get(group_name, 0.0)), 6), **s})
    summary = _compute_trend_summary(all_points)
    weighted_summary = _compute_weighted_group_summary(per_group)
    return {
        "schema": "naver_openapi_signals_v1",
        "ts_utc": _utc_now(),
        "trend_keywords": trend_keywords,
        "trend_weights": {k: round(v, 6) for k, v in trend_weights.items()},
        "lookback_days": int(lookback_days),
        "policy_scope": {
            "trading_primary_asset": "BTCUSDT",
            "kospi_role": "observation_only",
        },
        "datalab_search_trend": summary,  # backwards compatibility
        "datalab_search_trend_weighted": weighted_summary,
        "datalab_search_trend_per_group": per_group,
        "boundary_ack": True,
        "hypothesis_tier": "B",
        "note": "Research-only macro/news auxiliary signal from Naver DataLab (multi-group).",
    }


def _build_trend_payload(keywords: list[str], lookback_days: int) -> dict[str, Any]:
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=max(lookback_days, 7))
    groups = [{"groupName": kw, "keywords": [kw]} for kw in keywords if kw]
    return {
        "startDate": start.strftime("%Y-%m-%d"),
        "endDate": end.strftime("%Y-%m-%d"),
        "timeUnit": "date",
        "keywordGroups": groups,
        "device": "",
        "ages": [],
        "gender": "",
    }


def _sync_pre_news_shadow_input(news_doc: dict[str, Any], out_path: Path) -> int:
    data = news_doc.get("data")
    if not isinstance(data, list) or not data:
        return 0
    ts_default = str(news_doc.get("ts_utc") or _utc_now())
    rows: list[dict[str, Any]] = []
    for i, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            continue
        headline = str(item.get("title") or "").strip()
        if not headline:
            continue
        rows.append(
            {
                "row_id": f"naver_{i:03d}",
                "timestamp_utc": ts_default,
                "source": str(item.get("source") or "naver_news_search_api_v1"),
                "headline": headline,
                "link": item.get("link"),
                "pub_date": item.get("pub_date"),
                "query": item.get("query") or news_doc.get("query"),
            }
        )
    if not rows:
        return 0
    ingest: dict[str, Any] = {
        "adapter": "fetch_naver_openapi_signals_v1",
        "naver_news_feed_schema": news_doc.get("schema"),
        "query": news_doc.get("query"),
        "items_count": news_doc.get("items_count"),
    }
    if news_doc.get("queries"):
        ingest["queries"] = news_doc.get("queries")
    if news_doc.get("profile_id"):
        ingest["profile_id"] = news_doc.get("profile_id")
    doc = {
        "schema": "pre_news_shadow_input_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "ingest": ingest,
        "rows": rows,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path.resolve()}")
    return len(rows)


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--news-query", default="")
    ap.add_argument(
        "--news-queries",
        default="",
        help="Comma-separated news queries (merged deduped feed). Overrides --news-query when set.",
    )
    ap.add_argument(
        "--profile",
        choices=("kospi_premarket", "pre_news_shadow"),
        default="",
        help="Load query/trend SSOT from commander ingest JSON (premarket or pre-news shadow).",
    )
    ap.add_argument("--premarket-config", type=Path, default=PREMARKET_CONFIG)
    ap.add_argument("--pre-news-config", type=Path, default=PRE_NEWS_SHADOW_CONFIG)
    ap.add_argument("--trend-keywords", default="")
    ap.add_argument("--trend-weights", default="")
    ap.add_argument("--lookback-days", type=int, default=30)
    ap.add_argument("--news-display", type=int, default=20)
    ap.add_argument("--client-id", default="")
    ap.add_argument("--client-secret", default="")
    ap.add_argument("--signals-out", type=Path, default=DEFAULT_SIGNALS_OUT)
    ap.add_argument("--news-out", type=Path, default=DEFAULT_NEWS_OUT)
    ap.add_argument("--allow-cache-fallback", action="store_true")
    ap.add_argument("--pre-news-input-out", type=Path, default=DEFAULT_PRE_NEWS_INPUT)
    ap.add_argument("--skip-pre-news-input-sync", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    _load_env()

    client_id = args.client_id.strip() or _env("NAVER_CLIENT_ID")
    client_secret = args.client_secret.strip() or _env("NAVER_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("ERROR: missing NAVER_CLIENT_ID / NAVER_CLIENT_SECRET", file=sys.stderr)
        return 2

    hdr = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }
    profile_doc: dict[str, Any] = {}
    if args.profile == "kospi_premarket":
        profile_doc = load_premarket_profile(args.premarket_config)
        if not profile_doc:
            print(f"ERROR: missing or invalid premarket config: {args.premarket_config}", file=sys.stderr)
            return 2
    elif args.profile == "pre_news_shadow":
        profile_doc = load_news_ingest_profile(args.pre_news_config)
        if not profile_doc:
            print(f"ERROR: missing or invalid pre-news config: {args.pre_news_config}", file=sys.stderr)
            return 2

    news_queries_raw = args.news_queries.strip()
    if not news_queries_raw and profile_doc:
        news_queries_raw = ",".join(str(q) for q in (profile_doc.get("news_queries") or []) if str(q).strip())
    news_queries = [q.strip() for q in news_queries_raw.split(",") if q.strip()]

    news_query = args.news_query.strip() or _env("MKM_NAVER_NEWS_QUERY", "비트코인")
    if news_queries:
        news_query = news_queries[0]

    trend_keywords_raw = args.trend_keywords.strip() or _env("MKM_NAVER_TREND_KEYWORDS", "비트코인,환율,코스피")
    trend_weights_raw = args.trend_weights.strip() or _env("MKM_NAVER_TREND_WEIGHTS", "비트코인=0.75,환율=0.15,코스피=0.10")
    if profile_doc:
        if profile_doc.get("trend_keywords"):
            trend_keywords_raw = ",".join(str(k) for k in profile_doc.get("trend_keywords") or [])
        if profile_doc.get("trend_weights"):
            trend_weights_raw = str(profile_doc.get("trend_weights"))
        if profile_doc.get("lookback_days"):
            args.lookback_days = int(profile_doc.get("lookback_days"))

    trend_keywords = [x.strip() for x in trend_keywords_raw.split(",") if x.strip()]
    if not trend_keywords:
        print("ERROR: at least one trend keyword is required", file=sys.stderr)
        return 2
    trend_weights = _parse_trend_weights(trend_weights_raw, trend_keywords)
    trend_payload = _build_trend_payload(trend_keywords, args.lookback_days)
    trend_url = "https://openapi.naver.com/v1/datalab/search"
    per_query_display = int(max(1, min(args.news_display, 100)))
    if profile_doc.get("news_display_per_query"):
        per_query_display = int(max(1, min(int(profile_doc["news_display_per_query"]), 100)))
    max_merged = int(profile_doc.get("max_merged_news_items") or 40) if profile_doc else per_query_display

    trend_resp: dict[str, Any] | None = None
    news_batches: list[tuple[str, list[dict[str, Any]]]] = []
    queries_to_fetch = news_queries if news_queries else [news_query]
    try:
        trend_resp = _request_json(trend_url, method="POST", headers=hdr, payload=trend_payload)
        for qtext in queries_to_fetch:
            q = parse.urlencode({"query": qtext, "display": per_query_display, "sort": "date"})
            news_url = f"https://openapi.naver.com/v1/search/news.json?{q}"
            news_resp = _request_json(news_url, method="GET", headers=hdr)
            partial = _build_news_feed_doc(qtext, news_resp or {"items": []}, per_query_display)
            data = partial.get("data") if isinstance(partial.get("data"), list) else []
            news_batches.append((qtext, [x for x in data if isinstance(x, dict)]))
    except (error.HTTPError, error.URLError, TimeoutError, json.JSONDecodeError, RuntimeError) as exc:
        if not args.allow_cache_fallback:
            print(f"ERROR: Naver API request failed: {exc}", file=sys.stderr)
            return 1
        cached_signals = _read_json(args.signals_out)
        cached_news = _read_json(args.news_out)
        if not cached_signals or not cached_news:
            print(f"ERROR: Naver API failed and no valid cache fallback: {exc}", file=sys.stderr)
            return 1
        trend_resp = {"results": []}
        cached_data = cached_news.get("data") if isinstance(cached_news.get("data"), list) else []
        news_batches = [(str(cached_news.get("query") or "cache"), [x for x in cached_data if isinstance(x, dict)])]

    signals_doc = _build_signals_doc(trend_keywords, trend_weights, trend_resp or {"results": []}, args.lookback_days)
    merged = merge_news_feed_items(
        news_batches,
        max_items=max_merged if (profile_doc or len(queries_to_fetch) > 1) else per_query_display,
    )
    if len(queries_to_fetch) > 1 or profile_doc:
        news_doc = _build_merged_news_feed_doc(
            queries_to_fetch,
            merged,
            profile_id=str(profile_doc.get("profile_id") or args.profile or "") or None,
        )
    else:
        news_doc = _build_news_feed_doc(queries_to_fetch[0], {"items": []}, per_query_display)
        news_doc["data"] = merged
        news_doc["items_count"] = len(merged)

    if args.dry_run:
        print(
            json.dumps(
                {
                    "signals": signals_doc.get("datalab_search_trend"),
                    "news_count": news_doc.get("items_count"),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    for path, doc in ((args.signals_out, signals_doc), (args.news_out, news_doc)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {path.resolve()}")
    if not args.skip_pre_news_input_sync and int(news_doc.get("items_count") or 0) > 0:
        _sync_pre_news_shadow_input(news_doc, args.pre_news_input_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
