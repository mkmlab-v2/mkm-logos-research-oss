#!/usr/bin/env python3
"""Weekly TOP-N engagement report for commander interest topics (internal benchmark)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from commander_interest_benchmark_v1_lib import (  # noqa: E402
    DEFAULT_CONFIG,
    DEFAULT_LOG,
    engagement_score,
    ensure_signal_log,
    load_config,
    load_signals,
    resolve_path,
    topic_map,
    utc_now,
    window_bounds,
)

ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT_JSON = ART / "commander_interest_benchmark_weekly_latest.json"
DEFAULT_OUT_MD = ART / "commander_interest_benchmark_weekly_latest.md"


def _rank_rows(
    rows: list[dict[str, Any]],
    *,
    weights: dict[str, float],
    topics: dict[str, dict[str, Any]],
    top_n: int,
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for row in rows:
        topic_id = str(row.get("topic_id") or "unknown")
        score = engagement_score(row, weights)
        enriched.append(
            {
                "topic_id": topic_id,
                "topic_label_ko": (topics.get(topic_id) or {}).get("label_ko") or topic_id,
                "platform": str(row.get("platform") or "unknown"),
                "title": str(row.get("title") or "").strip(),
                "url": str(row.get("url") or "").strip(),
                "observed_at_utc": row.get("observed_at_utc"),
                "views": int(float(row.get("views") or 0)),
                "likes": int(float(row.get("likes") or 0)),
                "comments": int(float(row.get("comments") or 0)),
                "shares": int(float(row.get("shares") or 0)),
                "engagement_score": round(score, 4),
            }
        )
    enriched.sort(key=lambda r: (-float(r["engagement_score"]), str(r["observed_at_utc"])))
    return enriched[: max(1, int(top_n))]


def build_payload(
    *,
    config_path: Path,
    log_path: Path,
    window_days: int | None = None,
    top_n: int | None = None,
) -> dict[str, Any]:
    config = load_config(config_path)
    log_path = ensure_signal_log(log_path)
    window = int(window_days if window_days is not None else config.get("window_days") or 7)
    top = int(top_n if top_n is not None else config.get("top_n") or 10)
    weights = config.get("engagement_weights") or {}
    start, end = window_bounds(window)
    rows = load_signals(log_path, start=start, end=end, config=config)
    topics = topic_map(config)
    ranked = _rank_rows(rows, weights=weights, topics=topics, top_n=top)

    by_topic: dict[str, list[dict[str, Any]]] = {}
    for item in ranked:
        by_topic.setdefault(str(item["topic_id"]), []).append(item)

    return {
        "schema": "commander_interest_benchmark_weekly_v1",
        "generated_at_utc": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_days": window,
        "window_start_utc": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_end_utc": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "config_path": str(resolve_path(config_path).resolve()),
        "signal_log_path": str(resolve_path(log_path).resolve()),
        "signals_in_window": len(rows),
        "top_n": top,
        "top_items": ranked,
        "top_by_topic": by_topic,
        "track_wall": config.get("track_wall") or {},
        "disclaimer_ko": config.get("disclaimer_ko") or "",
    }


def render_md(payload: dict[str, Any]) -> str:
    lines = [
        "## Commander Interest Benchmark (Weekly)",
        f"- `window_days`: `{payload['window_days']}`",
        f"- `signals_in_window`: `{payload['signals_in_window']}`",
        f"- `top_n`: `{payload['top_n']}`",
        "",
        "### TOP items",
    ]
    for idx, item in enumerate(payload.get("top_items") or [], start=1):
        lines.append(
            f"{idx}. **[{item['topic_label_ko']}]** {item['title']} "
            f"({item['platform']}) — score `{item['engagement_score']}` "
            f"(👍 {item['likes']} · 💬 {item['comments']})"
        )
        if item.get("url"):
            lines.append(f"   - {item['url']}")
    lines.extend(
        [
            "",
            "### Policy",
            "- `lane`: internal observation / benchmarking only",
            "- `human_publish_only`: true",
            f"- disclaimer: {payload.get('disclaimer_ko') or '—'}",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config-json", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--log-jsonl", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--window-days", type=int, default=None)
    ap.add_argument("--top-n", type=int, default=None)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    ap.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    args = ap.parse_args()

    payload = build_payload(
        config_path=args.config_json,
        log_path=args.log_jsonl,
        window_days=args.window_days,
        top_n=args.top_n,
    )
    out_json = resolve_path(args.out_json)
    out_md = resolve_path(args.out_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md.write_text(render_md(payload), encoding="utf-8")
    print(json.dumps({"ok": True, "out_json": str(out_json), "out_md": str(out_md)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
