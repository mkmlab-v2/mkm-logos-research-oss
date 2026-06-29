#!/usr/bin/env python3
"""Build 7-day lag disaster-news context features for Korea B-track fusion (no lookahead).

Uses Naver Search News API when NAVER_CLIENT_ID/SECRET are set, or **Exa** (`EXA_API_KEY`,
``--use-exa``) when Naver is empty/401. Articles with pubDate in (D-lag_days .. D-1) only —
**excludes same-day headlines** for anti-leakage.

Outputs daily CSV keyed by date for join with myeongni fusion pipeline.

research_only · B-track only.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib import error, parse, request

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
DEFAULT_OUT = ROOT / "reports/korea_disaster_news_context_v1.csv"

FIRE_KW = ("산불", "산림화재", "화재", "방화", "건조", "폭염", "가뭄", "불조심")
FLOOD_KW = ("호우", "폭우", "침수", "수해", "집중호우", "태풍", "폭풍", "강우")
TRAFFIC_KW = ("교통사고", "추돌", "충돌", "안전사고", "산업재해", "붕괴", "사고")
POLITICS_KW = ("지방선거", "선거", "투표", "정치")

DEFAULT_QUERIES = (
    "산불",
    "산림화재",
    "폭염",
    "호우 침수",
    "교통사고",
    "지방선거",
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    if ENV_PATH.is_file():
        load_dotenv(ENV_PATH, override=False)


def _env(name: str, default: str = "") -> str:
    import os

    return str(os.environ.get(name, default)).strip()


def _request_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    timeout: float = 20.0,
) -> dict[str, Any]:
    data = None
    hdr = dict(headers or {})
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        hdr.setdefault("Content-Type", "application/json")
    req = request.Request(url=url, data=data, method=method, headers=hdr)
    with request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise RuntimeError("unexpected json shape")
    return obj


def _parse_pub_date(cell: str) -> date | None:
    s = str(cell or "").strip()
    if not s:
        return None
    try:
        if re.match(r"^\d{4}-\d{2}-\d{2}", s):
            return date.fromisoformat(s[:10])
        dt = parsedate_to_datetime(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).date()
    except (ValueError, TypeError, OverflowError):
        return None


def _score_text(text: str, keywords: tuple[str, ...]) -> int:
    t = text.lower()
    # Korean: case insensitive less relevant; substring match
    n = 0
    for kw in keywords:
        if kw in text or kw.lower() in t:
            n += 1
    return n


def _fetch_naver_news(query: str, *, display: int, hdr: dict[str, str]) -> list[dict[str, str]]:
    q = parse.urlencode({"query": query, "display": display, "sort": "date"})
    url = f"https://openapi.naver.com/v1/search/news.json?{q}"
    doc = _request_json(url, method="GET", headers=hdr)
    items = doc.get("items") or []
    rows: list[dict[str, str]] = []
    if not isinstance(items, list):
        return rows
    for it in items:
        if not isinstance(it, dict):
            continue
        title = re.sub(r"<[^>]+>", "", str(it.get("title") or ""))
        desc = re.sub(r"<[^>]+>", "", str(it.get("description") or ""))
        rows.append(
            {
                "query": query,
                "title": title,
                "description": desc,
                "pubDate": str(it.get("pubDate") or ""),
                "link": str(it.get("link") or ""),
            }
        )
    return rows


def _parse_iso_date(cell: str) -> date | None:
    s = str(cell or "").strip()
    if not s:
        return None
    try:
        if "T" in s:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
        return date.fromisoformat(s[:10])
    except (ValueError, TypeError):
        return None


def _article_from_text(
    *,
    pub: date,
    query: str,
    title: str,
    text: str,
    link: str,
) -> dict[str, Any]:
    blob = f"{title} {text}"
    return {
        "pub_date": pub.isoformat(),
        "query": query,
        "title": title,
        "link": link,
        "source_api": "exa",
        "fire_hits": _score_text(blob, FIRE_KW),
        "flood_hits": _score_text(blob, FLOOD_KW),
        "traffic_hits": _score_text(blob, TRAFFIC_KW),
        "politics_hits": _score_text(blob, POLITICS_KW),
    }


def _exa_search_batch(
    query: str,
    *,
    pool_start: date,
    pool_end: date,
    num_results: int,
    api_key: str,
) -> list[dict[str, Any]]:
    payload = {
        "query": f"한국 {query} 뉴스",
        "numResults": num_results,
        "startPublishedDate": f"{pool_start.isoformat()}T00:00:00.000Z",
        "endPublishedDate": f"{pool_end.isoformat()}T23:59:59.999Z",
        "contents": {"text": {"maxCharacters": 700}},
    }
    req = request.Request(
        url="https://api.exa.ai/search",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "x-api-key": api_key,
            "Content-Type": "application/json",
        },
    )
    with request.urlopen(req, timeout=45.0) as resp:
        doc = json.loads(resp.read().decode("utf-8"))
    rows: list[dict[str, Any]] = []
    for it in doc.get("results") or []:
        if not isinstance(it, dict):
            continue
        pd = _parse_iso_date(str(it.get("publishedDate") or it.get("published_date") or ""))
        if pd is None:
            continue
        if pd < pool_start or pd > pool_end:
            continue
        title = str(it.get("title") or "")
        text = str((it.get("text") or "") or "")
        link = str(it.get("url") or "")
        rows.append(
            _article_from_text(pub=pd, query=query, title=title, text=text, link=link)
        )
    return rows


def _collect_exa_articles(
    queries: list[str],
    *,
    pool_start: date,
    pool_end: date,
    num_per_query: int,
    api_key: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    all_rows: list[dict[str, Any]] = []
    warns: list[str] = []
    seen: set[str] = set()
    for q in queries:
        try:
            batch = _exa_search_batch(
                q,
                pool_start=pool_start,
                pool_end=pool_end,
                num_results=num_per_query,
                api_key=api_key,
            )
        except (error.HTTPError, error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
            warns.append(f"exa_query_fail:{q}:{e}")
            continue
        for row in batch:
            key = (row.get("link") or "") + "|" + (row.get("title") or "")[:80]
            if key in seen:
                continue
            seen.add(key)
            all_rows.append(row)
    return all_rows, warns


def _collect_articles(
    queries: list[str],
    *,
    display_per_query: int,
    hdr: dict[str, str],
) -> tuple[list[dict[str, Any]], list[str]]:
    all_rows: list[dict[str, Any]] = []
    warns: list[str] = []
    seen: set[str] = set()
    for q in queries:
        try:
            batch = _fetch_naver_news(q, display=display_per_query, hdr=hdr)
        except error.HTTPError as e:
            if e.code == 401:
                warns.append("naver_http_401_unauthorized:refresh_NAVER_CLIENT_ID_SECRET_in_.env")
            warns.append(f"naver_query_fail:{q}:{e}")
            continue
        except (error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
            warns.append(f"naver_query_fail:{q}:{e}")
            continue
        for row in batch:
            key = (row.get("link") or "") + "|" + (row.get("title") or "")[:80]
            if key in seen:
                continue
            seen.add(key)
            pd = _parse_pub_date(row.get("pubDate", ""))
            if pd is None:
                continue
            text = f"{row.get('title','')} {row.get('description','')}"
            all_rows.append(
                {
                    "pub_date": pd.isoformat(),
                    "query": q,
                    "title": row.get("title", ""),
                    "link": row.get("link", ""),
                    "source_api": "naver",
                    "fire_hits": _score_text(text, FIRE_KW),
                    "flood_hits": _score_text(text, FLOOD_KW),
                    "traffic_hits": _score_text(text, TRAFFIC_KW),
                    "politics_hits": _score_text(text, POLITICS_KW),
                }
            )
    return all_rows, warns


def _merge_article_pools(
    *pools: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for pool in pools:
        for a in pool:
            key = (str(a.get("link") or "")) + "|" + (str(a.get("title") or ""))[:80]
            if not key.strip("|") or key in seen:
                continue
            seen.add(key)
            out.append(a)
    return out


def _lag_features(
    articles: list[dict[str, Any]],
    target: date,
    *,
    lag_days: int,
) -> dict[str, Any]:
    start = target - timedelta(days=lag_days)
    end = target - timedelta(days=1)
    if end < start:
        end = start
    picked = [
        a
        for a in articles
        if start <= date.fromisoformat(str(a["pub_date"])) <= end
    ]
    fire = sum(int(a.get("fire_hits") or 0) for a in picked)
    flood = sum(int(a.get("flood_hits") or 0) for a in picked)
    traffic = sum(int(a.get("traffic_hits") or 0) for a in picked)
    politics = sum(int(a.get("politics_hits") or 0) for a in picked)
    n = len(picked)

    def _norm(x: float) -> float:
        if n == 0:
            return 0.0
        return round(min(1.0, x / max(3.0, n * 2.0)), 4)

    return {
        "lag_start": start.isoformat(),
        "lag_end": end.isoformat(),
        "article_count_lag": n,
        "news_fire_score_7d": _norm(fire),
        "news_flood_score_7d": _norm(flood),
        "news_traffic_score_7d": _norm(traffic),
        "news_politics_score_7d": _norm(politics),
    }


def _static_calendar_boost(target: date) -> dict[str, float]:
    """Public calendar facts (no news API) — low weight prior."""
    boosts = {"news_fire_score_7d": 0.0, "news_flood_score_7d": 0.0, "news_traffic_score_7d": 0.0, "news_politics_score_7d": 0.0}
    if target == date(2026, 6, 3):
        boosts["news_politics_score_7d"] = 0.35
        boosts["news_traffic_score_7d"] = 0.38  # 지방선거일·이동·집회 (static prior, lag-safe)
    if target == date(2026, 6, 4):
        boosts["news_traffic_score_7d"] = 0.36  # 선거 직후 교통·헤드라인 클러스터
    return boosts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date-from", default="2026-06-01")
    ap.add_argument("--date-to", default="2026-06-30")
    ap.add_argument("--lag-days", type=int, default=7)
    ap.add_argument("--display-per-query", type=int, default=50)
    ap.add_argument("--queries", default=",".join(DEFAULT_QUERIES))
    ap.add_argument("-o", "--out-csv", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--articles-json", type=Path, default=ROOT / "reports/korea_disaster_news_articles_v1.json")
    ap.add_argument("--skip-naver", action="store_true")
    ap.add_argument(
        "--use-exa",
        action="store_true",
        help="Also fetch via Exa REST (EXA_API_KEY). Default: auto when Naver yields 0 articles.",
    )
    ap.add_argument("--exa-only", action="store_true", help="Skip Naver; Exa + static calendar only.")
    ap.add_argument("--exa-per-query", type=int, default=25, help="Exa numResults per query.")
    ns = ap.parse_args()

    d0 = date.fromisoformat(ns.date_from)
    d1 = date.fromisoformat(ns.date_to)
    queries = [q.strip() for q in ns.queries.split(",") if q.strip()]
    pool_start = d0 - timedelta(days=ns.lag_days)
    pool_end = d1 - timedelta(days=1)

    _load_dotenv()
    client_id = _env("NAVER_CLIENT_ID")
    client_secret = _env("NAVER_CLIENT_SECRET")
    exa_key = _env("EXA_API_KEY")
    warns: list[str] = []
    naver_articles: list[dict[str, Any]] = []
    exa_articles: list[dict[str, Any]] = []
    source = "static_calendar_only"

    if not ns.exa_only and not ns.skip_naver and client_id and client_secret:
        hdr = {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
        naver_articles, nw = _collect_articles(
            queries, display_per_query=ns.display_per_query, hdr=hdr
        )
        warns.extend(nw)
    else:
        warns.append("naver_skipped_or_missing_credentials")

    use_exa = ns.use_exa or ns.exa_only or (not naver_articles and bool(exa_key))
    if use_exa and exa_key:
        exa_articles, ew = _collect_exa_articles(
            queries,
            pool_start=pool_start,
            pool_end=pool_end,
            num_per_query=ns.exa_per_query,
            api_key=exa_key,
        )
        warns.extend(ew)
    elif use_exa and not exa_key:
        warns.append("exa_requested_but_EXA_API_KEY_missing")

    articles = _merge_article_pools(naver_articles, exa_articles)
    if exa_articles and naver_articles:
        source = "naver_exa_merged_lag7"
    elif exa_articles:
        source = "exa_news_lag7"
    elif naver_articles:
        source = "naver_news_lag7"
    elif not articles:
        source = "empty_fallback_static"

    if ns.articles_json:
        ns.articles_json.parent.mkdir(parents=True, exist_ok=True)
        ns.articles_json.write_text(
            json.dumps(
                {
                    "schema": "korea_disaster_news_articles_v1",
                    "generated_at_utc": _utc(),
                    "n_articles": len(articles),
                    "warnings": warns,
                    "articles": articles[:500],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    rows_out: list[dict[str, str]] = []
    d = d0
    while d <= d1:
        feat = _lag_features(articles, d, lag_days=ns.lag_days)
        static = _static_calendar_boost(d)
        for k, v in static.items():
            feat[k] = round(min(1.0, float(feat.get(k, 0)) + v), 4)
        row = {"date": d.isoformat(), "news_source": source, **{k: str(v) for k, v in feat.items()}}
        rows_out.append(row)
        d += timedelta(days=1)

    headers = list(rows_out[0].keys()) if rows_out else ["date"]
    ns.out_csv.parent.mkdir(parents=True, exist_ok=True)
    with ns.out_csv.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(rows_out)

    meta = ns.out_csv.with_suffix(".meta.json")
    meta.write_text(
        json.dumps(
            {
                "schema": "korea_disaster_news_context_meta_v1",
                "generated_at_utc": _utc(),
                "lag_days": ns.lag_days,
                "anti_lookahead": "excludes pubDate on target day D",
                "article_pool_start": pool_start.isoformat(),
                "article_pool_end": pool_end.isoformat(),
                "queries": queries,
                "n_articles_naver": len(naver_articles),
                "n_articles_exa": len(exa_articles),
                "n_articles_pool": len(articles),
                "warnings": warns,
                "out_csv": str(ns.out_csv.resolve()),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {"ok": True, "rows": len(rows_out), "csv": str(ns.out_csv), "articles": len(articles), "warnings": len(warns)},
            ensure_ascii=False,
        )
    )
    return 0 if rows_out else 2


if __name__ == "__main__":
    raise SystemExit(main())
