#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Science Core long-history slice eval — year, regime, coverage [HYPO][research_only]."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.btrack_multilens_per_date_core_v1 import (  # noqa: E402
    DEFAULT_LOGOS_LENS,
    DEFAULT_MYEONGNI_JSONL,
    DEFAULT_SASANG_JSONL,
)
from scripts.run_science_core_horizon_empirical_eval_v1 import (  # noqa: E402
    DEFAULT_SCIENCE_JSONL_BTC,
    DEFAULT_SCIENCE_JSONL_KOSPI,
    build_daily_short_rows,
)
import scripts.run_three_lens_horizon_empirical_eval_v1 as v1  # noqa: E402

DEFAULT_OUT = ROOT / "reports/science_core_long_history_slice_eval_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/science_core_long_history_slice_eval_v1_latest.json"

TRACK_LENS_IDS = (
    "science_core",
    "price_only",
    "macro_only",
    "science_plus_sasang",
)

# [HYPO] heuristic crisis windows for research slicing — not live regime_map triggers.
HISTORICAL_REGIME_WINDOWS: dict[str, tuple[str, str]] = {
    "imf": ("1997-11-01", "1998-12-31"),
    "it_bubble": ("2000-01-01", "2002-10-31"),
    "lehman": ("2008-09-01", "2009-06-30"),
    "covid": ("2020-02-01", "2020-05-31"),
}

COVERAGE_SLICES: dict[str, Callable[[dict[str, Any]], bool]] = {
    "all": lambda _r: True,
    "news_causal_exa": lambda r: r.get("news_mode") == "causal_exa_news_window",
    "recent_5y": lambda r: str(r.get("session_date") or "") >= "2021-01-01",
    "holdout_2026_h1": lambda r: "2026-01-01" <= str(r.get("session_date") or "") <= "2026-06-08",
    "macro_bull_gate": lambda r: r.get("macro_gate_sign") == "bull",
    "macro_bear_gate": lambda r: r.get("macro_gate_sign") == "bear",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _repo_rel(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _macro_gate_sign(score: float | None) -> str:
    if score is None:
        return "unknown"
    if score > 0.05:
        return "bull"
    if score < -0.05:
        return "bear"
    return "neutral"


def _rolling_vol_terciles(
    closes: dict[str, float],
    trading_days: list[str],
    *,
    window: int = 21,
) -> dict[str, str]:
    import statistics

    vol_by_day: dict[str, float] = {}
    for i, dk in enumerate(trading_days):
        if i < window:
            continue
        rets: list[float] = []
        for j in range(i - window + 1, i + 1):
            d0, d1 = trading_days[j - 1], trading_days[j]
            c0, c1 = closes.get(d0), closes.get(d1)
            if c0 and c1 and c0 != 0:
                rets.append((c1 - c0) / c0)
        if len(rets) >= max(5, window // 2):
            vol_by_day[dk] = statistics.pstdev(rets)
    if not vol_by_day:
        return {}
    vals = sorted(vol_by_day.values())
    q1 = vals[len(vals) // 3]
    q2 = vals[(2 * len(vals)) // 3]
    out: dict[str, str] = {}
    for dk, vol in vol_by_day.items():
        if vol <= q1:
            out[dk] = "low_vol"
        elif vol <= q2:
            out[dk] = "mid_vol"
        else:
            out[dk] = "high_vol"
    return out


def _outcome_rates(rows: list[dict[str, Any]], lens_id: str) -> dict[str, Any]:
    outcomes = [
        (r.get("outcomes_short_1d") or {}).get(lens_id)
        for r in rows
        if lens_id in (r.get("outcomes_short_1d") or {})
    ]
    hits = sum(1 for o in outcomes if o == "HIT")
    fails = sum(1 for o in outcomes if o == "FAIL")
    neutral = sum(1 for o in outcomes if o == "NEUTRAL_DRAW")
    n = len(outcomes)
    n_dir = hits + fails
    sasang_ok = sum(1 for r in rows if r.get("sasang_data_quality") not in {None, "missing"})
    return {
        "n_scored": n,
        "hit": hits,
        "fail": fails,
        "neutral_draw": neutral,
        "directional_hit_rate": round(hits / n_dir, 4) if n_dir else None,
        "soft_hit_rate": round((hits + 0.5 * neutral) / n, 4) if n else None,
        "sasang_coverage_days": sasang_ok,
    }


def _slice_block(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"n_days": 0, "lenses": {}}
    date_min = min(str(r["session_date"]) for r in rows)
    date_max = max(str(r["session_date"]) for r in rows)
    lenses = {lid: _outcome_rates(rows, lid) for lid in TRACK_LENS_IDS}
    ranked = sorted(
        [{"lens_id": lid, **metrics} for lid, metrics in lenses.items() if metrics.get("n_scored")],
        key=lambda x: float(x.get("soft_hit_rate") or -1.0),
        reverse=True,
    )
    for i, row in enumerate(ranked, start=1):
        row["rank_by_soft_hit"] = i
    return {
        "n_days": len(rows),
        "date_min": date_min,
        "date_max": date_max,
        "lenses": lenses,
        "ranked_by_soft_hit_short_1d": ranked,
        "best_lens_id": ranked[0]["lens_id"] if ranked else None,
    }


def _enrich_daily_rows(
    daily_rows: list[dict[str, Any]],
    *,
    science_jsonl: Path,
    vol_tercile_by_day: dict[str, str],
) -> list[dict[str, Any]]:
    science_by: dict[str, dict[str, Any]] = {}
    for line in science_jsonl.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        dk = str(row.get("session_date") or "")[:10]
        if dk:
            science_by[dk] = row

    enriched: list[dict[str, Any]] = []
    for row in daily_rows:
        dk = str(row.get("session_date") or "")[:10]
        science_row = science_by.get(dk) or {}
        comps = science_row.get("components") if isinstance(science_row.get("components"), dict) else {}
        macro_block = comps.get("macro") if isinstance(comps.get("macro"), dict) else {}
        news_block = comps.get("news") if isinstance(comps.get("news"), dict) else {}
        macro_score = macro_block.get("direction_score")
        preds = row.get("predictions") if isinstance(row.get("predictions"), dict) else {}
        sasang_q = "missing"
        if preds.get("sasang") not in (None, "neutral"):
            sasang_q = "present"
        elif preds.get("science_plus_sasang") == preds.get("science_core"):
            sasang_q = "missing_or_neutral"
        enriched.append(
            {
                **row,
                "calendar_year": dk[:4],
                "macro_gate_sign": _macro_gate_sign(
                    float(macro_score) if macro_score is not None else None
                ),
                "macro_mode": macro_block.get("mode"),
                "news_mode": news_block.get("mode"),
                "vol_tercile": vol_tercile_by_day.get(dk),
                "sasang_data_quality": sasang_q,
            }
        )
    return enriched


def run_slice_eval(
    *,
    instrument: str,
    csv_path: Path,
    science_jsonl: Path,
    date_from: str | None,
    date_to: str | None,
    neutral_bps: float,
    myeongni_jsonl: Path,
    sasang_jsonl: Path,
    logos_lens: Path,
) -> dict[str, Any]:
    closes = v1._load_closes(csv_path)
    trading_days = sorted(closes.keys())
    vol_tercile_by_day = _rolling_vol_terciles(closes, trading_days)

    daily_rows = build_daily_short_rows(
        csv_path=csv_path,
        science_jsonl=science_jsonl,
        date_from=date_from,
        date_to=date_to,
        neutral_bps=neutral_bps,
        myeongni_jsonl=myeongni_jsonl,
        sasang_jsonl=sasang_jsonl,
        logos_lens=logos_lens,
        logos_jsonl=None,
        myeongni_momentum_window=5,
    )
    rows = _enrich_daily_rows(
        daily_rows,
        science_jsonl=science_jsonl,
        vol_tercile_by_day=vol_tercile_by_day,
    )

    by_year: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_macro: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_vol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_regime: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_coverage: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in rows:
        by_year[str(row.get("calendar_year") or "unknown")].append(row)
        by_macro[str(row.get("macro_gate_sign") or "unknown")].append(row)
        vol_key = str(row.get("vol_tercile") or "unknown")
        by_vol[vol_key].append(row)
        dk = str(row.get("session_date") or "")
        for regime_id, (start, end) in HISTORICAL_REGIME_WINDOWS.items():
            if start <= dk <= end:
                by_regime[regime_id].append(row)
        for cov_id, pred in COVERAGE_SLICES.items():
            if pred(row):
                by_coverage[cov_id].append(row)

    coverage_audit = {
        "news_causal_exa_days": sum(1 for r in rows if r.get("news_mode") == "causal_exa_news_window"),
        "news_global_snapshot_days": sum(1 for r in rows if r.get("news_mode") == "global_news_snapshot"),
        "macro_causal_gate_days": sum(1 for r in rows if r.get("macro_mode") == "causal_macro_risk_gate_asof"),
        "sasang_present_days": sum(1 for r in rows if r.get("sasang_data_quality") == "present"),
        "note": (
            "news causal_exa is sparse locally; long-window science_core is mostly price+macro. "
            "science_plus_sasang on long history lacks per-date sasang except recent humanist build."
        ),
    }

    return {
        "schema": "science_core_long_history_slice_eval_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "boundary_ack": True,
        "instrument": instrument,
        "csv_path": _repo_rel(csv_path),
        "science_jsonl": _repo_rel(science_jsonl),
        "date_from": date_from,
        "date_to": date_to,
        "neutral_bps": neutral_bps,
        "horizon": "short_1d",
        "n_eval_days": len(rows),
        "coverage_audit": coverage_audit,
        "slices": {
            "by_year": {k: _slice_block(v) for k, v in sorted(by_year.items())},
            "by_macro_gate": {k: _slice_block(v) for k, v in sorted(by_macro.items())},
            "by_vol_tercile": {k: _slice_block(v) for k, v in sorted(by_vol.items())},
            "by_historical_regime_window_hypo": {k: _slice_block(v) for k, v in sorted(by_regime.items())},
            "by_coverage": {k: _slice_block(v) for k, v in sorted(by_coverage.items())},
        },
        "headline": _headline(rows),
    }


def _headline(rows: list[dict[str, Any]]) -> dict[str, Any]:
    all_block = _slice_block(rows)
    recent = _slice_block([r for r in rows if str(r.get("session_date") or "") >= "2021-01-01"])
    holdout = _slice_block(
        [r for r in rows if "2026-01-01" <= str(r.get("session_date") or "") <= "2026-06-08"]
    )
    news_causal = _slice_block([r for r in rows if r.get("news_mode") == "causal_exa_news_window"])
    return {
        "all_history_best_lens": all_block.get("best_lens_id"),
        "all_history_science_core_soft_hit": (all_block.get("lenses") or {}).get("science_core", {}).get("soft_hit_rate"),
        "recent_5y_best_lens": recent.get("best_lens_id"),
        "recent_5y_science_core_soft_hit": (recent.get("lenses") or {}).get("science_core", {}).get("soft_hit_rate"),
        "holdout_2026_h1_best_lens": holdout.get("best_lens_id"),
        "holdout_2026_h1_science_plus_sasang_soft_hit": (
            (holdout.get("lenses") or {}).get("science_plus_sasang", {}).get("soft_hit_rate")
        ),
        "news_causal_exa_n_days": news_causal.get("n_days"),
        "trust_note": (
            "Long history ~46-50% soft hit = no daily edge. Holdout uplift is local; "
            "news causal coverage is tiny; do not promote to Track A or live trading."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--instrument", choices=("kospi", "btc", "both"), default="both")
    ap.add_argument("--date-from", type=str, default="1997-01-01")
    ap.add_argument("--date-to", type=str, default="2026-06-08")
    ap.add_argument("--neutral-bps", type=float, default=5.0)
    ap.add_argument("--science-jsonl-kospi", type=Path, default=DEFAULT_SCIENCE_JSONL_KOSPI)
    ap.add_argument("--science-jsonl-btc", type=Path, default=DEFAULT_SCIENCE_JSONL_BTC)
    ap.add_argument("--myeongni-jsonl", type=Path, default=DEFAULT_MYEONGNI_JSONL)
    ap.add_argument("--sasang-jsonl", type=Path, default=DEFAULT_SASANG_JSONL)
    ap.add_argument(
        "--sasang-jsonl-kospi",
        type=Path,
        default=None,
        help="Override sasang JSONL for KOSPI leg (default: --sasang-jsonl).",
    )
    ap.add_argument("--logos-lens", type=Path, default=DEFAULT_LOGOS_LENS)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact-output", type=Path, default=ART_OUT)
    args = ap.parse_args(argv)

    legs: dict[str, Any] = {}
    if args.instrument in ("kospi", "both"):
        if not args.science_jsonl_kospi.is_file():
            print(f"ERROR: missing {args.science_jsonl_kospi}", file=sys.stderr)
            return 1
        kospi_sasang = args.sasang_jsonl_kospi or args.sasang_jsonl
        legs["kospi"] = run_slice_eval(
            instrument="kospi",
            csv_path=v1.KOSPI_CSV,
            science_jsonl=args.science_jsonl_kospi,
            date_from=args.date_from,
            date_to=args.date_to,
            neutral_bps=args.neutral_bps,
            myeongni_jsonl=args.myeongni_jsonl,
            sasang_jsonl=kospi_sasang,
            logos_lens=args.logos_lens,
        )
    if args.instrument in ("btc", "both"):
        if not args.science_jsonl_btc.is_file():
            print(f"ERROR: missing {args.science_jsonl_btc}", file=sys.stderr)
            return 1
        legs["btc"] = run_slice_eval(
            instrument="btc",
            csv_path=v1.BTC_CSV,
            science_jsonl=args.science_jsonl_btc,
            date_from="2014-09-17" if args.date_from < "2014-09-17" else args.date_from,
            date_to=args.date_to,
            neutral_bps=args.neutral_bps,
            myeongni_jsonl=args.myeongni_jsonl,
            sasang_jsonl=args.sasang_jsonl,
            logos_lens=args.logos_lens,
        )

    payload: dict[str, Any] = {
        "schema": "science_core_long_history_slice_eval_bundle_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "legs": legs,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.artifact_output.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    args.output.write_text(text, encoding="utf-8")
    args.artifact_output.write_text(text, encoding="utf-8")

    kospi = legs.get("kospi") or {}
    headline = kospi.get("headline") or {}
    print(
        f"WROTE: {args.output.resolve()} "
        f"kospi_days={kospi.get('n_eval_days')} "
        f"holdout_best={headline.get('holdout_2026_h1_best_lens')} "
        f"news_causal_n={headline.get('news_causal_exa_n_days')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
