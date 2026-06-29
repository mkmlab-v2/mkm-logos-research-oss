#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Resolve balanced KOSPI premarket news queries from SSOT + context [HYPO]."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "data/commander/kospi_premarket_news_ingest_v1.json"
DEFAULT_OVERNIGHT = ROOT / "docs/final/artifacts/global_market_overnight_signals_v1_latest.json"
DEFAULT_KOSPI_CSV = ROOT / "research/market_data/kospi_daily_external_yf.csv"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return doc if isinstance(doc, dict) else {}


def _last_kospi_return_pct(csv_path: Path) -> float | None:
    if not csv_path.is_file():
        return None
    lines = [ln.strip() for ln in csv_path.read_text(encoding="utf-8-sig").splitlines() if ln.strip()]
    if len(lines) < 3:
        return None
    try:
        c1 = float(lines[-1].split(",")[4])
        c0 = float(lines[-2].split(",")[4])
    except (IndexError, ValueError):
        return None
    if c0 == 0:
        return None
    return (c1 / c0 - 1.0) * 100.0


def _overnight_tilt(path: Path) -> str:
    doc = _read_json(path)
    return str(doc.get("composite_tilt") or "neutral")


def _dedupe_queries(queries: list[str], *, cap: int) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for q in queries:
        s = str(q).strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
        if len(out) >= cap:
            break
    return out


def _rotational_pick(pool: list[str], *, as_of: date, pick_count: int) -> list[str]:
    if not pool or pick_count <= 0:
        return []
    start = (as_of.toordinal() + as_of.weekday()) % len(pool)
    picked: list[str] = []
    for i in range(min(pick_count, len(pool))):
        picked.append(pool[(start + i) % len(pool)])
    return picked


def resolve_premarket_news_queries(
    config: dict[str, Any],
    *,
    as_of: date | None = None,
    overnight_path: Path | None = None,
    kospi_csv: Path | None = None,
) -> dict[str, Any]:
    """Return resolved query plan for Naver + Exa (research_only)."""
    today = as_of or date.today()
    base = [str(q) for q in (config.get("news_queries") or []) if str(q).strip()]
    rotational = [str(q) for q in (config.get("rotational_boost_queries") or []) if str(q).strip()]
    pick_n = int(config.get("rotational_pick_count") or 2)
    max_q = int(config.get("max_distinct_news_queries") or 10)

    rot_picked = _rotational_pick(rotational, as_of=today, pick_count=pick_n)

    contextual: list[str] = []
    tilt = _overnight_tilt(overnight_path or DEFAULT_OVERNIGHT)
    kospi_ret = _last_kospi_return_pct(kospi_csv or DEFAULT_KOSPI_CSV)

    if tilt in ("risk_off_overnight", "risk_off"):
        contextual.extend(str(q) for q in (config.get("context_risk_off_boost") or []) if str(q).strip())
    if kospi_ret is not None and kospi_ret <= float(config.get("context_kospi_shock_threshold_pct") or -2.5):
        contextual.extend(str(q) for q in (config.get("context_kospi_shock_boost") or []) if str(q).strip())

    merged = _dedupe_queries(base + rot_picked + contextual, cap=max_q)
    exa_base = [str(q) for q in (config.get("exa_queries") or []) if str(q).strip()]
    exa_ctx: list[str] = []
    if tilt in ("risk_off_overnight", "risk_off"):
        exa_ctx.extend(str(q) for q in (config.get("exa_risk_off_boost") or []) if str(q).strip())

    return {
        "schema": "kospi_premarket_dynamic_query_plan_v1",
        "as_of_kst": today.isoformat(),
        "weekday_ko": ["월", "화", "수", "목", "금", "토", "일"][today.weekday()],
        "news_queries_resolved": merged,
        "exa_queries_resolved": _dedupe_queries(exa_base + exa_ctx, cap=int(config.get("max_exa_queries") or 4)),
        "context": {
            "overnight_composite_tilt": tilt,
            "kospi_last_daily_return_pct": round(kospi_ret, 4) if kospi_ret is not None else None,
            "rotational_picked": rot_picked,
            "contextual_boost": contextual,
        },
        "caps": {"max_distinct_news_queries": max_q, "rotational_pick_count": pick_n},
    }


def load_config(path: Path | None = None) -> dict[str, Any]:
    p = path or DEFAULT_CONFIG
    doc = _read_json(p)
    if doc.get("schema") != "kospi_premarket_news_ingest_v1":
        return {}
    return doc
