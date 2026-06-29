#!/usr/bin/env python3
"""[HYPO] KOSPI June 2026 miss streak — per-date ensemble vs score vs realized."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE = ROOT / "reports/btrack_prophecy_score_recommended_eval_chain_v1_latest.json"
DEFAULT_DUAL = ROOT / "reports/btrack_ensemble_per_date_directions_dual_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_june2026_miss_streak_decomposition_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _dual_index(dual: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for r in dual.get("rows") or []:
        if not isinstance(r, dict):
            continue
        ed = str(r.get("eval_date") or "")[:10]
        inst = str(r.get("instrument") or "").lower()
        if len(ed) == 10 and inst:
            out[(ed, inst)] = r
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--dual-json", type=Path, default=DEFAULT_DUAL)
    ap.add_argument("--month-prefix", default="2026-06", help="YYYY-MM filter on eval_date")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    score_path = args.score_json if args.score_json.is_absolute() else ROOT / args.score_json
    dual_path = args.dual_json if args.dual_json.is_absolute() else ROOT / args.dual_json
    score = _load(score_path)
    dual = _load(dual_path)
    dix = _dual_index(dual)
    prefix = str(args.month_prefix).strip()

    days: list[dict[str, Any]] = []
    for r in score.get("rows") or []:
        if not isinstance(r, dict):
            continue
        if str(r.get("instrument") or "").lower() != "kospi":
            continue
        ed = str(r.get("eval_date") or "")[:10]
        if not ed.startswith(prefix):
            continue
        ens = dix.get((ed, "kospi")) or {}
        pred_score = r.get("predicted_direction")
        pred_ens = ens.get("predicted_direction")
        actual = r.get("actual_direction")
        hit = pred_score == actual
        lens = ens.get("lens_values") if isinstance(ens.get("lens_values"), dict) else {}
        price_lens = lens.get("price") if isinstance(lens.get("price"), dict) else {}
        days.append(
            {
                "eval_date": ed,
                "score_pred": pred_score,
                "ensemble_pred": pred_ens,
                "actual": actual,
                "hit": hit,
                "daily_return": r.get("daily_return"),
                "ret_pct": round(float(r.get("daily_return") or 0) * 100, 4) if r.get("daily_return") is not None else None,
                "ensemble_confidence": ens.get("confidence"),
                "price_lens_score": price_lens.get("score"),
                "price_lens_confidence": price_lens.get("confidence"),
                "weighted_score": ens.get("weighted_score"),
                "score_matches_ensemble": pred_score == pred_ens,
                "flow_score_for_reversal": r.get("flow_score_for_reversal"),
                "miss_reason_tag": (
                    "price_lens_bull_into_bear_day"
                    if pred_ens == "bull" and actual == "bear" and float(price_lens.get("score") or 0) > 0.5
                    else ("ensemble_bull_miss" if pred_score == "bull" and actual == "bear" else None)
                ),
            }
        )

    days.sort(key=lambda x: x["eval_date"])
    hits = sum(1 for d in days if d.get("hit"))
    miss_streak_end = 0
    for d in reversed(days):
        if d.get("hit"):
            break
        miss_streak_end += 1

    doc = {
        "schema": "kospi_june2026_miss_streak_decomposition_v1",
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "generated_at_utc": _utc_now(),
        "month_prefix": prefix,
        "score_json": str(score_path.resolve().relative_to(ROOT.resolve())).replace("\\", "/"),
        "dual_json": str(dual_path.resolve().relative_to(ROOT.resolve())).replace("\\", "/"),
        "neutral_bps": score.get("neutral_bps"),
        "n_days": len(days),
        "hits": hits,
        "hit_rate": round(hits / len(days), 6) if days else None,
        "trailing_miss_streak": miss_streak_end,
        "days": days,
        "summary": {
            "price_lens_bull_on_bear_miss_n": sum(
                1 for d in days if d.get("miss_reason_tag") == "price_lens_bull_into_bear_day"
            ),
            "score_ensemble_mismatch_n": sum(1 for d in days if d.get("score_matches_ensemble") is False),
            "note": "June panel uses causal per-date ensemble (overnight OFF). Misses at tail often align with high price_lens bull score into realized bear.",
        },
    }
    out = args.output if args.output.is_absolute() else ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out} days={len(days)} hit_rate={doc['hit_rate']} trailing_miss={miss_streak_end}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
