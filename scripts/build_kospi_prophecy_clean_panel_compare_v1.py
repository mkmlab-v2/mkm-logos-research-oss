#!/usr/bin/env python3
"""Compare KOSPI/BTC hit rates on full vs clean OHLCV panels [HYPO][research_only]."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_prophecy_clean_panel_compare_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _bad_ohlcv_dates(rows: list[dict[str, Any]], *, max_abs_return: float) -> list[str]:
    bad: list[str] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        try:
            ret = abs(float(r.get("daily_return") or 0.0))
        except (TypeError, ValueError):
            continue
        if ret > max_abs_return:
            bad.append(str(r.get("eval_date") or "")[:10])
    return sorted({d for d in bad if d})


def _leg_metrics(rows: list[dict[str, Any]], *, instrument: str, exclude_dates: set[str]) -> dict[str, Any]:
    leg = [
        r
        for r in rows
        if isinstance(r, dict)
        and str(r.get("instrument") or "").lower() == instrument
        and str(r.get("eval_date") or "")[:10] not in exclude_dates
    ]
    hits = sum(1 for r in leg if r.get("predicted_direction") == r.get("actual_direction"))
    n = len(leg)
    dist = Counter(str(r.get("predicted_direction") or "") for r in leg)
    return {
        "hits": hits,
        "n": n,
        "hit_rate": round(hits / n, 4) if n else None,
        "pred_distribution": dict(dist),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--max-abs-daily-return", type=float, default=0.15)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    if not args.score_json.is_file():
        print(f"missing score: {args.score_json}", file=sys.stderr)
        return 2

    score = _load(args.score_json)
    rows = [r for r in (score.get("rows") or []) if isinstance(r, dict)]
    bad = _bad_ohlcv_dates(rows, max_abs_return=float(args.max_abs_daily_return))
    exclude = set(bad)

    full = {
        "kospi": _leg_metrics(rows, instrument="kospi", exclude_dates=set()),
        "btc": _leg_metrics(rows, instrument="btc", exclude_dates=set()),
    }
    clean = {
        "kospi": _leg_metrics(rows, instrument="kospi", exclude_dates=exclude),
        "btc": _leg_metrics(rows, instrument="btc", exclude_dates=exclude),
    }
    full_all = [r for r in rows]
    clean_all = [r for r in rows if str(r.get("eval_date") or "")[:10] not in exclude]
    full_combined_hits = sum(1 for r in full_all if r.get("predicted_direction") == r.get("actual_direction"))
    clean_combined_hits = sum(1 for r in clean_all if r.get("predicted_direction") == r.get("actual_direction"))

    out = {
        "schema": "kospi_prophecy_clean_panel_compare_v1",
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "generated_at_utc": _utc_now(),
        "inputs": {
            "score_json": str(args.score_json.relative_to(ROOT)) if args.score_json.is_relative_to(ROOT) else str(args.score_json),
            "max_abs_daily_return": float(args.max_abs_daily_return),
            "neutral_bps": score.get("neutral_bps"),
        },
        "excluded_bad_ohlcv_dates": bad,
        "full_panel": {**full, "combined": {"hits": full_combined_hits, "n": len(full_all), "hit_rate": round(full_combined_hits / len(full_all), 4) if full_all else None}},
        "clean_panel": {**clean, "combined": {"hits": clean_combined_hits, "n": len(clean_all), "hit_rate": round(clean_combined_hits / len(clean_all), 4) if clean_all else None}},
        "delta_clean_minus_full_pp": {
            "kospi": round((clean["kospi"]["hit_rate"] or 0) - (full["kospi"]["hit_rate"] or 0), 4) * 100 if full["kospi"]["hit_rate"] is not None else None,
            "btc": round((clean["btc"]["hit_rate"] or 0) - (full["btc"]["hit_rate"] or 0), 4) * 100 if full["btc"]["hit_rate"] is not None else None,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(f"excluded={bad} kospi clean={clean['kospi']['hit_rate']} full={full['kospi']['hit_rate']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
