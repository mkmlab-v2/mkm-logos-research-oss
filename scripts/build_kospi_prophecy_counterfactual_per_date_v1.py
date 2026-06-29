#!/usr/bin/env python3
"""Refresh frozen-multi vs per-date causal KOSPI counterfactual [HYPO][research_only]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_HYP = ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json"
DEFAULT_DUAL = ROOT / "reports/btrack_ensemble_per_date_directions_dual_v1_latest.json"
DEFAULT_BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports/kospi_prophecy_counterfactual_per_date_v1_latest.json"
WORK_FROZEN = ROOT / "reports/_kospi_cf_frozen_score_tmp.json"
WORK_CAUSAL = ROOT / "reports/_kospi_cf_causal_score_tmp.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _kospi_metrics(rows: list[dict[str, Any]], *, exclude: set[str]) -> dict[str, Any]:
    leg = [
        r
        for r in rows
        if isinstance(r, dict)
        and str(r.get("instrument") or "").lower() == "kospi"
        and str(r.get("eval_date") or "")[:10] not in exclude
    ]
    hits = sum(1 for r in leg if r.get("predicted_direction") == r.get("actual_direction"))
    n = len(leg)
    dist = Counter(str(r.get("predicted_direction") or "") for r in leg)
    return {"hits": hits, "n": n, "hit_rate": round(hits / n, 4) if n else None, "pred_distribution": dict(dist)}


def _bad_dates(rows: list[dict[str, Any]], *, max_abs: float) -> set[str]:
    bad: set[str] = set()
    for r in rows:
        try:
            if abs(float(r.get("daily_return") or 0.0)) > max_abs:
                bad.add(str(r.get("eval_date") or "")[:10])
        except (TypeError, ValueError):
            continue
    return {d for d in bad if d}


def _build_score(
    *,
    hypothesis: Path,
    btc_csv: Path,
    per_date_json: Path | None,
    out: Path,
    recent_days: int,
    neutral_bps: float,
) -> int:
    cmd = [
        sys.executable,
        str(ROOT / "scripts/build_btrack_prophecy_score_from_ohlcv.py"),
        "--hypothesis-json",
        str(hypothesis),
        "--btc-csv",
        str(btc_csv),
        "--force-dual-leg-panel",
        "--recent-trading-days",
        str(recent_days),
        "--neutral-bps",
        str(neutral_bps),
        "--output",
        str(out),
    ]
    if per_date_json is not None:
        cmd.extend(["--per-date-direction-json", str(per_date_json)])
    return subprocess.run(cmd, cwd=str(ROOT)).returncode


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--recent-trading-days", type=int, default=30)
    ap.add_argument("--neutral-bps-frozen", type=float, default=8.0)
    ap.add_argument("--neutral-bps-causal", type=float, default=5.0)
    ap.add_argument("--max-abs-daily-return", type=float, default=0.15)
    ap.add_argument("--dual-json", type=Path, default=DEFAULT_DUAL)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    if not DEFAULT_HYP.is_file():
        print(f"missing hypothesis: {DEFAULT_HYP}", file=sys.stderr)
        return 2

    rc = _build_score(
        hypothesis=DEFAULT_HYP,
        btc_csv=DEFAULT_BTC,
        per_date_json=None,
        out=WORK_FROZEN,
        recent_days=int(args.recent_trading_days),
        neutral_bps=float(args.neutral_bps_frozen),
    )
    if rc != 0:
        return rc
    if not args.dual_json.is_file():
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/build_btrack_dual_per_date_directions_v1.py"),
                "--recent-trading-days",
                str(int(args.recent_trading_days)),
            ],
            cwd=str(ROOT),
            check=False,
        )
    rc = _build_score(
        hypothesis=DEFAULT_HYP,
        btc_csv=DEFAULT_BTC,
        per_date_json=args.dual_json,
        out=WORK_CAUSAL,
        recent_days=int(args.recent_trading_days),
        neutral_bps=float(args.neutral_bps_causal),
    )
    if rc != 0:
        return rc

    frozen_doc = _load(WORK_FROZEN)
    causal_doc = _load(WORK_CAUSAL)
    frozen_rows = [r for r in (frozen_doc.get("rows") or []) if isinstance(r, dict)]
    causal_rows = [r for r in (causal_doc.get("rows") or []) if isinstance(r, dict)]
    bad = _bad_dates(causal_rows, max_abs=float(args.max_abs_daily_return))

    frozen_m = _kospi_metrics(frozen_rows, exclude=bad)
    causal_m = _kospi_metrics(causal_rows, exclude=bad)

    frozen_by: dict[str, str] = {}
    causal_by: dict[str, str] = {}
    for r in frozen_rows:
        if str(r.get("instrument") or "").lower() == "kospi":
            frozen_by[str(r.get("eval_date") or "")[:10]] = str(r.get("predicted_direction") or "")
    for r in causal_rows:
        if str(r.get("instrument") or "").lower() == "kospi":
            causal_by[str(r.get("eval_date") or "")[:10]] = str(r.get("predicted_direction") or "")

    flipped: list[dict[str, Any]] = []
    for ed in sorted(set(frozen_by) & set(causal_by) - bad):
        fa = next(
            (
                r.get("actual_direction")
                for r in causal_rows
                if str(r.get("instrument") or "").lower() == "kospi" and str(r.get("eval_date") or "")[:10] == ed
            ),
            None,
        )
        fp, cp = frozen_by[ed], causal_by[ed]
        if fp != fa and cp == fa:
            flipped.append({"eval_date": ed, "frozen_pred": fp, "causal_pred": cp, "actual": fa})

    delta_pp = None
    if frozen_m.get("hit_rate") is not None and causal_m.get("hit_rate") is not None:
        delta_pp = round((causal_m["hit_rate"] - frozen_m["hit_rate"]) * 100, 2)

    out_doc: dict[str, Any] = {
        "schema": "kospi_prophecy_counterfactual_per_date_v1",
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "generated_at_utc": _utc_now(),
        "comparison_window": {
            "clean_dates_excluding_bad_ohlcv": causal_m.get("n"),
            "excluded_bad_ohlcv_dates": sorted(bad),
        },
        "frozen_baseline": {
            "mode": "frozen_multi_hypothesis_no_per_date",
            "neutral_bps": float(args.neutral_bps_frozen),
            **frozen_m,
        },
        "per_date_causal_kospi": {
            "per_date_directions": str(args.dual_json.relative_to(ROOT)).replace("\\", "/"),
            "kospi_ensemble_config": "docs/final/artifacts/btrack_lens_ensemble_kospi_per_date_v1.json",
            "overnight_overlay": "off",
            "neutral_bps": float(args.neutral_bps_causal),
            **causal_m,
        },
        "delta": {
            "hit_rate_pp": delta_pp,
            "hits_gained": (causal_m.get("hits") or 0) - (frozen_m.get("hits") or 0),
        },
        "flipped_frozen_miss_to_causal_hit": flipped,
        "note": "In-sample clean panel; not WF holdout. Track A promotion requires combined_all_passed + human.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output} frozen={frozen_m.get('hit_rate')} causal={causal_m.get('hit_rate')} delta_pp={delta_pp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
