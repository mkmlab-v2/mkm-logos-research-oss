#!/usr/bin/env python3
"""Headline NLP verify helpers for macro_news_shock hero slot [HYPO]."""

from __future__ import annotations

import json
import re
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
KST = ZoneInfo("Asia/Seoul")
DEFAULT_ARCHIVE = ROOT / "reports/pre_news_shadow_daily_archive_v1.jsonl"
DEFAULT_LATEST = ROOT / "docs/final/artifacts/pre_news_shadow_input_latest.json"

MACRO_SHOCK_EN = frozenset(
    "cpi fomc fed tariff sanction war crisis crash plunge shock inflation rate hike cut recession selloff".split()
)
MACRO_SHOCK_KO = frozenset("환율 금리 관세 지정학 긴축 인플레 쇼크 급락 급등 위기 전쟁 제재".split())
BEAR_KO = ("급락", "폭락", "쇼크", "위기")
BEAR_EN = ("crash", "plunge", "shock", "crisis", "selloff")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_merged_pre_news_doc(
    *,
    latest_path: Path | None = None,
    archive_path: Path | None = None,
) -> dict[str, Any]:
    """Merge latest snapshot + daily archive JSONL for headline session lookup."""
    latest_p = latest_path or DEFAULT_LATEST
    archive_p = archive_path or DEFAULT_ARCHIVE
    latest = _read_json(latest_p)
    merged: dict[tuple[str, str, str], dict[str, Any]] = {}

    def _ingest(row: dict[str, Any]) -> None:
        if not isinstance(row, dict):
            return
        key = (
            str(row.get("row_id") or ""),
            str(row.get("pub_date") or ""),
            str(row.get("headline") or row.get("title") or ""),
        )
        merged[key] = row

    for row in latest.get("rows") or []:
        _ingest(row)
    if archive_p.is_file():
        for line in archive_p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            doc = json.loads(line)
            inner = doc.get("row") if isinstance(doc.get("row"), dict) else doc
            _ingest(inner)

    return {
        "schema": "pre_news_shadow_merged_v1",
        "generated_at_utc": latest.get("generated_at_utc"),
        "research_only": True,
        "sources": {
            "latest": str(latest_p).replace("\\", "/"),
            "archive": str(archive_p).replace("\\", "/"),
        },
        "n_rows": len(merged),
        "rows": list(merged.values()),
    }


def pub_date_to_kst_date(pub_date: str) -> str | None:
    raw = (pub_date or "").strip()
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            from datetime import timezone

            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(KST).strftime("%Y-%m-%d")
    except (TypeError, ValueError, IndexError):
        m = re.search(r"(\d{4}-\d{2}-\d{2})", raw)
        return m.group(1) if m else None


def headlines_for_session(pre_news_doc: dict[str, Any], session_date: str) -> list[str]:
    rows = pre_news_doc.get("rows") if isinstance(pre_news_doc.get("rows"), list) else []
    out: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        dk = pub_date_to_kst_date(str(row.get("pub_date") or ""))
        if dk != session_date:
            continue
        h = str(row.get("headline") or row.get("title") or "").strip()
        if h:
            out.append(h)
    return out


def score_headlines(headlines: list[str]) -> dict[str, Any]:
    macro_hits = 0
    bear_hits = 0
    bull_hits = 0
    for h in headlines:
        h_low = h.lower()
        tok = set(re.findall(r"[a-z0-9]+", h_low))
        if any(k in h_low for k in MACRO_SHOCK_KO) or any(k in tok for k in MACRO_SHOCK_EN):
            macro_hits += 1
        if any(w in h_low for w in BEAR_KO) or any(w in tok for w in BEAR_EN):
            bear_hits += 1
        if any(w in h_low for w in ("반등", "상승", "랠리", "rally", "surge", "rebound")):
            bull_hits += 1
    shock_score = min(1.0, 0.12 * macro_hits + 0.15 * bear_hits - 0.05 * bull_hits)
    return {
        "n_headlines": len(headlines),
        "macro_keyword_hits": macro_hits,
        "bear_keyword_hits": bear_hits,
        "bull_keyword_hits": bull_hits,
        "headline_shock_score": round(shock_score, 4),
    }


def headline_gt_for_session(
    pre_news_doc: dict[str, Any],
    session_date: str,
    *,
    min_macro_hits: int = 1,
    min_bear_hits: int = 1,
    shock_score_threshold: float = 0.35,
) -> dict[str, Any]:
    headlines = headlines_for_session(pre_news_doc, session_date)
    if not headlines:
        return {
            "headline_scorable": False,
            "reason": "no_headlines_for_session_date",
            "session_date": session_date,
        }
    scored = score_headlines(headlines)
    shock_binary = (
        scored["macro_keyword_hits"] >= min_macro_hits
        or scored["bear_keyword_hits"] >= min_bear_hits
        or scored["headline_shock_score"] >= shock_score_threshold
    )
    return {
        "headline_scorable": True,
        "session_date": session_date,
        "actual_binary_headline": bool(shock_binary),
        "sample_headlines": headlines[:3],
        **scored,
        "thresholds": {
            "min_macro_hits": min_macro_hits,
            "min_bear_hits": min_bear_hits,
            "shock_score_threshold": shock_score_threshold,
        },
    }


def build_headline_verify_board(
    pre_news_doc: dict[str, Any],
    session_dates: list[str],
    *,
    min_macro_hits: int = 1,
    min_bear_hits: int = 1,
    shock_score_threshold: float = 0.35,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for dk in session_dates:
        row = headline_gt_for_session(
            pre_news_doc,
            dk,
            min_macro_hits=min_macro_hits,
            min_bear_hits=min_bear_hits,
            shock_score_threshold=shock_score_threshold,
        )
        rows.append(row)
    scorable = [r for r in rows if r.get("headline_scorable")]
    shock_days = sum(1 for r in scorable if r.get("actual_binary_headline"))
    return {
        "schema": "btrack_macro_news_shock_headline_verify_v1",
        "n_sessions": len(session_dates),
        "n_headline_scorable": len(scorable),
        "n_headline_shock_days": shock_days,
        "rows": rows,
    }
