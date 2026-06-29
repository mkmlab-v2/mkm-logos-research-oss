#!/usr/bin/env python3
"""H-DSS1 chronicle HOLD alignment: DSS news stress vs chronicle final_decision (B-track)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NEWS = ROOT / "docs/final/artifacts/news_observation_v1_latest.jsonl"
DEFAULT_CHRONICLE = ROOT / "docs/final/artifacts/chronicle_history_news_signal_history_latest.jsonl"
DEFAULT_OVERLAY = ROOT / "docs/final/artifacts/chronicle_history_news_signal_h_dss1_daily_overlay_latest.jsonl"
DEFAULT_HYP = ROOT / "docs/final/artifacts/biblical_resonance_hypotheses_v1.json"
DEFAULT_OUT = ROOT / "reports/biblical_history_h_dss1_chronicle_hold_alignment_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict):
                rows.append(obj)
        except json.JSONDecodeError:
            continue
    return rows


def _row_ts(row: dict[str, Any], keys: tuple[str, ...]) -> datetime | None:
    for k in keys:
        ts = _parse_iso(row.get(k))
        if ts is not None:
            return ts
    return None


def _in_window(rows: list[dict[str, Any]], keys: tuple[str, ...], since: datetime) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        ts = _row_ts(row, keys)
        if ts is not None and ts >= since:
            out.append(row)
    return out


def _group_match(text: str, group: list[str]) -> bool:
    return any(tok.lower() in text for tok in group)


def _hypothesis_match(text: str, groups: list[list[str]]) -> bool:
    return any(_group_match(text, g) for g in groups)


def main() -> int:
    ap = argparse.ArgumentParser(description="H-DSS1 chronicle HOLD alignment eval.")
    ap.add_argument("--news-jsonl", type=Path, default=DEFAULT_NEWS)
    ap.add_argument("--chronicle-jsonl", type=Path, default=DEFAULT_CHRONICLE)
    ap.add_argument("--chronicle-overlay-jsonl", type=Path, default=DEFAULT_OVERLAY)
    ap.add_argument("--hypotheses-json", type=Path, default=DEFAULT_HYP)
    ap.add_argument("--lookback-days", type=int, default=90)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    since = now - timedelta(days=args.lookback_days)
    news_rows = _in_window(_load_jsonl(args.news_jsonl), ("as_of_utc", "published_utc"), since)
    chronicle_rows = _in_window(
        _load_jsonl(args.chronicle_jsonl),
        ("generated_at_utc", "as_of_utc"),
        since,
    )
    overlay_rows = _in_window(
        _load_jsonl(args.chronicle_overlay_jsonl),
        ("generated_at_utc", "as_of_utc"),
        since,
    )
    if overlay_rows:
        chronicle_rows = chronicle_rows + overlay_rows

    hyp_doc = _load_json(args.hypotheses_json)
    dss1 = next(
        (h for h in hyp_doc.get("hypotheses", []) if isinstance(h, dict) and h.get("id") == "H-DSS1"),
        None,
    )
    groups = dss1.get("keyword_groups_any", []) if isinstance(dss1, dict) else []
    if not isinstance(groups, list):
        groups = []

    dss1_news_days: set[str] = set()
    for row in news_rows:
        txt = str(row.get("canonical_text", "")).lower()
        if _hypothesis_match(txt, groups):
            ts = _row_ts(row, ("as_of_utc", "published_utc"))
            if ts is not None:
                dss1_news_days.add(ts.date().isoformat())

    hold_rows = sum(1 for r in chronicle_rows if str(r.get("final_decision", "")).upper() == "HOLD")
    chronicle_hold_rate = (hold_rows / len(chronicle_rows)) if chronicle_rows else 0.0

    aligned = 0
    compared = 0
    for row in chronicle_rows:
        ts = _row_ts(row, ("generated_at_utc", "as_of_utc"))
        if ts is None:
            continue
        day = ts.date().isoformat()
        if day not in dss1_news_days:
            continue
        compared += 1
        if str(row.get("final_decision", "")).upper() == "HOLD":
            aligned += 1

    day_alignment_rate = (aligned / compared) if compared else None

    payload = {
        "schema": "biblical_history_h_dss1_chronicle_hold_alignment_v1",
        "hypothesis_id": "H-DSS1",
        "generated_at_utc": _utc_now(),
        "research_rail": "B",
        "hypothesis_tier": "[HYPO]",
        "gating_status": "NON_GATING",
        "window_days": args.lookback_days,
        "inputs": {
            "news_jsonl": str(args.news_jsonl),
            "chronicle_jsonl": str(args.chronicle_jsonl),
            "news_row_count": len(news_rows),
            "chronicle_row_count": len(chronicle_rows),
            "chronicle_overlay_jsonl": str(args.chronicle_overlay_jsonl),
            "chronicle_overlay_row_count": len(overlay_rows),
            "h_dss1_news_match_days": sorted(dss1_news_days),
        },
        "metrics": {
            "chronicle_hold_rate": round(chronicle_hold_rate, 6),
            "h_dss1_news_days_with_chronicle_overlap": compared,
            "hold_aligned_on_overlap_days": aligned,
            "hold_alignment_on_h_dss1_news_days": round(day_alignment_rate, 6) if day_alignment_rate is not None else None,
            "global_hold_alignment_proxy": round(chronicle_hold_rate, 6),
        },
        "interpretation": {
            "status": "research_only_not_promotion_proof",
            "note": (
                "Chronicle rows use generated_at_utc; alignment is same-calendar-day overlap "
                "with H-DSS1 keyword news days only."
            ),
        },
        "fact_lock_notice": "Chronicle HOLD is NON_GATING shadow; not Track A or live trading gate.",
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.output_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
