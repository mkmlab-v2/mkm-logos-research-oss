#!/usr/bin/env python3
"""[HYPO] BTC leg miss/hit breakdown from btrack_prophecy_score panel + dual per-date directions.

Writes reports/btrack_btc_leg_miss_analysis_v1_latest.json and .md. research_only.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
DEFAULT_DUAL = ROOT / "reports/btrack_ensemble_per_date_directions_dual_v1_latest.json"
DEFAULT_OUT_JSON = ROOT / "reports/btrack_btc_leg_miss_analysis_v1_latest.json"
DEFAULT_OUT_MD = ROOT / "reports/btrack_btc_leg_miss_analysis_v1_latest.md"
SCHEMA = "btrack_btc_leg_miss_analysis_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _classify_row(r: dict[str, Any]) -> str:
    pred = str(r.get("predicted_direction") or "").strip().lower()
    actual = str(r.get("actual_direction") or "").strip().lower()
    if not pred or not actual:
        return "incomplete"
    if pred == actual:
        return "hit"
    if pred == "neutral" or actual == "neutral":
        return "partial_neutral"
    return "miss"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--dual-json", type=Path, default=DEFAULT_DUAL)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    ap.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    args = ap.parse_args(argv)

    score = _load(args.score_json)
    if not score:
        raise SystemExit(f"missing score: {args.score_json}")

    rows = [
        r
        for r in (score.get("rows") or [])
        if isinstance(r, dict) and str(r.get("instrument") or "").lower() == "btc"
    ]
    rows.sort(key=lambda r: str(r.get("eval_date")))

    dual = _load(args.dual_json) or {}
    dual_btc = {
        str(r.get("eval_date"))[:10]: r
        for r in (dual.get("rows") or [])
        if isinstance(r, dict) and str(r.get("instrument") or "").lower() == "btc"
    }
    dual_kospi = {
        str(r.get("eval_date"))[:10]: r
        for r in (dual.get("rows") or [])
        if isinstance(r, dict) and str(r.get("instrument") or "").lower() == "kospi"
    }

    kospi_rows = [
        r
        for r in (score.get("rows") or [])
        if isinstance(r, dict) and str(r.get("instrument") or "").lower() == "kospi"
    ]
    kospi_by_date = {str(r.get("eval_date"))[:10]: r for r in kospi_rows}

    detail: list[dict[str, Any]] = []
    counts = {"hit": 0, "miss": 0, "partial_neutral": 0, "incomplete": 0}
    decouple_days: list[str] = []

    for r in rows:
        d = str(r.get("eval_date"))[:10]
        cls = _classify_row(r)
        counts[cls] = counts.get(cls, 0) + 1
        k = kospi_by_date.get(d)
        k_pred = str(k.get("predicted_direction") or "").lower() if k else None
        b_pred_dual = str((dual_btc.get(d) or {}).get("predicted_direction") or "").lower() or None
        k_pred_dual = str((dual_kospi.get(d) or {}).get("predicted_direction") or "").lower() or None
        if k_pred and str(r.get("predicted_direction") or "").lower() != k_pred:
            decouple_days.append(d)
        price_lens = ((dual_btc.get(d) or {}).get("lens_values") or {}).get("price") or {}
        detail.append(
            {
                "eval_date": d,
                "classification": cls,
                "predicted_direction": r.get("predicted_direction"),
                "actual_direction": r.get("actual_direction"),
                "daily_return_pct": round(float(r.get("daily_return") or 0) * 100, 4),
                "flow_score_for_reversal": r.get("flow_score_for_reversal"),
                "kospi_predicted_same_day": k_pred,
                "dual_btc_predicted": b_pred_dual,
                "dual_kospi_predicted": k_pred_dual,
                "btc_price_lens_score": price_lens.get("score"),
                "btc_price_lens_confidence": price_lens.get("confidence"),
            }
        )

    n = len(rows)
    hits = counts["hit"]
    rate = round(hits / n, 6) if n else None
    misses = [x for x in detail if x["classification"] == "miss"]
    partials = [x for x in detail if x["classification"] == "partial_neutral"]

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "inputs": {
            "score_json": str(args.score_json),
            "dual_json": str(args.dual_json) if args.dual_json.is_file() else None,
            "n_btc_rows": n,
            "eval_date_first": detail[0]["eval_date"] if detail else None,
            "eval_date_last": detail[-1]["eval_date"] if detail else None,
            "hypothesis_instrument_declared": (score.get("inputs") or {}).get("hypothesis_instrument_declared"),
        },
        "summary": {
            "price_directional_hit_rate": rate,
            "price_hits": hits,
            "n_evaluated": n,
            "classification_counts": counts,
            "days_btc_kospi_pred_differ": len(decouple_days),
            "decouple_dates": decouple_days,
        },
        "misses": misses,
        "partial_neutral": partials,
        "all_rows": detail,
        "notes_ko": [
            "flow_score_for_reversal은 KOSPI 일별 수급 기반; BTC leg 채점 행에 복사될 수 있으나 BTC 전용 피처는 아님.",
            "KOSPI 급등·수급 강한 날에도 BTC per-date는 price 렌즈 bear 쪽이면 디커플 가능.",
        ],
    }

    md_lines = [
        "# B-track BTC leg miss analysis [HYPO]",
        "",
        f"- generated_at_utc: `{out['generated_at_utc']}`",
        f"- window: {out['inputs']['eval_date_first']} .. {out['inputs']['eval_date_last']} ({n} rows)",
        f"- hit_rate: **{100 * rate:.1f}%** ({hits}/{n})" if rate is not None else "- hit_rate: n/a",
        f"- BTC≠KOSPI prediction days: **{len(decouple_days)}**",
        "",
        "## Misses",
    ]
    for m in misses:
        md_lines.append(
            f"- {m['eval_date']}: pred **{m['predicted_direction']}** vs actual **{m['actual_direction']}** "
            f"({m['daily_return_pct']:+.2f}%) · KOSPI same day **{m.get('kospi_predicted_same_day')}**"
        )
    if partials:
        md_lines.append("")
        md_lines.append("## Partial (neutral involved)")
        for p in partials:
            md_lines.append(
                f"- {p['eval_date']}: pred **{p['predicted_direction']}** vs actual **{p['actual_direction']}** "
                f"({p['daily_return_pct']:+.2f}%)"
            )
    md_lines.extend(["", "*research_only — not Track A / not live trading.*", ""])

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.out_md.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"WROTE: {args.out_json.resolve()}")
    print(f"WROTE: {args.out_md.resolve()}")
    print(f"btc_hit_rate={rate} misses={len(misses)} partial_neutral={len(partials)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
