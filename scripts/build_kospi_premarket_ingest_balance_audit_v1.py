#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Balance audit for KOSPI premarket ingest — headline mix + lens tilt [HYPO]."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/kospi_premarket_ingest_balance_audit_v1_latest.json"
ART = ROOT / "docs/final/artifacts/kospi_premarket_ingest_balance_audit_v1_latest.json"

BUCKETS: list[tuple[str, frozenset[str]]] = [
    ("kospi_domestic", frozenset(["코스피", "코스닥", "한국", "삼성", "하이닉스", "kospi"])),
    ("us_markets", frozenset(["뉴욕", "나스닥", "다우", "s&p", "fed", "연준", "미국 증시"])),
    ("fx_rates", frozenset(["환율", "원달러", "달러", "금리", "채권"])),
    ("geopolitics", frozenset(["중동", "전쟁", "지정학", "제재", "tariff", "관세"])),
    ("ai_semis", frozenset(["ai", "반도체", "메모리", "hbm", "마이크론", "인텔", "nvidia", "오픈ai"])),
    ("other", frozenset()),
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return doc if isinstance(doc, dict) else {}


def _bucketize_headline(text: str) -> str:
    low = text.lower()
    for name, keys in BUCKETS:
        if name == "other":
            continue
        if any(k in low for k in keys):
            return name
    return "other"


def _entropy(counts: Counter[str]) -> float:
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    ent = 0.0
    for c in counts.values():
        p = c / total
        if p > 0:
            ent -= p * math.log2(p)
    return round(ent, 4)


def build_audit(
    *,
    pre_news_path: Path,
    news_lens_path: Path,
    macro_lens_path: Path,
    overnight_path: Path,
    query_plan_path: Path | None = None,
) -> dict[str, Any]:
    pre = _read_json(pre_news_path)
    rows = pre.get("rows") if isinstance(pre.get("rows"), list) else []
    headlines = [str(r.get("headline") or "") for r in rows if isinstance(r, dict)]
    by_query = Counter(str(r.get("query") or "unknown") for r in rows if isinstance(r, dict))
    by_bucket = Counter(_bucketize_headline(h) for h in headlines if h.strip())

    news_lens = _read_json(news_lens_path)
    macro_lens = _read_json(macro_lens_path)
    overnight = _read_json(overnight_path)
    plan = _read_json(query_plan_path) if query_plan_path and query_plan_path.is_file() else {}

    n_buckets_hit = sum(1 for k, v in by_bucket.items() if k != "other" and v > 0)
    balance_score = round(min(1.0, _entropy(by_bucket) / math.log2(max(len(BUCKETS), 2))), 4)

    flags: list[str] = []
    if by_bucket.get("ai_semis", 0) == 0:
        flags.append("missing_ai_semis_bucket")
    if by_bucket.get("us_markets", 0) == 0:
        flags.append("missing_us_markets_bucket")
    if len(headlines) < 10:
        flags.append("low_headline_count")

    return {
        "schema": "kospi_premarket_ingest_balance_audit_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "headline_count": len(headlines),
        "by_query": dict(by_query),
        "by_topic_bucket": dict(by_bucket),
        "balance_entropy": _entropy(by_bucket),
        "balance_score_0_1": balance_score,
        "buckets_covered": n_buckets_hit,
        "quality_flags": flags,
        "lens_snapshot": {
            "news_direction_score": (news_lens.get("scores") or {}).get("direction_score"),
            "macro_direction_score": (macro_lens.get("scores") or {}).get("direction_score"),
            "overnight_composite_tilt": overnight.get("composite_tilt"),
            "session_anchor_date": overnight.get("session_anchor_date"),
        },
        "query_plan_pointer": str(query_plan_path) if query_plan_path else None,
        "resolved_queries": plan.get("news_queries_resolved"),
        "note_ko": "균형·커버리지 관측만 — active 표결·종목 목표가 아님",
        "reproduce": "py scripts/build_kospi_premarket_ingest_balance_audit_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pre-news", type=Path, default=ROOT / "docs/final/artifacts/pre_news_shadow_input_latest.json")
    ap.add_argument("--news-lens", type=Path, default=ROOT / "docs/final/artifacts/news_independent_lens_latest.json")
    ap.add_argument("--macro-lens", type=Path, default=ROOT / "docs/final/artifacts/macro_independent_lens_latest.json")
    ap.add_argument("--overnight", type=Path, default=ROOT / "docs/final/artifacts/global_market_overnight_signals_v1_latest.json")
    ap.add_argument("--query-plan", type=Path, default=ROOT / "reports/kospi_premarket_dynamic_query_plan_v1_latest.json")
    ap.add_argument("--output", type=Path, default=OUT)
    ns = ap.parse_args()

    doc = build_audit(
        pre_news_path=ns.pre_news,
        news_lens_path=ns.news_lens,
        macro_lens_path=ns.macro_lens,
        overnight_path=ns.overnight,
        query_plan_path=ns.query_plan,
    )
    ns.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ART.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "balance_score": doc["balance_score_0_1"], "flags": doc["quality_flags"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
