#!/usr/bin/env python3
"""Evaluate biblical-symbolic resonance hypotheses against observed news/history."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NEWS = ROOT / "docs" / "final" / "artifacts" / "news_observation_v1_latest.jsonl"
DEFAULT_CHRONICLE = ROOT / "docs" / "final" / "artifacts" / "chronicle_history_news_signal_history_latest.jsonl"
DEFAULT_HYP = ROOT / "docs" / "final" / "artifacts" / "biblical_resonance_hypotheses_v1.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "biblical_resonance_eval_latest.json"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
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


def _in_window(rows: list[dict[str, Any]], ts_key: str, since: datetime) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        ts = _parse_iso(row.get(ts_key))
        if ts is not None and ts >= since:
            out.append(row)
    return out


def _group_match(text: str, group: list[str]) -> bool:
    return any(tok.lower() in text for tok in group)


def _hypothesis_match(text: str, groups: list[list[str]]) -> bool:
    return any(_group_match(text, g) for g in groups)


def _calc(rows_news: list[dict[str, Any]], rows_chronicle: list[dict[str, Any]], hyp_cfg: dict[str, Any]) -> dict[str, Any]:
    groups = hyp_cfg.get("keyword_groups_any", [])
    if not isinstance(groups, list):
        groups = []

    matched = 0
    stress_hits = 0
    stress_terms = ("risk-off", "stress", "shock", "volatility", "liquidity thin", "credit spreads")
    for r in rows_news:
        txt = str(r.get("canonical_text", "")).lower()
        if _hypothesis_match(txt, groups):
            matched += 1
            if any(t in txt for t in stress_terms):
                stress_hits += 1

    total_news = max(1, len(rows_news))
    coverage = matched / total_news
    stress_alignment = (stress_hits / matched) if matched > 0 else 0.0

    hold_rows = sum(1 for r in rows_chronicle if str(r.get("final_decision", "")).upper() == "HOLD")
    hold_alignment = (hold_rows / max(1, len(rows_chronicle))) if rows_chronicle else 0.0

    # Conservative composite; history alignment weighs higher than lexical coverage.
    score = (0.25 * coverage) + (0.25 * stress_alignment) + (0.5 * hold_alignment)

    return {
        "id": str(hyp_cfg.get("id", "unknown")),
        "label": str(hyp_cfg.get("label", "unknown")),
        "anchor_symbol": str(hyp_cfg.get("anchor_symbol", "")),
        "matched_rows": matched,
        "coverage_ratio": round(coverage, 6),
        "stress_alignment_ratio": round(stress_alignment, 6),
        "hold_alignment_ratio": round(hold_alignment, 6),
        "composite_score": round(score, 6),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate biblical resonance hypotheses.")
    ap.add_argument("--news-jsonl", type=Path, default=DEFAULT_NEWS)
    ap.add_argument("--chronicle-jsonl", type=Path, default=DEFAULT_CHRONICLE)
    ap.add_argument("--hypotheses-json", type=Path, default=DEFAULT_HYP)
    ap.add_argument("--lookback-days", type=int, default=30)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.hypotheses_json.exists():
        raise FileNotFoundError(f"Missing hypotheses file: {args.hypotheses_json}")

    now = _now_utc()
    since = now - timedelta(days=args.lookback_days)
    news_rows = _in_window(_load_jsonl(args.news_jsonl), "as_of_utc", since)
    chronicle_rows = _in_window(_load_jsonl(args.chronicle_jsonl), "as_of_utc", since)
    hyp = _load_json(args.hypotheses_json)

    hypo_list = hyp.get("hypotheses", [])
    if not isinstance(hypo_list, list):
        hypo_list = []

    eval_rows = [_calc(news_rows, chronicle_rows, h) for h in hypo_list]
    strong = sum(1 for r in eval_rows if r["composite_score"] >= 0.6)
    medium = sum(1 for r in eval_rows if 0.4 <= r["composite_score"] < 0.6)
    weak = max(0, len(eval_rows) - strong - medium)
    unique_days = len({str(r.get("as_of_utc", ""))[:10] for r in news_rows if r.get("as_of_utc")})

    out = {
        "schema": "biblical_resonance_eval_v1",
        "generated_at_utc": now.isoformat().replace("+00:00", "Z"),
        "source_track": "B",
        "observation_mode": "KEEP_OBSERVATION_ONLY",
        "auto_bind_to_atrack_forbidden": True,
        "window_days": args.lookback_days,
        "inputs": {
            "news_jsonl": str(args.news_jsonl),
            "chronicle_jsonl": str(args.chronicle_jsonl),
            "hypotheses_json": str(args.hypotheses_json),
            "news_row_count": len(news_rows),
            "chronicle_row_count": len(chronicle_rows),
            "news_unique_asof_days": unique_days,
        },
        "hypotheses": eval_rows,
        "summary": {
            "strong_count": strong,
            "medium_count": medium,
            "weak_count": weak,
        },
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": out["schema"],
                "output_json": str(args.output_json),
                "news_row_count": len(news_rows),
                "strong_count": strong,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
