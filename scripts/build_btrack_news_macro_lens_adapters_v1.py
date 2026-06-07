#!/usr/bin/env python3
"""Build news_independent_lens_latest.json + macro_independent_lens_latest.json for B-track bundle.

Reads optional shadow/feed artifacts and emits myeongni-shaped ``scores`` blocks so
``generate_btrack_hypothesis_prophecy_v1`` can set macro_available/news_available.

Deterministic keyword tilt (research_only, not a sentiment model).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRE_NEWS = ROOT / "docs/final/artifacts/pre_news_shadow_input_latest.json"
DEFAULT_EXTERNAL_FEED = ROOT / "docs/final/artifacts/external_feed_drop_latest.validated.json"
DEFAULT_EXTERNAL_FEED_FALLBACK = ROOT / "docs/final/artifacts/external_feed_drop_latest.json"
DEFAULT_NAVER_SIGNALS = ROOT / "docs/final/artifacts/naver_openapi_signals_latest.json"
DEFAULT_NAVER_NEWS_FEED = ROOT / "docs/final/artifacts/naver_news_feed_latest.json"
DEFAULT_EXTERNAL_MACRO_SIGNALS = ROOT / "docs/final/artifacts/external_macro_signals_latest.json"
DEFAULT_EXTERNAL_NEWS_FEED = ROOT / "docs/final/artifacts/external_news_feed_latest.json"
DEFAULT_BTC_MARKET_SIGNALS = ROOT / "docs/final/artifacts/btc_market_signals_latest.json"
DEFAULT_BTC_ALT_PUBLIC_SIGNALS = ROOT / "docs/final/artifacts/btc_alt_public_signals_latest.json"
DEFAULT_GLOBAL_OVERNIGHT = ROOT / "docs/final/artifacts/global_market_overnight_signals_v1_latest.json"
DEFAULT_EXA_NEWS_JSONL = ROOT / "reports/exa_macro_news_observation_staging_v1_latest.jsonl"
DEFAULT_NEWS_OUT = ROOT / "docs/final/artifacts/news_independent_lens_latest.json"
DEFAULT_MACRO_OUT = ROOT / "docs/final/artifacts/macro_independent_lens_latest.json"

BULL = frozenset(
    "rally surge gain up bull recovery expansion stabilize stabilization growth rebound "
    "support risk-on riskon breakthrough momentum".split()
)
BEAR = frozenset(
    "crisis crash down bear selloff fear tighten tightening slump recession loss "
    "risk-off riskoff stress shock decline plunge".split()
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _score_from_texts(texts: list[str]) -> tuple[float, float, dict[str, Any]]:
    if not texts:
        return 0.0, 0.0, {"reason": "no_text", "n": 0}
    raw = 0.0
    for t in texts:
        tok = _tokenize(t)
        raw += sum(1.0 for w in BULL if w in tok)
        raw -= sum(1.0 for w in BEAR if w in tok)
    n = len(texts)
    # Mild saturation so one headline cannot dominate unboundedly.
    direction = max(-1.0, min(1.0, raw / max(1.0, 2.0 * n)))
    confidence = min(1.0, 0.12 + 0.06 * min(n, 8))
    return direction, confidence, {"n_texts": n, "raw_tilt": raw}


def _headlines_from_pre_news(doc: dict[str, Any]) -> list[str]:
    rows = doc.get("rows") if isinstance(doc.get("rows"), list) else []
    out: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        h = str(row.get("headline") or row.get("title") or "").strip()
        if h:
            out.append(h)
    return out


def _strings_from_feed_item(item: Any, depth: int = 0) -> list[str]:
    if depth > 6:
        return []
    if isinstance(item, str):
        s = item.strip()
        return [s] if s else []
    if not isinstance(item, dict):
        return []
    keys = ("headline", "title", "summary", "text", "body", "description", "snippet", "content")
    acc: list[str] = []
    for k in keys:
        v = item.get(k)
        if isinstance(v, str) and v.strip():
            acc.append(v.strip())
    for v in item.values():
        acc.extend(_strings_from_feed_item(v, depth + 1))
    return acc


def _texts_from_external_feed(doc: dict[str, Any]) -> list[str]:
    data = doc.get("data")
    if not isinstance(data, list):
        return []
    texts: list[str] = []
    for it in data:
        texts.extend(_strings_from_feed_item(it))
    return texts


def _texts_from_naver_news_feed(doc: dict[str, Any]) -> list[str]:
    data = doc.get("data")
    if not isinstance(data, list):
        return []
    texts: list[str] = []
    for row in data:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or "").strip()
        desc = str(row.get("description") or "").strip()
        if title:
            texts.append(title)
        if desc:
            texts.append(desc)
    return texts


def _macro_seed_texts_from_naver_signals(doc: dict[str, Any]) -> list[str]:
    trend = doc.get("datalab_search_trend_weighted") if isinstance(doc.get("datalab_search_trend_weighted"), dict) else {}
    if not trend:
        trend = doc.get("datalab_search_trend") if isinstance(doc.get("datalab_search_trend"), dict) else {}
    if not isinstance(trend, dict):
        return []
    seeds: list[str] = []

    def _add_seed(tr: str) -> None:
        t = tr.strip().lower()
        if t == "up":
            seeds.append("growth momentum recovery")
        elif t == "down":
            seeds.append("risk-off decline stress")
        elif t == "flat":
            seeds.append("stabilization support")

    _add_seed(str(trend.get("trend") or ""))
    per_group = doc.get("datalab_search_trend_per_group")
    if isinstance(per_group, list):
        for row in per_group:
            if not isinstance(row, dict):
                continue
            try:
                w = float(row.get("weight") or 0.0)
            except (TypeError, ValueError):
                w = 0.0
            if w <= 0.0:
                continue
            _add_seed(str(row.get("trend") or ""))
    return seeds


def _macro_seed_texts_from_global_overnight(doc: dict[str, Any] | None) -> list[str]:
    if not doc or doc.get("schema") != "global_market_overnight_signals_v1":
        return []
    seeds: list[str] = []
    for row in doc.get("indices") or []:
        if not isinstance(row, dict):
            continue
        try:
            ch = float(row.get("change_pct") or 0.0)
        except (TypeError, ValueError):
            continue
        label = str(row.get("label_ko") or row.get("id") or "index")
        if ch <= -0.5:
            seeds.append(f"{label} overnight selloff decline risk-off stress")
        elif ch >= 0.5:
            seeds.append(f"{label} overnight rally gain momentum recovery")
        else:
            seeds.append(f"{label} stabilization flat consolidation")
    composite = str(doc.get("composite_tilt") or "")
    if composite == "risk_off_overnight":
        seeds.append("global risk-off selloff stress decline")
    elif composite == "risk_on_overnight":
        seeds.append("global rally risk-on momentum support")
    return seeds


def _news_headlines_from_global_overnight(doc: dict[str, Any] | None) -> list[str]:
    if not doc or doc.get("schema") != "global_market_overnight_signals_v1":
        return []
    out: list[str] = []
    for h in doc.get("news_headlines") or []:
        if isinstance(h, str) and h.strip():
            out.append(h.strip())
    return out


def _macro_seed_texts_from_external_macro(doc: dict[str, Any]) -> list[str]:
    trend = doc.get("macro_trend") if isinstance(doc.get("macro_trend"), dict) else {}
    t = str(trend.get("trend") or "").strip().lower()
    if t == "up":
        return ["growth expansion support"]
    if t == "down":
        return ["tightening risk-off stress"]
    if t == "flat":
        return ["stabilization"]
    return []


def _macro_seed_texts_from_btc_market(doc: dict[str, Any]) -> list[str]:
    trend = doc.get("market_micro_trend") if isinstance(doc.get("market_micro_trend"), dict) else {}
    t = str(trend.get("trend") or "").strip().lower()
    if t == "up":
        return ["btc momentum breakout support"]
    if t == "down":
        return ["btc crowding unwind risk-off"]
    if t == "flat":
        return ["btc consolidation stabilization"]
    return []


def _macro_seed_texts_from_btc_alt_public(doc: dict[str, Any]) -> list[str]:
    trend = doc.get("alt_public_trend") if isinstance(doc.get("alt_public_trend"), dict) else {}
    t = str(trend.get("trend") or "").strip().lower()
    if t == "up":
        return ["btc public momentum support"]
    if t == "down":
        return ["btc sentiment overheating unwind"]
    if t == "flat":
        return ["btc public sentiment neutral"]
    return []


def _texts_from_exa_news_jsonl(path: Path) -> list[str]:
    if not path.is_file():
        return []
    texts: list[str] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        t = str(row.get("canonical_text") or "").strip()
        if t:
            texts.append(t[:2000])
    return texts


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT))
    except ValueError:
        return str(p.resolve())


def _build_news_doc(
    pre_news_path: Path,
    pre_doc: dict[str, Any] | None,
    naver_news_path: Path,
    naver_news_doc: dict[str, Any] | None,
    external_news_path: Path,
    external_news_doc: dict[str, Any] | None,
    global_overnight_path: Path,
    global_overnight_doc: dict[str, Any] | None,
    exa_news_path: Path,
    exa_texts: list[str],
) -> dict[str, Any]:
    pre_texts = _headlines_from_pre_news(pre_doc) if pre_doc else []
    naver_texts = _texts_from_naver_news_feed(naver_news_doc) if naver_news_doc else []
    external_texts = _texts_from_naver_news_feed(external_news_doc) if external_news_doc else []
    overnight_texts = _news_headlines_from_global_overnight(global_overnight_doc)
    texts = pre_texts + naver_texts + external_texts + overnight_texts + exa_texts
    ds, cf, meta = _score_from_texts(texts)
    return {
        "schema": "news_independent_lens_v0",
        "version": "0.1.0",
        "lens_id": "news",
        "engine_id": "independent_lens_v0",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "policy_scope": {
            "trading_primary_asset": "BTCUSDT",
            "kospi_role": "observation_only",
        },
        "boundary_ack": True,
        "scores": {"direction_score": round(ds, 6), "confidence": round(cf, 6)},
        "news_stream_outputs": {
            "adapter": "build_btrack_news_macro_lens_adapters_v1",
            "headline_count": len(texts),
            "pre_news_headline_count": len(pre_texts),
            "naver_news_text_count": len(naver_texts),
            "external_news_text_count": len(external_texts),
            "global_overnight_headline_count": len(overnight_texts),
            "exa_macro_text_count": len(exa_texts),
            "digest": " | ".join(texts[:5])[:500],
            "tilt_meta": meta,
        },
        "provenance": {
            "source": "pre_news_shadow_input_adapter_v1",
            "input_path": _rel(pre_news_path) if pre_doc else "",
            "naver_news_input_path": _rel(naver_news_path) if naver_news_doc else "",
            "external_news_input_path": _rel(external_news_path) if external_news_doc else "",
            "global_overnight_input_path": _rel(global_overnight_path) if global_overnight_doc else "",
            "exa_news_jsonl_path": _rel(exa_news_path) if exa_texts else "",
        },
        "note": "B-track news lens from pre_news_shadow_input (keyword tilt); research_only; not live trading.",
    }


def _build_macro_doc(
    feed_path: Path,
    feed_doc: dict[str, Any] | None,
    naver_signals_path: Path,
    naver_signals_doc: dict[str, Any] | None,
    external_macro_path: Path,
    external_macro_doc: dict[str, Any] | None,
    btc_market_path: Path,
    btc_market_doc: dict[str, Any] | None,
    btc_alt_public_path: Path,
    btc_alt_public_doc: dict[str, Any] | None,
    global_overnight_path: Path,
    global_overnight_doc: dict[str, Any] | None,
    exa_news_path: Path,
    exa_texts: list[str],
) -> dict[str, Any]:
    feed_texts = _texts_from_external_feed(feed_doc) if feed_doc else []
    naver_seed_texts = _macro_seed_texts_from_naver_signals(naver_signals_doc) if naver_signals_doc else []
    external_macro_seed_texts = _macro_seed_texts_from_external_macro(external_macro_doc) if external_macro_doc else []
    btc_market_seed_texts = _macro_seed_texts_from_btc_market(btc_market_doc) if btc_market_doc else []
    btc_alt_public_seed_texts = _macro_seed_texts_from_btc_alt_public(btc_alt_public_doc) if btc_alt_public_doc else []
    overnight_seed_texts = _macro_seed_texts_from_global_overnight(global_overnight_doc)
    texts = (
        feed_texts
        + naver_seed_texts
        + external_macro_seed_texts
        + btc_market_seed_texts
        + btc_alt_public_seed_texts
        + overnight_seed_texts
        + exa_texts
    )
    ds, cf, meta = _score_from_texts(texts)
    return {
        "schema": "macro_independent_lens_v0",
        "version": "0.1.0",
        "lens_id": "macro",
        "engine_id": "independent_lens_v0",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "policy_scope": {
            "trading_primary_asset": "BTCUSDT",
            "kospi_role": "observation_only",
        },
        "boundary_ack": True,
        "scores": {"direction_score": round(ds, 6), "confidence": round(cf, 6)},
        "macro_stream_outputs": {
            "adapter": "build_btrack_news_macro_lens_adapters_v1",
            "snippet_count": len(texts),
            "external_feed_text_count": len(feed_texts),
            "naver_signal_seed_count": len(naver_seed_texts),
            "external_macro_seed_count": len(external_macro_seed_texts),
            "btc_market_seed_count": len(btc_market_seed_texts),
            "btc_alt_public_seed_count": len(btc_alt_public_seed_texts),
            "global_overnight_seed_count": len(overnight_seed_texts),
            "exa_macro_text_count": len(exa_texts),
            "tilt_meta": meta,
        },
        "provenance": {
            "source": "external_feed_drop_adapter_v1",
            "input_path": _rel(feed_path) if feed_doc else "",
            "items_count": int(feed_doc.get("items_count") or 0) if feed_doc else 0,
            "naver_signals_input_path": _rel(naver_signals_path) if naver_signals_doc else "",
            "external_macro_input_path": _rel(external_macro_path) if external_macro_doc else "",
            "btc_market_input_path": _rel(btc_market_path) if btc_market_doc else "",
            "btc_alt_public_input_path": _rel(btc_alt_public_path) if btc_alt_public_doc else "",
            "global_overnight_input_path": _rel(global_overnight_path) if global_overnight_doc else "",
            "exa_news_jsonl_path": _rel(exa_news_path) if exa_texts else "",
        },
        "note": "B-track macro lens from external_feed_drop (keyword tilt); research_only; not live trading.",
    }


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pre-news-input", type=Path, default=DEFAULT_PRE_NEWS)
    ap.add_argument("--external-feed", type=Path, default=DEFAULT_EXTERNAL_FEED)
    ap.add_argument("--naver-signals", type=Path, default=DEFAULT_NAVER_SIGNALS)
    ap.add_argument("--naver-news-feed", type=Path, default=DEFAULT_NAVER_NEWS_FEED)
    ap.add_argument("--external-macro-signals", type=Path, default=DEFAULT_EXTERNAL_MACRO_SIGNALS)
    ap.add_argument("--external-news-feed", type=Path, default=DEFAULT_EXTERNAL_NEWS_FEED)
    ap.add_argument("--btc-market-signals", type=Path, default=DEFAULT_BTC_MARKET_SIGNALS)
    ap.add_argument("--btc-alt-public-signals", type=Path, default=DEFAULT_BTC_ALT_PUBLIC_SIGNALS)
    ap.add_argument("--global-overnight", type=Path, default=DEFAULT_GLOBAL_OVERNIGHT)
    ap.add_argument("--exa-news-jsonl", type=Path, default=DEFAULT_EXA_NEWS_JSONL)
    ap.add_argument("--news-out", type=Path, default=DEFAULT_NEWS_OUT)
    ap.add_argument("--macro-out", type=Path, default=DEFAULT_MACRO_OUT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    pre_doc = _read_json(args.pre_news_input)
    feed_doc = _read_json(args.external_feed)
    if feed_doc is None and args.external_feed == DEFAULT_EXTERNAL_FEED:
        feed_doc = _read_json(DEFAULT_EXTERNAL_FEED_FALLBACK)
    naver_signals_doc = _read_json(args.naver_signals)
    naver_news_doc = _read_json(args.naver_news_feed)
    external_macro_doc = _read_json(args.external_macro_signals)
    external_news_doc = _read_json(args.external_news_feed)
    btc_market_doc = _read_json(args.btc_market_signals)
    btc_alt_public_doc = _read_json(args.btc_alt_public_signals)
    global_overnight_doc = _read_json(args.global_overnight)
    exa_texts = _texts_from_exa_news_jsonl(args.exa_news_jsonl)

    news_doc = _build_news_doc(
        args.pre_news_input,
        pre_doc,
        args.naver_news_feed,
        naver_news_doc,
        args.external_news_feed,
        external_news_doc,
        args.global_overnight,
        global_overnight_doc,
        args.exa_news_jsonl,
        exa_texts,
    )
    macro_doc = _build_macro_doc(
        args.external_feed,
        feed_doc,
        args.naver_signals,
        naver_signals_doc,
        args.external_macro_signals,
        external_macro_doc,
        args.btc_market_signals,
        btc_market_doc,
        args.btc_alt_public_signals,
        btc_alt_public_doc,
        args.global_overnight,
        global_overnight_doc,
        args.exa_news_jsonl,
        exa_texts,
    )

    if args.dry_run:
        print(json.dumps({"news": news_doc["scores"], "macro": macro_doc["scores"]}, indent=2))
        return 0

    for path, doc in ((args.news_out, news_doc), (args.macro_out, macro_doc)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
