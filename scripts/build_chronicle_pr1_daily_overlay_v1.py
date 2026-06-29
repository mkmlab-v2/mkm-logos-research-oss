#!/usr/bin/env python3
"""Build daily chronicle overlay rows aligned to PR1 news days (B-track research only)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NEWS = ROOT / "docs/final/artifacts/news_observation_v1_latest.jsonl"
DEFAULT_HYP = ROOT / "docs/final/artifacts/biblical_resonance_hypotheses_v1.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/chronicle_history_news_signal_pr1_daily_overlay_latest.jsonl"


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


def _group_match(text: str, group: list[str]) -> bool:
    return any(tok.lower() in text for tok in group)


def _hypothesis_match(text: str, groups: list[list[str]]) -> bool:
    return any(_group_match(text, g) for g in groups)


def main() -> int:
    ap = argparse.ArgumentParser(description="Build PR1-aligned daily chronicle overlay.")
    ap.add_argument("--news-jsonl", type=Path, default=DEFAULT_NEWS)
    ap.add_argument("--hypotheses-json", type=Path, default=DEFAULT_HYP)
    ap.add_argument("--lookback-days", type=int, default=90)
    ap.add_argument("--output-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--include-all-news-days", action="store_true", help="Also emit rows for each news day.")
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    since = now - timedelta(days=args.lookback_days)
    news_rows = []
    for row in _load_jsonl(args.news_jsonl):
        ts = _parse_iso(row.get("as_of_utc") or row.get("published_utc"))
        if ts is not None and ts >= since:
            news_rows.append(row)

    hyp_doc = _load_json(args.hypotheses_json)
    pr1 = next(
        (h for h in hyp_doc.get("hypotheses", []) if isinstance(h, dict) and h.get("id") == "H-PR1"),
        None,
    )
    groups = pr1.get("keyword_groups_any", []) if isinstance(pr1, dict) else []
    if not isinstance(groups, list):
        groups = []

    pr1_days: set[str] = set()
    all_days: set[str] = set()
    for row in news_rows:
        ts = _parse_iso(row.get("as_of_utc") or row.get("published_utc"))
        if ts is None:
            continue
        day = ts.date().isoformat()
        all_days.add(day)
        txt = str(row.get("canonical_text", "")).lower()
        if _hypothesis_match(txt, groups):
            pr1_days.add(day)

    target_days = sorted(all_days if args.include_all_news_days else pr1_days)
    overlay_rows: list[dict[str, Any]] = []
    for day in target_days:
        generated = f"{day}T23:59:59Z"
        is_pr1 = day in pr1_days
        overlay_rows.append(
            {
                "schema": "chronicle_history_news_signal_history_row_v1",
                "generated_at_utc": generated,
                "source_track": "B",
                "governance_state": "S1_SHADOW",
                "observation_mode": "KEEP_OBSERVATION_ONLY",
                "overlay_kind": "pr1_daily_research_v1",
                "dual_regime_primary_id": "research_overlay",
                "window_count": 1,
                "history_similarity": 0.35,
                "source_reliability_score": 0.2,
                "context_stress_inverse": 0.5 if is_pr1 else 0.3,
                "composite_signal_score": 0.42 if is_pr1 else 0.35,
                "candidate_decision": "WATCH" if is_pr1 else "HOLD",
                "final_decision": "HOLD",
                "pr1_news_day": is_pr1,
            }
        )

    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.output_jsonl.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in overlay_rows) + ("\n" if overlay_rows else ""),
        encoding="utf-8",
    )

    meta = {
        "ok": True,
        "output_jsonl": str(args.output_jsonl),
        "row_count": len(overlay_rows),
        "pr1_news_days": sorted(pr1_days),
        "lookback_days": args.lookback_days,
        "generated_at_utc": _utc_now(),
    }
    print(json.dumps(meta, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
