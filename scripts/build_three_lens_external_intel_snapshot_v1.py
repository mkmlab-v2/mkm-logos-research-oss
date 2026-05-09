#!/usr/bin/env python3
"""Build external intel snapshot for three-lens coordinator."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_s() -> str:
    return _now().strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _safe_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return _read_json(path)
    except Exception:
        return {}


def _parse_ts(value: Any) -> datetime | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
        return datetime.fromisoformat(s).astimezone(timezone.utc)
    except Exception:
        return None


def _fresh(ts: datetime | None, max_age_hours: int) -> bool:
    if ts is None:
        return False
    return (_now() - ts) <= timedelta(hours=max(1, max_age_hours))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--external-macro-json", type=Path, default=ART / "external_macro_signals_latest.json")
    ap.add_argument("--external-news-json", type=Path, default=ART / "external_news_feed_latest.json")
    ap.add_argument("--news-lens-json", type=Path, default=ART / "news_independent_lens_latest.json")
    ap.add_argument("--macro-lens-json", type=Path, default=ART / "macro_independent_lens_latest.json")
    ap.add_argument("--max-age-hours", type=int, default=48)
    ap.add_argument("--output-json", type=Path, default=ART / "three_lens_external_intel_snapshot_latest.json")
    args = ap.parse_args()

    macro = _safe_json(args.external_macro_json if args.external_macro_json.is_absolute() else ROOT / args.external_macro_json)
    news = _safe_json(args.external_news_json if args.external_news_json.is_absolute() else ROOT / args.external_news_json)
    news_lens = _safe_json(args.news_lens_json if args.news_lens_json.is_absolute() else ROOT / args.news_lens_json)
    macro_lens = _safe_json(args.macro_lens_json if args.macro_lens_json.is_absolute() else ROOT / args.macro_lens_json)

    macro_ts = _parse_ts(macro.get("ts_utc"))
    news_ts = _parse_ts(news.get("ts_utc"))
    news_lens_ts = _parse_ts(news_lens.get("ts_utc"))
    macro_lens_ts = _parse_ts(macro_lens.get("ts_utc"))

    macro_fresh = _fresh(macro_ts, args.max_age_hours)
    news_fresh = _fresh(news_ts, args.max_age_hours)
    news_lens_fresh = _fresh(news_lens_ts, args.max_age_hours)
    macro_lens_fresh = _fresh(macro_lens_ts, args.max_age_hours)

    macro_trend = (macro.get("macro_trend") or {}) if isinstance(macro.get("macro_trend"), dict) else {}
    items_count = int(news.get("items_count") or 0)
    news_score = ((news_lens.get("scores") or {}).get("direction_score") if isinstance(news_lens.get("scores"), dict) else None)
    macro_score = ((macro_lens.get("scores") or {}).get("direction_score") if isinstance(macro_lens.get("scores"), dict) else None)
    news_conf = ((news_lens.get("scores") or {}).get("confidence") if isinstance(news_lens.get("scores"), dict) else None)
    news_stream_outputs = news_lens.get("news_stream_outputs") if isinstance(news_lens.get("news_stream_outputs"), dict) else {}
    lens_headline_count = int(news_stream_outputs.get("headline_count") or 0)
    lens_fallback_news_ok = bool(news_lens_fresh and lens_headline_count > 0)
    effective_news_items_count = items_count if items_count > 0 else lens_headline_count

    payload = {
        "schema": "three_lens_external_intel_snapshot_v1",
        "generated_at_utc": _now_s(),
        "max_age_hours": int(args.max_age_hours),
        "freshness": {
            "external_macro_fresh": macro_fresh,
            "external_news_fresh": news_fresh,
            "macro_lens_fresh": macro_lens_fresh,
            "news_lens_fresh": news_lens_fresh,
        },
        "external_macro": {
            "ts_utc": macro.get("ts_utc"),
            "trend": macro_trend.get("trend"),
            "trend_score": macro_trend.get("score"),
            "boundary_ack": macro.get("boundary_ack"),
        },
        "external_news": {
            "ts_utc": news.get("ts_utc"),
            "items_count": items_count,
            "effective_items_count": effective_news_items_count,
            "boundary_ack": news.get("boundary_ack"),
        },
        "lens_scores": {
            "macro_direction_score": macro_score,
            "news_direction_score": news_score,
            "news_confidence": news_conf,
            "news_headline_count": lens_headline_count,
        },
        "fallbacks": {
            "news_lens_fallback_used": bool(items_count <= 0 and lens_fallback_news_ok),
            "news_lens_fallback_ok": lens_fallback_news_ok,
        },
        "ready_for_orchestrator_context": bool(macro_fresh and macro_lens_fresh and (news_fresh or lens_fallback_news_ok)),
    }

    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "ready": payload["ready_for_orchestrator_context"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
