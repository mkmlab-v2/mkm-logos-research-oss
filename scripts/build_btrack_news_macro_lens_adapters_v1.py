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


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT))
    except ValueError:
        return str(p.resolve())


def _build_news_doc(pre_news_path: Path, pre_doc: dict[str, Any] | None) -> dict[str, Any]:
    texts = _headlines_from_pre_news(pre_doc) if pre_doc else []
    ds, cf, meta = _score_from_texts(texts)
    return {
        "schema": "news_independent_lens_v0",
        "version": "0.1.0",
        "lens_id": "news",
        "engine_id": "independent_lens_v0",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "scores": {"direction_score": round(ds, 6), "confidence": round(cf, 6)},
        "news_stream_outputs": {
            "adapter": "build_btrack_news_macro_lens_adapters_v1",
            "headline_count": len(texts),
            "digest": " | ".join(texts[:5])[:500],
            "tilt_meta": meta,
        },
        "provenance": {
            "source": "pre_news_shadow_input_adapter_v1",
            "input_path": _rel(pre_news_path) if pre_doc else "",
        },
        "note": "B-track news lens from pre_news_shadow_input (keyword tilt); research_only; not live trading.",
    }


def _build_macro_doc(feed_path: Path, feed_doc: dict[str, Any] | None) -> dict[str, Any]:
    texts = _texts_from_external_feed(feed_doc) if feed_doc else []
    ds, cf, meta = _score_from_texts(texts)
    return {
        "schema": "macro_independent_lens_v0",
        "version": "0.1.0",
        "lens_id": "macro",
        "engine_id": "independent_lens_v0",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "scores": {"direction_score": round(ds, 6), "confidence": round(cf, 6)},
        "macro_stream_outputs": {
            "adapter": "build_btrack_news_macro_lens_adapters_v1",
            "snippet_count": len(texts),
            "tilt_meta": meta,
        },
        "provenance": {
            "source": "external_feed_drop_adapter_v1",
            "input_path": _rel(feed_path) if feed_doc else "",
            "items_count": int(feed_doc.get("items_count") or 0) if feed_doc else 0,
        },
        "note": "B-track macro lens from external_feed_drop (keyword tilt); research_only; not live trading.",
    }


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pre-news-input", type=Path, default=DEFAULT_PRE_NEWS)
    ap.add_argument("--external-feed", type=Path, default=DEFAULT_EXTERNAL_FEED)
    ap.add_argument("--news-out", type=Path, default=DEFAULT_NEWS_OUT)
    ap.add_argument("--macro-out", type=Path, default=DEFAULT_MACRO_OUT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    pre_doc = _read_json(args.pre_news_input)
    feed_doc = _read_json(args.external_feed)
    if feed_doc is None and args.external_feed == DEFAULT_EXTERNAL_FEED:
        feed_doc = _read_json(DEFAULT_EXTERNAL_FEED_FALLBACK)

    news_doc = _build_news_doc(args.pre_news_input, pre_doc)
    macro_doc = _build_macro_doc(args.external_feed, feed_doc)

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
