#!/usr/bin/env python3
"""Build research-only chronicle overlay with HOLD/WATCH/REDUCE mix (falsification lane)."""

from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULES = ROOT / "docs/final/artifacts/chronicle_history_news_decision_rules_v1.json"
DEFAULT_HISTORY = ROOT / "docs/final/artifacts/chronicle_history_news_signal_history_latest.jsonl"
DEFAULT_PR1 = ROOT / "docs/final/artifacts/chronicle_history_news_signal_pr1_daily_overlay_latest.jsonl"
DEFAULT_DSS1 = ROOT / "docs/final/artifacts/chronicle_history_news_signal_h_dss1_daily_overlay_latest.jsonl"
DEFAULT_OUT = ROOT / "docs/final/artifacts/chronicle_history_news_signal_research_decision_mix_latest.jsonl"


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


def _tier_from_score(score: float, thresholds: dict[str, Any]) -> str:
    reduce_min = float(thresholds.get("reduce_min", 0.7))
    watch_min = float(thresholds.get("watch_min", 0.35))
    if score >= reduce_min:
        return "REDUCE"
    if score >= watch_min:
        return "WATCH"
    return "HOLD"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rules-json", type=Path, default=DEFAULT_RULES)
    ap.add_argument("--history-jsonl", type=Path, default=DEFAULT_HISTORY)
    ap.add_argument("--pr1-overlay-jsonl", type=Path, default=DEFAULT_PR1)
    ap.add_argument("--h-dss1-overlay-jsonl", type=Path, default=DEFAULT_DSS1)
    ap.add_argument("--lookback-days", type=int, default=90)
    ap.add_argument("--output-jsonl", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    rules = _load_json(args.rules_json)
    thresholds = rules.get("thresholds") if isinstance(rules.get("thresholds"), dict) else {}
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=args.lookback_days)

    merged: list[dict[str, Any]] = []
    for path in (args.history_jsonl, args.pr1_overlay_jsonl, args.h_dss1_overlay_jsonl):
        for row in _load_jsonl(path):
            ts = _parse_iso(row.get("generated_at_utc")) or _parse_iso(row.get("as_of_utc"))
            if ts is not None and ts >= since:
                merged.append(row)

    out_rows: list[dict[str, Any]] = []
    counts = {"HOLD": 0, "WATCH": 0, "REDUCE": 0}
    for row in merged:
        copy_row = copy.deepcopy(row)
        score = float(copy_row.get("composite_signal_score", 0.0) or 0.0)
        cand = str(copy_row.get("candidate_decision", "")).upper()
        tier = _tier_from_score(score, thresholds)
        if cand in ("HOLD", "WATCH", "REDUCE"):
            rank = {"HOLD": 0, "WATCH": 1, "REDUCE": 2}
            if rank.get(cand, 0) > rank.get(tier, 0):
                tier = cand
        # H-DSS1 overlay rows anchor HOLD on matched news days (falsification / hold-alignment lane).
        if copy_row.get("h_dss1_news_day") is True or str(copy_row.get("overlay_kind", "")).startswith(
            "h_dss1_daily"
        ):
            tier = "HOLD"
        copy_row["overlay_kind"] = "research_decision_mix_v1"
        copy_row["final_decision"] = tier
        copy_row["research_decision_mix"] = True
        counts[tier] = counts.get(tier, 0) + 1
        out_rows.append(copy_row)

    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.output_jsonl.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in out_rows) + ("\n" if out_rows else ""),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "ok": True,
                "output_jsonl": str(args.output_jsonl),
                "row_count": len(out_rows),
                "decision_counts": counts,
                "lookback_days": args.lookback_days,
                "generated_at_utc": _utc_now(),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
